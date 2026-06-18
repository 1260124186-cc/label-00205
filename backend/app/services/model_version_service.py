"""
模型版本管理服务

基于数据库的模型版本管理，支持：
1. 版本注册（训练完成后自动注册）
2. 版本列表查询
3. 激活/回滚指定版本
4. 自动清理旧版本（超过 max_versions）
5. 按版本加载模型（用于 A/B 测试和 shadow mode）
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from loguru import logger
from sqlalchemy import and_

from app.utils.config import config
from app.utils.database import get_db, ModelVersionORM
from app.middleware import get_effective_tenant_id
from app.middleware.tenant_isolation import get_tenant_model_path, resolve_model_filename


class ModelVersionService:
    """
    模型版本管理服务（基于数据库实现）

    提供模型版本的完整生命周期管理。
    """

    def __init__(self):
        self.save_path = Path(config.get('model.save_path', './trained_models'))
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.max_versions = config.get('model_version.max_versions', 10)
        self.auto_cleanup = config.get('model_version.auto_cleanup', True)

        self._versioned_models_dir = self.save_path / 'versioned'
        self._versioned_models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"模型版本管理服务初始化完成: "
            f"save_path={self.save_path}, "
            f"max_versions={self.max_versions}, "
            f"auto_cleanup={self.auto_cleanup}"
        )

    def _get_version_file_path(
        self, model_type: str, node_id: str, version: str
    ) -> Path:
        """获取版本化模型文件的路径（租户隔离）"""
        tenant_id = get_effective_tenant_id()
        base = str(self._versioned_models_dir)
        if tenant_id is not None:
            return Path(get_tenant_model_path(base, tenant_id, f"{model_type}/{node_id}/{version}.pt"))
        return (
            self._versioned_models_dir
            / model_type
            / node_id
            / f"{version}.pt"
        )

    def _get_active_file_path(self, model_type: str, node_id: str) -> Path:
        """获取活动版本模型文件的路径（租户隔离）"""
        tenant_id = get_effective_tenant_id()
        filename = resolve_model_filename(model_type, node_id)
        return Path(get_tenant_model_path(str(self.save_path), tenant_id, filename))

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
    ) -> Dict[str, Any]:
        """
        注册新的模型版本

        Args:
            model_type: 模型类型 (bolt/flange)
            node_id: 节点ID
            model_file_path: 当前模型文件路径
            metrics: 训练指标
            training_config: 训练配置
            description: 版本描述
            training_session_id: 训练会话ID
            parent_version: 父版本号（增量训练用）
            training_samples: 训练样本数
            validation_samples: 验证样本数
            training_duration_seconds: 训练时长（秒）
            architecture_summary: 模型架构摘要
            freeze_layers: 冻结层列表

        Returns:
            版本信息字典
        """
        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                version_number = self._get_next_version(db, model_type, node_id)

                version_file = self._get_version_file_path(
                    model_type, node_id, version_number
                )
                version_file.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(model_file_path, version_file)

                file_hash = self._calculate_file_hash(version_file)
                file_size = version_file.stat().st_size

                db.query(ModelVersionORM).filter(
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.model_id == node_id,
                    ModelVersionORM.is_active == True
                ).update({ModelVersionORM.is_active: False})

                version_orm = ModelVersionORM(
                    model_type=model_type,
                    model_id=node_id,
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
                        if architecture_summary else None
                    ),
                    freeze_layers=(
                        json.dumps(freeze_layers, ensure_ascii=False)
                        if freeze_layers else None
                    ),
                    create_time=datetime.now(),
                )
                db.add(version_orm)
                db.flush()

                if self.auto_cleanup:
                    self._cleanup_old_versions(db, model_type, node_id)

                db.commit()

                logger.info(
                    f"模型版本已注册: {model_type}/{node_id} "
                    f"v{version_number}, F1={metrics.get('f1_score', 'N/A')}"
                )

                return self._orm_to_dict(version_orm)

        except Exception as e:
            logger.error(f"注册模型版本失败: {e}")
            raise

    def _get_next_version(
        self, db, model_type: str, node_id: str
    ) -> str:
        """获取下一个版本号"""
        latest = (
            db.query(ModelVersionORM)
            .filter(
                ModelVersionORM.model_type == model_type,
                ModelVersionORM.model_id == node_id,
            )
            .order_by(ModelVersionORM.create_time.desc())
            .first()
        )

        if latest and latest.version.startswith('v'):
            parts = latest.version[1:].split('.')
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"v{major}.{minor}.{patch + 1}"

        return "v1.0.0"

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希"""
        import hashlib

        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _cleanup_old_versions(
        self, db, model_type: str, node_id: str
    ) -> int:
        """
        清理超过 max_versions 的旧版本

        Returns:
            清理的版本数量
        """
        versions = (
            db.query(ModelVersionORM)
            .filter(
                ModelVersionORM.model_type == model_type,
                ModelVersionORM.model_id == node_id,
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
                    f"清理旧版本: {model_type}/{node_id} v{v.version}"
                )
            except Exception as e:
                logger.warning(
                    f"删除旧版本失败: {model_type}/{node_id} v{v.version}, error={e}"
                )

        if deleted_count > 0:
            logger.info(
                f"已清理 {deleted_count} 个旧版本: "
                f"{model_type}/{node_id}"
            )

        return deleted_count

    def list_versions(
        self,
        model_type: str,
        node_id: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        列出模型的所有版本

        Args:
            model_type: 模型类型
            node_id: 节点ID
            limit: 返回数量限制

        Returns:
            版本列表信息
        """
        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                versions = (
                    db.query(ModelVersionORM)
                    .filter(
                        ModelVersionORM.model_type == model_type,
                        ModelVersionORM.model_id == node_id,
                    )
                    .order_by(ModelVersionORM.create_time.desc())
                    .limit(limit)
                    .all()
                )

                items = [self._orm_to_dict(v) for v in versions]

                return {
                    'model_type': model_type,
                    'node_id': node_id,
                    'total': len(items),
                    'items': items,
                }

        except Exception as e:
            logger.error(f"列出模型版本失败: {e}")
            raise

    def get_version(
        self,
        model_type: str,
        node_id: str,
        version: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定版本信息

        Args:
            model_type: 模型类型
            node_id: 节点ID
            version: 版本号，None 则返回活动版本

        Returns:
            版本信息字典，不存在则返回 None
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                if version:
                    v = (
                        db.query(ModelVersionORM)
                        .filter(
                            ModelVersionORM.model_type == model_type,
                            ModelVersionORM.model_id == node_id,
                            ModelVersionORM.version == version,
                        )
                        .first()
                    )
                else:
                    v = (
                        db.query(ModelVersionORM)
                        .filter(
                            ModelVersionORM.model_type == model_type,
                            ModelVersionORM.model_id == node_id,
                            ModelVersionORM.is_active == True,
                        )
                        .first()
                    )

                return self._orm_to_dict(v) if v else None

        except Exception as e:
            logger.error(f"获取模型版本失败: {e}")
            return None

    def activate_version(
        self,
        model_type: str,
        node_id: str,
        version: str,
    ) -> Dict[str, Any]:
        """
        激活指定版本（切换活动版本）

        Args:
            model_type: 模型类型
            node_id: 节点ID
            version: 目标版本号

        Returns:
            激活后的版本信息
        """
        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                target = (
                    db.query(ModelVersionORM)
                    .filter(
                        ModelVersionORM.model_type == model_type,
                        ModelVersionORM.model_id == node_id,
                        ModelVersionORM.version == version,
                    )
                    .first()
                )

                if target is None:
                    raise ValueError(f"版本不存在: {version}")

                if not target.file_path or not os.path.exists(target.file_path):
                    raise FileNotFoundError(
                        f"版本文件不存在: {target.file_path}"
                    )

                active_file = self._get_active_file_path(model_type, node_id)
                shutil.copy2(target.file_path, active_file)

                db.query(ModelVersionORM).filter(
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.model_id == node_id,
                    ModelVersionORM.is_active == True,
                ).update({ModelVersionORM.is_active: False})

                target.is_active = True
                target.update_time = datetime.now()

                db.commit()
                db.refresh(target)

                logger.info(
                    f"模型版本已激活: {model_type}/{node_id} -> v{version}"
                )

                return self._orm_to_dict(target)

        except Exception as e:
            logger.error(f"激活模型版本失败: {e}")
            raise

    def rollback(
        self,
        model_type: str,
        node_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        回滚到指定版本（或上一个版本）

        Args:
            model_type: 模型类型
            node_id: 节点ID
            version: 目标版本号，None 则回滚到上一个版本

        Returns:
            回滚后的版本信息
        """
        if version is None:
            version_list = self.list_versions(model_type, node_id, limit=2)
            items = version_list.get('items', [])
            if len(items) < 2:
                raise ValueError("没有可回滚的上一个版本")
            version = items[1]['version']

        return self.activate_version(model_type, node_id, version)

    def delete_version(
        self,
        model_type: str,
        node_id: str,
        version: str,
    ) -> bool:
        """
        删除指定版本

        Args:
            model_type: 模型类型
            node_id: 节点ID
            version: 版本号

        Returns:
            是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                target = (
                    db.query(ModelVersionORM)
                    .filter(
                        ModelVersionORM.model_type == model_type,
                        ModelVersionORM.model_id == node_id,
                        ModelVersionORM.version == version,
                    )
                    .first()
                )

                if target is None:
                    return False

                if target.is_active:
                    raise ValueError("不能删除活动版本")

                if target.file_path and os.path.exists(target.file_path):
                    try:
                        os.remove(target.file_path)
                    except OSError as e:
                        logger.warning(f"删除版本文件失败: {e}")

                db.delete(target)
                db.commit()

                logger.info(
                    f"版本已删除: {model_type}/{node_id} v{version}"
                )

                return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False

    def get_model_file_path(
        self,
        model_type: str,
        node_id: str,
        version: Optional[str] = None,
    ) -> Optional[str]:
        """
        获取指定版本的模型文件路径

        Args:
            model_type: 模型类型
            node_id: 节点ID
            version: 版本号，None 则返回活动版本路径

        Returns:
            模型文件路径，不存在则返回 None
        """
        version_info = self.get_version(model_type, node_id, version)
        if version_info and version_info.get('file_path'):
            if os.path.exists(version_info['file_path']):
                return version_info['file_path']
        return None

    def cleanup_old_versions_manual(
        self,
        model_type: str,
        node_id: str,
    ) -> int:
        """
        手动清理旧版本（供 API 调用）

        Args:
            model_type: 模型类型
            node_id: 节点ID

        Returns:
            清理的版本数量
        """
        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                count = self._cleanup_old_versions(db, model_type, node_id)
                db.commit()
                return count

        except Exception as e:
            logger.error(f"手动清理旧版本失败: {e}")
            raise

    def compare_versions(
        self,
        model_type: str,
        node_id: str,
        version1: str,
        version2: str,
    ) -> Dict[str, Any]:
        """
        对比两个版本的指标

        Args:
            model_type: 模型类型
            node_id: 节点ID
            version1: 版本1
            version2: 版本2

        Returns:
            对比结果
        """
        v1 = self.get_version(model_type, node_id, version1)
        v2 = self.get_version(model_type, node_id, version2)

        if v1 is None or v2 is None:
            raise ValueError("版本不存在")

        metrics1 = v1.get('metrics') or {}
        metrics2 = v2.get('metrics') or {}

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
                'diff': diff,
                'improved': improved,
            }

        return {
            'model_type': model_type,
            'node_id': node_id,
            'version1': version1,
            'version2': version2,
            'metrics_comparison': metrics_comparison,
            'config_diff': {
                version1: v1.get('config') or {},
                version2: v2.get('config') or {},
            },
        }

    def _orm_to_dict(self, orm: ModelVersionORM) -> Dict[str, Any]:
        """将 ORM 对象转换为字典"""
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
            'id': orm.id,
            'model_type': orm.model_type,
            'model_id': orm.model_id,
            'version': orm.version,
            'file_path': orm.file_path,
            'file_hash': orm.file_hash,
            'file_size_bytes': orm.file_size_bytes,
            'metrics': metrics,
            'config': config_data,
            'is_active': orm.is_active or False,
            'description': orm.description,
            'training_session_id': orm.training_session_id,
            'parent_version': orm.parent_version,
            'training_samples': orm.training_samples,
            'validation_samples': orm.validation_samples,
            'training_duration_seconds': orm.training_duration_seconds,
            'architecture_summary': arch_summary,
            'freeze_layers': freeze_layers,
            'create_time': orm.create_time,
            'update_time': orm.update_time,
        }


_model_version_service = None


def get_model_version_service() -> ModelVersionService:
    """获取模型版本管理服务单例"""
    global _model_version_service
    if _model_version_service is None:
        _model_version_service = ModelVersionService()
    return _model_version_service
