"""
租户级数据与模型强隔离 Enforcement 模块

功能:
1. 跨租户访问检测与 404 错误封装（防枚举攻击，非 403）
2. 训练并发硬限制管理（acquire/release）
3. 配额硬限制检查（模型数、存储GB、日API调用、训练并发）
4. 自动注入 tenant_id 的查询构建辅助
5. 组织树解析（根据组织节点ID反推 tenant_id）
6. 模型文件路径标准化（trained_models/{tenant_id}/xxx）

使用示例:
    from app.services.tenant.enforcement import (
        enforce_tenant_access,
        not_found_404,
        acquire_training_slot,
        release_training_slot,
        check_hard_quota,
        get_tenant_model_dir,
    )
"""

import os
import threading
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Type, TypeVar

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import Query, Session

from app.middleware import (
    get_effective_tenant_id,
    is_super_admin,
    is_audit_mode,
)
from app.utils.config import config
from app.utils.database import (
    get_db,
    Tenant,
    TenantQuota,
    OrganizationNode,
    ModelVersionORM,
    TrainingLog,
)


T = TypeVar("T")


_tenant_training_locks: Dict[int, threading.Semaphore] = {}
_global_enforcement_lock = threading.Lock()


def not_found_404(detail: str = "Resource not found") -> HTTPException:
    """
    生成跨租户访问 404 错误（非 403，防止资源枚举攻击）

    设计原则:
    - 跨租户访问一律返回 404，不区分"不存在"和"无权限"
    - 攻击者无法通过 403/404 的差异来探测有效资源ID

    Args:
        detail: 错误描述（统一为通用描述，避免信息泄露）

    Returns:
        HTTPException: status_code=404
    """
    return HTTPException(
        status_code=404,
        detail={"error": "NotFound", "message": detail},
    )


def enforce_tenant_access(
    resource_tenant_id: Optional[int],
    resource_id: Optional[Any] = None,
    resource_type: str = "resource",
) -> None:
    """
    强制检查租户访问权限。跨租户访问返回 404。

    规则:
    - 超级管理员审计模式：允许只读（middleware已拦截写入）
    - 普通用户：resource_tenant_id 必须等于 current_tenant_id
    - resource_tenant_id 为 None（未绑定租户）：视为不存在，返回 404
    - current_tenant_id 为 None（未认证）：返回 404

    Args:
        resource_tenant_id: 资源所属租户ID
        resource_id: 资源ID（用于日志记录）
        resource_type: 资源类型描述（用于日志记录）

    Raises:
        HTTPException: 404 - 跨租户访问或资源不存在
    """
    current_tenant_id = get_effective_tenant_id()

    if current_tenant_id is None:
        logger.warning(
            f"Tenant enforcement blocked: no tenant context, "
            f"type={resource_type}, id={resource_id}"
        )
        raise not_found_404()

    if resource_tenant_id is None:
        logger.warning(
            f"Tenant enforcement blocked: resource has no tenant_id, "
            f"type={resource_type}, id={resource_id}, current_tenant={current_tenant_id}"
        )
        raise not_found_404()

    if is_super_admin():
        logger.debug(
            f"Super admin access: type={resource_type}, id={resource_id}, "
            f"audit_mode={is_audit_mode()}, current_tenant={current_tenant_id}, "
            f"resource_tenant={resource_tenant_id}"
        )
        return

    if int(resource_tenant_id) != int(current_tenant_id):
        logger.warning(
            f"Cross-tenant access blocked: type={resource_type}, id={resource_id}, "
            f"current_tenant={current_tenant_id}, resource_tenant={resource_tenant_id}"
        )
        raise not_found_404()


def enforce_tenant_query(
    query: Query,
    model_class: Any,
    tenant_id: Optional[int] = None,
) -> Query:
    """
    为查询自动注入 tenant_id 过滤条件。

    用法:
        q = db.query(BoltData).filter(...)
        q = enforce_tenant_query(q, BoltData)
        results = q.all()

    超级管理员审计模式：按审计租户ID过滤。

    Args:
        query: SQLAlchemy Query 对象
        model_class: ORM 模型类（检查是否有 tenant_id 字段）
        tenant_id: 指定租户ID，None则使用上下文的 effective_tenant_id

    Returns:
        Query: 已注入 tenant_id 过滤的查询
    """
    if not hasattr(model_class, "tenant_id"):
        return query

    effective_id = tenant_id or get_effective_tenant_id()
    if effective_id is not None:
        return query.filter(model_class.tenant_id == effective_id)
    return query.filter(model_class.tenant_id == -1)


def resolve_tenant_id_from_org_node(
    db: Session,
    org_node_id: int,
) -> Optional[int]:
    """
    通过组织树解析获取节点所属的 tenant_id。

    Args:
        db: 数据库会话
        org_node_id: 组织节点ID

    Returns:
        租户ID，找不到返回 None
    """
    node = (
        db.query(OrganizationNode)
        .filter(OrganizationNode.id == org_node_id)
        .first()
    )
    if node:
        return node.tenant_id
    return None


def get_base_models_dir() -> Path:
    """
    获取模型根目录 trained_models/
    """
    base = Path(config.get("model.save_path", "./trained_models"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_tenant_model_dir(tenant_id: Optional[int] = None) -> Path:
    """
    获取指定租户的模型目录 trained_models/{tenant_id}/

    目录结构:
        trained_models/
            {tenant_id}/
                bolt_lstm_{node_id}.pt
                flange_attention_{node_id}.pt
                versioned/
                    bolt/
                        {node_id}/
                            v1.0.0.pt
                    flange/
                        ...

    Args:
        tenant_id: 租户ID，None则使用上下文

    Returns:
        Path: 租户模型目录路径
    """
    effective_id = tenant_id or get_effective_tenant_id()
    if effective_id is None:
        raise ValueError("Tenant ID is required for model directory resolution")

    tenant_dir = get_base_models_dir() / str(effective_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return tenant_dir


def get_active_model_path(
    model_type: str,
    node_id: str,
    tenant_id: Optional[int] = None,
) -> Path:
    """
    获取活动版本模型文件路径：trained_models/{tenant_id}/{type}_{id}.pt

    Args:
        model_type: 模型类型 (bolt/flange)
        node_id: 节点ID
        tenant_id: 租户ID，None则使用上下文

    Returns:
        Path: 模型文件路径
    """
    tenant_dir = get_tenant_model_dir(tenant_id)
    if model_type == "bolt":
        return tenant_dir / f"bolt_lstm_{node_id}.pt"
    elif model_type == "flange":
        return tenant_dir / f"flange_attention_{node_id}.pt"
    else:
        return tenant_dir / f"{model_type}_{node_id}.pt"


def get_versioned_model_dir(
    model_type: str,
    node_id: str,
    tenant_id: Optional[int] = None,
) -> Path:
    """
    获取版本化模型目录：trained_models/{tenant_id}/versioned/{type}/{id}/

    Args:
        model_type: 模型类型
        node_id: 节点ID
        tenant_id: 租户ID

    Returns:
        Path: 版本目录路径
    """
    tenant_dir = get_tenant_model_dir(tenant_id)
    version_dir = tenant_dir / "versioned" / model_type / str(node_id)
    version_dir.mkdir(parents=True, exist_ok=True)
    return version_dir


def get_versioned_model_path(
    model_type: str,
    node_id: str,
    version: str,
    tenant_id: Optional[int] = None,
) -> Path:
    """
    获取指定版本的模型文件路径。

    Returns:
        Path: 版本化模型文件路径
    """
    return get_versioned_model_dir(model_type, node_id, tenant_id) / f"{version}.pt"


# ============================================================
# 训练并发硬限制
# ============================================================

def _get_tenant_semaphore(tenant_id: int) -> threading.Semaphore:
    """获取（懒创建）租户级训练并发信号量"""
    with _global_enforcement_lock:
        sem = _tenant_training_locks.get(tenant_id)
        if sem is None:
            with get_db() as db:
                quota = None
                if db is not None:
                    quota = (
                        db.query(TenantQuota)
                        .filter(TenantQuota.tenant_id == tenant_id)
                        .first()
                    )
                max_concurrency = (
                    quota.max_training_concurrency if quota else 2
                )
            sem = threading.Semaphore(max_concurrency)
            _tenant_training_locks[tenant_id] = sem
        return sem


def refresh_tenant_concurrency_limit(tenant_id: int) -> None:
    """
    当租户配额的 max_training_concurrency 被修改后调用此函数刷新信号量。

    注意：此操作不会抢占正在进行的训练，仅对新 acquire 生效。
    """
    with _global_enforcement_lock:
        _tenant_training_locks.pop(tenant_id, None)


def get_current_training_count(tenant_id: int, db: Optional[Session] = None) -> int:
    """
    查询数据库中当前租户正在运行（running/pending）的训练任务数。

    Args:
        tenant_id: 租户ID
        db: 可选数据库会话

    Returns:
        int: 活跃训练数
    """
    def _query(session: Session) -> int:
        return (
            session.query(TrainingLog)
            .filter(
                TrainingLog.tenant_id == tenant_id,
                TrainingLog.status.in_(["pending", "running"]),
            )
            .count()
        )

    if db is not None:
        return _query(db)
    with get_db() as session:
        if session is None:
            return 0
        return _query(session)


@contextmanager
def acquire_training_slot(
    tenant_id: Optional[int] = None,
    timeout: float = 0,
) -> Generator[bool, None, None]:
    """
    申请训练并发槽（硬限制）。使用 with 语句自动释放。

    优先使用 DB 层面的计数与信号量双层控制：
    1. 先检查 DB 中 running/pending 的数量是否 < 配额
    2. 再获取线程级信号量

    Usage:
        with acquire_training_slot(tenant_id=123) as ok:
            if not ok:
                raise HTTPException(429, "训练并发已满")
            run_training(...)

    Args:
        tenant_id: 租户ID，None则使用上下文
        timeout: 信号量等待超时秒数，0为非阻塞

    Yields:
        bool: 是否成功获取槽位

    Raises:
        ValueError: tenant_id 无法解析
    """
    effective_id = tenant_id or get_effective_tenant_id()
    if effective_id is None:
        raise ValueError("Tenant ID required for training slot acquisition")

    with get_db() as db:
        if db is None:
            yield False
            return
        quota = (
            db.query(TenantQuota)
            .filter(TenantQuota.tenant_id == effective_id)
            .first()
        )
        if quota is None:
            yield False
            return

        running_count = (
            db.query(TrainingLog)
            .filter(
                TrainingLog.tenant_id == effective_id,
                TrainingLog.status.in_(["pending", "running"]),
            )
            .count()
        )
        if running_count >= quota.max_training_concurrency:
            logger.warning(
                f"Training concurrency limit reached: tenant={effective_id}, "
                f"running={running_count}, max={quota.max_training_concurrency}"
            )
            yield False
            return

    sem = _get_tenant_semaphore(effective_id)
    acquired = sem.acquire(timeout=timeout if timeout > 0 else False)
    try:
        yield acquired
    finally:
        if acquired:
            sem.release()


def increment_training_concurrency_counter(tenant_id: int, db: Session) -> None:
    """
    递增 TenantQuota.current_training_concurrency（仅作统计显示，非硬限制依据）
    硬限制依据为 TrainingLog.status in (pending/running)
    """
    try:
        running = (
            db.query(TrainingLog)
            .filter(
                TrainingLog.tenant_id == tenant_id,
                TrainingLog.status.in_(["pending", "running"]),
            )
            .count()
        )
        quota = (
            db.query(TenantQuota)
            .filter(TenantQuota.tenant_id == tenant_id)
            .first()
        )
        if quota:
            quota.current_training_concurrency = running
    except Exception as e:
        logger.warning(f"Failed to update training concurrency counter: {e}")


# ============================================================
# 配额硬限制检查
# ============================================================

class QuotaExceededError(Exception):
    """配额超限异常"""
    def __init__(self, resource: str, current: float, limit: float):
        self.resource = resource
        self.current = current
        self.limit = limit
        super().__init__(f"Quota exceeded: {resource} {current}/{limit}")


def check_hard_quota(
    tenant_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    检查租户所有硬配额，返回详细状态。

    Returns:
        {
            "ok": bool,
            "model_count": {"current": int, "limit": int, "ok": bool},
            "storage_mb": {"current": float, "limit": int, "ok": bool},
            "api_calls_today": {"current": int, "limit": int, "ok": bool},
            "training_concurrency": {"current": int, "limit": int, "ok": bool},
        }
    """
    effective_id = tenant_id or get_effective_tenant_id()
    if effective_id is None:
        raise ValueError("Tenant ID required for quota check")

    def _check(session: Session) -> Dict[str, Any]:
        quota = (
            session.query(TenantQuota)
            .filter(TenantQuota.tenant_id == effective_id)
            .first()
        )
        if quota is None:
            raise ValueError(f"No quota record for tenant {effective_id}")

        model_count = (
            session.query(ModelVersionORM)
            .filter(
                ModelVersionORM.tenant_id == effective_id,
                ModelVersionORM.is_active == True,
            )
            .count()
        )

        storage_used_mb = _calculate_tenant_storage_usage(effective_id, session)

        today = datetime.now().strftime("%Y-%m-%d")
        if quota.api_call_reset_date != today:
            api_calls = 0
        else:
            api_calls = quota.current_api_calls_today or 0

        training_count = (
            session.query(TrainingLog)
            .filter(
                TrainingLog.tenant_id == effective_id,
                TrainingLog.status.in_(["pending", "running"]),
            )
            .count()
        )

        return {
            "ok": (
                model_count <= quota.max_models
                and storage_used_mb <= quota.max_storage_mb
                and api_calls <= quota.max_api_calls_per_day
                and training_count <= quota.max_training_concurrency
            ),
            "model_count": {
                "current": model_count,
                "limit": quota.max_models,
                "ok": model_count <= quota.max_models,
            },
            "storage_mb": {
                "current": round(storage_used_mb, 2),
                "limit": quota.max_storage_mb,
                "ok": storage_used_mb <= quota.max_storage_mb,
            },
            "api_calls_today": {
                "current": api_calls,
                "limit": quota.max_api_calls_per_day,
                "ok": api_calls <= quota.max_api_calls_per_day,
            },
            "training_concurrency": {
                "current": training_count,
                "limit": quota.max_training_concurrency,
                "ok": training_count <= quota.max_training_concurrency,
            },
        }

    if db is not None:
        return _check(db)
    with get_db() as session:
        if session is None:
            raise RuntimeError("Database unavailable")
        return _check(session)


def ensure_model_quota_available(
    tenant_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> None:
    """
    训练/注册新模型前调用：检查模型数和存储配额。

    Raises:
        HTTPException (429): 模型数或存储超限
    """
    status = check_hard_quota(tenant_id, db)
    mc = status["model_count"]
    if not mc["ok"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "ModelQuotaExceeded",
                "message": (
                    f"模型数量超限: 当前 {mc['current']} / 上限 {mc['limit']}。"
                    f"请删除旧版本后再训练新模型。"
                ),
                "current": mc["current"],
                "limit": mc["limit"],
            },
        )
    st = status["storage_mb"]
    if not st["ok"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "StorageQuotaExceeded",
                "message": (
                    f"存储配额超限: 当前 {st['current']:.2f}MB / 上限 {st['limit']}MB。"
                    f"请清理旧模型文件后再试。"
                ),
                "current_mb": st["current"],
                "limit_mb": st["limit"],
            },
        )


def _calculate_tenant_storage_usage(
    tenant_id: int,
    db: Optional[Session] = None,
) -> float:
    """
    计算租户存储用量（MB）：
    1. 优先从 ModelVersionORM.file_size_bytes 汇总（精确）
    2. 回退到扫描磁盘目录（兜底）
    """
    try:
        def _from_db(session: Session) -> Optional[float]:
            total_bytes = (
                session.query(
                    ModelVersionORM.file_size_bytes
                )
                .filter(ModelVersionORM.tenant_id == tenant_id)
                .all()
            )
            if total_bytes:
                total = sum(
                    (r[0] or 0) for r in total_bytes if r[0] is not None
                )
                return total / (1024 * 1024)
            return None

        usage_mb = None
        if db is not None:
            usage_mb = _from_db(db)
        else:
            with get_db() as session:
                if session is not None:
                    usage_mb = _from_db(session)

        if usage_mb is not None:
            return usage_mb

        try:
            tenant_dir = get_tenant_model_dir(tenant_id)
            total_bytes = 0
            for f in tenant_dir.rglob("*"):
                if f.is_file():
                    total_bytes += f.stat().st_size
            return total_bytes / (1024 * 1024)
        except Exception:
            return 0.0

    except Exception as e:
        logger.warning(f"Failed to calculate storage usage for tenant {tenant_id}: {e}")
        return 0.0


def sync_tenant_storage_usage(tenant_id: int, db: Session) -> None:
    """
    同步租户存储用量到 TenantQuota.current_storage_mb。
    模型注册/删除后调用。
    """
    try:
        usage_mb = _calculate_tenant_storage_usage(tenant_id, db)
        quota = (
            db.query(TenantQuota)
            .filter(TenantQuota.tenant_id == tenant_id)
            .first()
        )
        if quota:
            quota.current_storage_mb = round(usage_mb, 2)
    except Exception as e:
        logger.warning(f"Failed to sync storage usage for tenant {tenant_id}: {e}")


def sync_tenant_model_count(tenant_id: int, db: Session) -> None:
    """
    同步租户当前模型数量到 TenantQuota.current_model_count。
    """
    try:
        active_count = (
            db.query(ModelVersionORM)
            .filter(
                ModelVersionORM.tenant_id == tenant_id,
                ModelVersionORM.is_active == True,
            )
            .count()
        )
        quota = (
            db.query(TenantQuota)
            .filter(TenantQuota.tenant_id == tenant_id)
            .first()
        )
        if quota:
            quota.current_model_count = active_count
    except Exception as e:
        logger.warning(f"Failed to sync model count for tenant {tenant_id}: {e}")


# ============================================================
# 一次性查询 + 租户权限校验辅助（单条）
# ============================================================

def get_one_or_404(
    db: Session,
    model_class: Type[T],
    record_id: Any,
    id_column: str = "id",
) -> T:
    """
    查询单条记录并强制校验租户权限。跨租户/不存在 → 404。

    超级管理员审计模式：允许跨租户读取（middleware已拦截写入）。

    Usage:
        bolt = get_one_or_404(db, BoltData, 12345)

    Args:
        db: 数据库会话
        model_class: ORM 模型类
        record_id: 记录ID
        id_column: 主键列名，默认 "id"

    Returns:
        ORM 实例

    Raises:
        HTTPException: 404
    """
    column = getattr(model_class, id_column)
    record = db.query(model_class).filter(column == record_id).first()

    if record is None:
        raise not_found_404()

    if hasattr(model_class, "tenant_id"):
        enforce_tenant_access(
            resource_tenant_id=getattr(record, "tenant_id"),
            resource_id=record_id,
            resource_type=model_class.__name__,
        )

    return record
