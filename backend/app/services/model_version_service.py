"""
模型版本管理服务（租户隔离版）

基于数据库的模型版本管理，支持：
1. 版本注册（训练完成后自动注册）
2. 版本列表查询（自动按当前租户过滤）
3. 激活/回滚指定版本（跨租户访问→404）
4. 自动清理旧版本（超过 max_versions）
5. 按版本加载模型（用于 A/B 测试和 shadow mode）
6. 模型路径标准化：trained_models/{tenant_id}/xxx
7. 配额硬限制检查（模型数、存储）
8. 注册/删除后自动同步模型数与存储统计

安全策略：
- 所有查询自动注入 tenant_id 过滤
- 每条记录在返回前 enforce_tenant_access，跨租户→404
- 注册新模型前检查 ensure_model_quota_available
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_

from app.utils.config import config
from app.utils.database import get_db, ModelVersionORM
from app.middleware import (
    get_effective_tenant_id,
    is_super_admin,
    is_audit_mode,
)
from app.services.tenant import (
    enforce_tenant_access,
    enforce_tenant_query,
    get_active_model_path,
    get_versioned_model_path,
    ensure_model_quota_available,
    sync_tenant_storage_usage,
    sync_tenant_model_count,
    not_found_404,
)


class ModelVersionService:
    """
    模型版本管理服务（基于数据库 + 强租户隔离）

    提供模型版本的完整生命周期管理。
    """

    def __init__(self):
        self.max_versions = config.get("model_version.max_versions", 10)
        self.auto_cleanup = config.get("model_version.auto_cleanup", True)

        logger.info(
            "模型版本管理服务初始化完成: "
            f"max_versions={self.max_versions}, "
            f"auto_cleanup={self.auto_cleanup}"
        )

    # ============================================================
    # 路径解析（全部走 enforcement 模块）
    # ============================================================

    def _get_version_file_path(
        self,
        model_type: str,
        node_id: str,
        version: str,
        tenant_id: Optional[int] = None,
    ) -> Path:
        """获取版本化模型文件的路径"""
        return get_versioned_model_path(model_type, str(node_id), version, tenant_id)

    def _get_active_file_path(
        self,
        model_type: str,
        node_id: str,
        tenant_id: Optional[int] = None,
    ) -> Path:
        """获取活动版本模型文件的路径（主路径）"""
        return get_active_model_path(model_type, str(node_id), tenant_id)

    # ============================================================
    # 版本注册
    # ============================================================

    def register_version(
        self,
        model_type: str,
        node_id: str,
        model_file_path: str,
        metrics: Dict[str, Any],
        training_config: Optional[Dict[str, Any]] = None,
        description: str = "",
        training_session_id: Optional[str] = None,
        parent_version: Optional[str] = None,
        training_samples: Optional[int] = None,
        validation_samples: Optional[int] = None,
        training_duration_seconds: Optional[float] = None,
        architecture_summary: Optional[Dict[str, Any]] = None,
        freeze_layers: Optional[List[str]] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        注册新的模型版本

        前置检查：
        1. 必须有有效 tenant_id（显式传入或从上下文解析）
        2. 检查配额：模型数、存储用量

        写入：
        1. 复制模型文件到 trained_models/{tenant_id}/versioned/{type}/{id}/vX.Y.Z.pt
        2. 复制一份为活动版本 trained_models/{tenant_id}/bolt_lstm_{id}.pt
        3. 写入 ModelVersionORM（带 tenant_id）
        4. 同步 TenantQuota 计数与存储
        """
        effective_id = tenant_id or get_effective_tenant_id()
        if effective_id is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                ensure_model_quota_available(effective_id, db)

                version_number = self._get_next_version(
                    db, model_type, node_id, effective_id
                )

                version_file = self._get_version_file_path(
                    model_type, node_id, version_number, effective_id
                )
                version_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(model_file_path, version_file)

                active_file = self._get_active_file_path(
                    model_type, node_id, effective_id
                )
                active_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(model_file_path, active_file)

                file_hash = self._calculate_file_hash(version_file)
                file_size = version_file.stat().st_size

                db.query(ModelVersionORM).filter(
                    ModelVersionORM.tenant_id == effective_id,
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.model_id == str(node_id),
                    ModelVersionORM.is_active == True,
                ).update({ModelVersionORM.is_active: False})

                version_orm = ModelVersionORM(
                    tenant_id=effective_id,
                    model_type=model_type,
                    model_id=str(node_id),
                    version=version_number,
                    file_path=str(version_file),
                    file_hash=file_hash,
                    file_size_bytes=file_size,
                    metrics=json.dumps(metrics, ensure_ascii=False),
                    config=json.dumps(training_config or {}, ensure_ascii=False),
                    is_active=True,
                    description=description,
                    training_session_id=training_session_id,
                    parent_version=parent_version,
                    training_samples=training_samples,
                    validation_samples=validation_samples,
                    training_duration_seconds=training_duration_seconds,
                    architecture_summary=(
                        json.dumps(architecture_summary, ensure_ascii=False)
                        if architecture_summary
                        else None
                    ),
                    freeze_layers=(
                        json.dumps(freeze_layers, ensure_ascii=False)
                        if freeze_layers
                        else None
                    ),
                    create_time=datetime.now(),
                )
                db.add(version_orm)
                db.flush()

                if self.auto_cleanup:
                    self._cleanup_old_versions(
                        db, model_type, node_id, effective_id
                    )

                sync_tenant_model_count(effective_id, db)
                sync_tenant_storage_usage(effective_id, db)

                db.commit()
                db.refresh(version_orm)

                logger.info(
                    f"模型版本已注册: tenant={effective_id}, "
                    f"{model_type}/{node_id} "
                    f"v{version_number}, F1={metrics.get('f1_score', 'N/A')}, "
                    f"size={file_size}B"
                )

                return self._orm_to_dict(version_orm)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"注册模型版本失败: {e}")
            raise

    def _get_next_version(
        self, db, model_type: str, node_id: str, tenant_id: int
    ) -> str:
        """获取下一个版本号（按租户隔离）"""
        latest = (
            db.query(ModelVersionORM)
            .filter(
                ModelVersionORM.tenant_id == tenant_id,
                ModelVersionORM.model_type == model_type,
                ModelVersionORM.model_id == str(node_id),
            )
            .order_by(ModelVersionORM.create_time.desc())
            .first()
        )

        if latest and latest.version.startswith("v"):
            parts = latest.version[1:].split(".")
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"v{major}.{minor}.{patch + 1}"

        return "v1.0.0"

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """计算文件MD5哈希"""
        import hashlib

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    # ============================================================
    # 旧版本清理
    # ============================================================

    def _cleanup_old_versions(
        self, db, model_type: str, node_id: str, tenant_id: int
    ) -> int:
        """
        清理超过 max_versions 的旧版本（按租户隔离）

        Returns:
            清理的版本数量
        """
        versions = (
            db.query(ModelVersionORM)
            .filter(
                ModelVersionORM.tenant_id == tenant_id,
                ModelVersionORM.model_type == model_type,
                ModelVersionORM.model_id == str(node_id),
            )
            .order_by(ModelVersionORM.create_time.desc())
            .all()
        )

        if len(versions) <= self.max_versions:
            return 0

        to_delete = versions[self.max_versions:]
        deleted_count = 0

        for v in to_delete:
            if v.is_active:
                continue

            try:
                if v.file_path and os.path.exists(v.file_path):
                    os.remove(v.file_path)
                    version_dir = Path(v.file_path).parent
                    if version_dir.exists() and not any(version_dir.iterdir()):
                        try:
                            version_dir.rmdir()
                        except OSError:
                            pass

                db.delete(v)
                deleted_count += 1
                logger.debug(
                    f"清理旧版本: tenant={tenant_id}, "
                    f"{model_type}/{node_id} v{v.version}"
                )
            except Exception as e:
                logger.warning(
                    f"删除旧版本失败: tenant={tenant_id}, "
                    f"{model_type}/{node_id} v{v.version}, error={e}"
                )

        if deleted_count > 0:
            sync_tenant_storage_usage(tenant_id, db)
            sync_tenant_model_count(tenant_id, db)
            logger.info(
                f"已清理 {deleted_count} 个旧版本: "
                f"tenant={tenant_id}, {model_type}/{node_id}"
            )

        return deleted_count

    # ============================================================
    # 查询（全部 enforce 租户隔离）
    # ============================================================

    def list_versions(
        self,
        model_type: str,
        node_id: str,
        limit: int = 50,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        列出模型的所有版本（当前租户可见）

        Raises:
            HTTPException(404): 无有效 tenant context
        """
        effective_id = tenant_id or get_effective_tenant_id()
        if effective_id is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                q = db.query(ModelVersionORM).filter(
                    ModelVersionORM.tenant_id == effective_id,
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.model_id == str(node_id),
                )
                versions = (
                    q.order_by(ModelVersionORM.create_time.desc())
                    .limit(limit)
                    .all()
                )

                items = []
                for v in versions:
                    try:
                        enforce_tenant_access(
                            v.tenant_id, v.id, "ModelVersion"
                        )
                        items.append(self._orm_to_dict(v))
                    except HTTPException:
                        continue

                return {
                    "tenant_id": effective_id,
                    "model_type": model_type,
                    "node_id": node_id,
                    "total": len(items),
                    "items": items,
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"列出模型版本失败: {e}")
            raise

    def get_version(
        self,
        model_type: str,
        node_id: str,
        version: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定版本信息。跨租户访问 → 404
        """
        effective_id = tenant_id or get_effective_tenant_id()
        if effective_id is None:
            return None

        try:
            with get_db() as db:
                if db is None:
                    return None

                if version:
                    v = (
                        db.query(ModelVersionORM)
                        .filter(
                            ModelVersionORM.tenant_id == effective_id,
                            ModelVersionORM.model_type == model_type,
                            ModelVersionORM.model_id == str(node_id),
                            ModelVersionORM.version == version,
                        )
                        .first()
                    )
                else:
                    v = (
                        db.query(ModelVersionORM)
                        .filter(
                            ModelVersionORM.tenant_id == effective_id,
                            ModelVersionORM.model_type == model_type,
                            ModelVersionORM.model_id == str(node_id),
                            ModelVersionORM.is_active == True,
                        )
                        .first()
                    )

                if v is None:
                    return None

                enforce_tenant_access(v.tenant_id, v.id, "ModelVersion")
                return self._orm_to_dict(v)

        except HTTPException:
            return None
        except Exception as e:
            logger.error(f"获取模型版本失败: {e}")
            return None

    # ============================================================
    # 激活 / 回滚
    # ============================================================

    def activate_version(
        self,
        model_type: str,
        node_id: str,
        version: str,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        激活指定版本（切换活动版本）。跨租户访问 → 404

        操作：
        1. 校验租户权限
        2. 将目标版本文件复制为活动文件（trained_models/{tenant_id}/xxx）
        3. 数据库中切换 is_active 标志
        """
        if is_audit_mode():
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": "审计模式为只读，无法激活模型版本",
                },
            )

        effective_id = tenant_id or get_effective_tenant_id()
        if effective_id is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                target = (
                    db.query(ModelVersionORM)
                    .filter(
                        ModelVersionORM.tenant_id == effective_id,
                        ModelVersionORM.model_type == model_type,
                        ModelVersionORM.model_id == str(node_id),
                        ModelVersionORM.version == version,
                    )
                    .first()
                )

                if target is None:
                    raise not_found_404("目标模型版本不存在")

                enforce_tenant_access(
                    target.tenant_id, target.id, "ModelVersion"
                )

                if not target.file_path or not os.path.exists(target.file_path):
                    raise not_found_404("版本文件已丢失")

                active_file = self._get_active_file_path(
                    model_type, node_id, effective_id
                )
                active_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target.file_path, active_file)

                db.query(ModelVersionORM).filter(
                    ModelVersionORM.tenant_id == effective_id,
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.model_id == str(node_id),
                    ModelVersionORM.is_active == True,
                ).update({ModelVersionORM.is_active: False})

                target.is_active = True
                target.update_time = datetime.now()

                db.commit()
                db.refresh(target)

                logger.info(
                    f"模型版本已激活: tenant={effective_id}, "
                    f"{model_type}/{node_id} -> v{version}"
                )

                return self._orm_to_dict(target)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"激活模型版本失败: {e}")
            raise

    def rollback(
        self,
        model_type: str,
        node_id: str,
        version: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        回滚到指定版本（或上一个版本）
        """
        if version is None:
            version_list = self.list_versions(model_type, node_id, limit=2, tenant_id=tenant_id)
            items = version_list.get("items", [])
            if len(items) < 2:
                raise not_found_404("没有可回滚的上一个版本")
            version = items[1]["version"]

        return self.activate_version(model_type, node_id, version, tenant_id=tenant_id)

    # ============================================================
    # 删除版本
    # ============================================================

    def delete_version(
        self,
        model_type: str,
        node_id: str,
        version: str,
        tenant_id: Optional[int] = None,
    ) -> bool:
        """
        删除指定版本（不能是活动版本）。跨租户访问 → 404
        """
        if is_audit_mode():
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": "审计模式为只读，无法删除模型版本",
                },
            )

        effective_id = tenant_id or get_effective_tenant_id()
        if effective_id is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                target = (
                    db.query(ModelVersionORM)
                    .filter(
                        ModelVersionORM.tenant_id == effective_id,
                        ModelVersionORM.model_type == model_type,
                        ModelVersionORM.model_id == str(node_id),
                        ModelVersionORM.version == version,
                    )
                    .first()
                )

                if target is None:
                    raise not_found_404()

                enforce_tenant_access(
                    target.tenant_id, target.id, "ModelVersion"
                )

                if target.is_active:
                    raise ValueError("不能删除活动版本")

                if target.file_path and os.path.exists(target.file_path):
                    try:
                        os.remove(target.file_path)
                    except OSError as e:
                        logger.warning(f"删除版本文件失败: {e}")

                db.delete(target)
                sync_tenant_model_count(effective_id, db)
                sync_tenant_storage_usage(effective_id, db)
                db.commit()

                logger.info(
                    f"版本已删除: tenant={effective_id}, "
                    f"{model_type}/{node_id} v{version}"
                )

                return True

        except HTTPException:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False

    # ============================================================
    # 文件路径查询
    # ============================================================

    def get_model_file_path(
        self,
        model_type: str,
        node_id: str,
        version: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Optional[str]:
        """
        获取指定版本的模型文件路径（带租户权限校验）

        Returns:
            模型文件路径，不存在或无权限则返回 None
        """
        version_info = self.get_version(model_type, node_id, version, tenant_id=tenant_id)
        if version_info and version_info.get("file_path"):
            if os.path.exists(version_info["file_path"]):
                return version_info["file_path"]
        return None

    # ============================================================
    # 其它 API
    # ============================================================

    def cleanup_old_versions_manual(
        self,
        model_type: str,
        node_id: str,
        tenant_id: Optional[int] = None,
    ) -> int:
        """
        手动清理旧版本（供 API 调用）
        """
        if is_audit_mode():
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": "审计模式为只读",
                },
            )

        effective_id = tenant_id or get_effective_tenant_id()
        if effective_id is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                count = self._cleanup_old_versions(
                    db, model_type, node_id, effective_id
                )
                db.commit()
                return count

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"手动清理旧版本失败: {e}")
            raise

    def compare_versions(
        self,
        model_type: str,
        node_id: str,
        version1: str,
        version2: str,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        对比两个版本的指标
        """
        v1 = self.get_version(model_type, node_id, version1, tenant_id=tenant_id)
        v2 = self.get_version(model_type, node_id, version2, tenant_id=tenant_id)

        if v1 is None or v2 is None:
            raise not_found_404("版本不存在")

        metrics1 = v1.get("metrics") or {}
        metrics2 = v2.get("metrics") or {}

        all_metrics = set(metrics1.keys()) | set(metrics2.keys())
        metrics_comparison = {}

        for metric in all_metrics:
            val1 = metrics1.get(metric, 0)
            val2 = metrics2.get(metric, 0)
            try:
                diff = float(val2) - float(val1)
                improved = diff > 0
            except (TypeError, ValueError):
                diff = None
                improved = None

            metrics_comparison[metric] = {
                version1: val1,
                version2: val2,
                "diff": diff,
                "improved": improved,
            }

        return {
            "model_type": model_type,
            "node_id": node_id,
            "version1": version1,
            "version2": version2,
            "metrics_comparison": metrics_comparison,
            "config_diff": {
                version1: v1.get("config") or {},
                version2: v2.get("config") or {},
            },
        }

    # ============================================================
    # ORM → Dict
    # ============================================================

    @staticmethod
    def _orm_to_dict(orm: ModelVersionORM) -> Dict[str, Any]:
        """将 ORM 对象转换为字典（含 tenant_id）"""
        metrics = None
        if orm.metrics:
            try:
                metrics = json.loads(orm.metrics)
            except Exception:
                metrics = None

        config_data = None
        if orm.config:
            try:
                config_data = json.loads(orm.config)
            except Exception:
                config_data = None

        arch_summary = None
        if orm.architecture_summary:
            try:
                arch_summary = json.loads(orm.architecture_summary)
            except Exception:
                arch_summary = None

        freeze_layers = None
        if orm.freeze_layers:
            try:
                freeze_layers = json.loads(orm.freeze_layers)
            except Exception:
                freeze_layers = None

        return {
            "id": orm.id,
            "tenant_id": orm.tenant_id,
            "model_type": orm.model_type,
            "model_id": orm.model_id,
            "version": orm.version,
            "file_path": orm.file_path,
            "file_hash": orm.file_hash,
            "file_size_bytes": orm.file_size_bytes,
            "metrics": metrics,
            "config": config_data,
            "is_active": orm.is_active or False,
            "description": orm.description,
            "training_session_id": orm.training_session_id,
            "parent_version": orm.parent_version,
            "training_samples": orm.training_samples,
            "validation_samples": orm.validation_samples,
            "training_duration_seconds": orm.training_duration_seconds,
            "architecture_summary": arch_summary,
            "freeze_layers": freeze_layers,
            "create_time": orm.create_time,
            "update_time": orm.update_time,
        }


_model_version_service = None


def get_model_version_service() -> ModelVersionService:
    """获取模型版本管理服务单例"""
    global _model_version_service
    if _model_version_service is None:
        _model_version_service = ModelVersionService()
    return _model_version_service
