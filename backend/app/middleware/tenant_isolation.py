import os
from typing import Optional, Type, Any, Dict

from fastapi import HTTPException, Depends
from loguru import logger
from sqlalchemy.orm import Query

from app.middleware import (
    get_effective_tenant_id,
    is_super_admin,
    is_audit_mode,
    get_audit_tenant_id,
)


class TenantIsolationMixin:
    """
    租户隔离查询 Mixin

    为 Service 类提供自动租户隔离的查询方法。
    所有查询自动追加 tenant_id 过滤，审计模式下切换到审计租户。

    用法:
        class MyService(TenantIsolationMixin):
            def get_something(self, item_id: int):
                query = self.tenant_filter(db.query(MyModel)).filter(MyModel.id == item_id)
                return query.first()
    """

    def _get_tenant_id(self) -> Optional[int]:
        return get_effective_tenant_id()

    def tenant_filter(self, query: Query, model_class: Optional[Type] = None) -> Query:
        """
        为查询追加租户隔离过滤

        Args:
            query: SQLAlchemy 查询对象
            model_class: 模型类，如果不传则尝试从查询中推断

        Returns:
            追加了 tenant_id 过滤的查询
        """
        tenant_id = self._get_tenant_id()
        if tenant_id is None:
            return query

        if model_class is None:
            model_class = query.column_descriptions[0]['entity']
            if model_class is None:
                return query

        if hasattr(model_class, 'tenant_id'):
            return query.filter(model_class.tenant_id == tenant_id)

        return query

    def tenant_filter_with_org_tree(
        self,
        query: Query,
        model_class: Optional[Type] = None,
        org_node_id: Optional[int] = None,
    ) -> Query:
        """
        为查询追加租户隔离 + 组织树过滤

        如果指定了 org_node_id，则通过组织树解析该节点及其所有后代节点，
        将查询限定在组织树子集范围内。

        Args:
            query: SQLAlchemy 查询对象
            model_class: 模型类
            org_node_id: 组织节点ID（可选）

        Returns:
            追加了租户隔离和组织树过滤的查询
        """
        query = self.tenant_filter(query, model_class)

        if org_node_id is not None:
            try:
                from app.utils.database import get_db, OrganizationNode
                with get_db() as db:
                    if db is not None:
                        tenant_id = self._get_tenant_id()
                        node = db.query(OrganizationNode).filter(
                            OrganizationNode.id == org_node_id,
                            OrganizationNode.tenant_id == tenant_id,
                        ).first()
                        if node and node.path:
                            descendant_ids = [node.id]
                            descendants = db.query(OrganizationNode).filter(
                                OrganizationNode.tenant_id == tenant_id,
                                OrganizationNode.path.like(f"{node.path}/%"),
                            ).all()
                            descendant_ids.extend([d.id for d in descendants])
                            if model_class and hasattr(model_class, 'org_node_id'):
                                query = query.filter(model_class.org_node_id.in_(descendant_ids))
            except Exception as e:
                logger.warning(f"组织树过滤失败: {e}")

        return query

    def enforce_tenant_id(self, **kwargs) -> Dict[str, Any]:
        """
        在创建记录时自动注入 tenant_id

        Args:
            kwargs: 创建记录的参数字典

        Returns:
            注入了 tenant_id 的参数字典
        """
        tenant_id = self._get_tenant_id()
        if tenant_id is not None and 'tenant_id' not in kwargs:
            kwargs['tenant_id'] = tenant_id
        return kwargs


def enforce_tenant_ownership(resource_tenant_id: Optional[int]) -> None:
    """
    校验资源是否属于当前租户，跨租户访问抛出 404

    核心安全策略: 跨租户访问返回 404 而非 403，防止租户枚举攻击。
    超级管理员在审计模式下可以访问其他租户的数据（只读）。

    Args:
        resource_tenant_id: 资源所属的租户ID

    Raises:
        HTTPException: 404 如果资源不属于当前租户
    """
    if resource_tenant_id is None:
        return

    current_tenant_id = get_effective_tenant_id()

    if current_tenant_id is None:
        return

    if resource_tenant_id == current_tenant_id:
        return

    if is_super_admin() and is_audit_mode():
        return

    raise HTTPException(
        status_code=404,
        detail={"error": "Not Found", "message": "请求的资源不存在"}
    )


async def require_tenant_context():
    """
    FastAPI 依赖项：要求有效的租户上下文

    Raises:
        HTTPException: 401 如果没有租户上下文
    """
    tenant_id = get_effective_tenant_id()
    if tenant_id is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "需要租户认证"}
        )
    return tenant_id


async def require_write_permission():
    """
    FastAPI 依赖项：要求写权限（非审计模式）

    Raises:
        HTTPException: 403 如果处于审计模式
    """
    if is_audit_mode():
        raise HTTPException(
            status_code=403,
            detail={"error": "Forbidden", "message": "审计模式为只读，不允许修改操作"}
        )
    return True


class QuotaEnforcer:
    """
    配额硬限制执行器

    在模型训练、API 调用等关键操作前检查配额是否超限。
    支持的配额类型:
    - model: 模型数量
    - storage: 存储 GB
    - api_call: 日 API 调用
    - training: 训练并发数
    """

    def __init__(self):
        from app.services.tenant import QuotaService
        self.quota_service = QuotaService()

    def check_model_quota(self, tenant_id: Optional[int] = None) -> None:
        """
        检查模型数量配额

        Raises:
            HTTPException: 429 如果超过配额
        """
        tid = tenant_id or get_effective_tenant_id()
        if tid is None:
            return

        if not self.quota_service.check_quota(tid, 'model'):
            quota = self.quota_service.get_quota(tid)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "QuotaExceeded",
                    "message": f"模型数量已达上限 ({quota.max_models if quota else 'N/A'})",
                    "resource": "model",
                    "quota_type": "max_models",
                }
            )

    def check_storage_quota(self, tenant_id: Optional[int] = None, additional_mb: float = 0) -> None:
        """
        检查存储配额

        Args:
            tenant_id: 租户ID
            additional_mb: 预计额外需要的存储量 (MB)

        Raises:
            HTTPException: 429 如果超过配额
        """
        tid = tenant_id or get_effective_tenant_id()
        if tid is None:
            return

        quota = self.quota_service.get_quota(tid)
        if quota is None:
            return

        projected = quota.current_storage_mb + additional_mb
        if projected > quota.max_storage_mb:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "QuotaExceeded",
                    "message": f"存储空间已达上限 ({quota.max_storage_mb} MB)",
                    "resource": "storage",
                    "quota_type": "max_storage_mb",
                    "current_mb": quota.current_storage_mb,
                    "max_mb": quota.max_storage_mb,
                }
            )

    def check_api_quota(self, tenant_id: Optional[int] = None) -> None:
        """
        检查日 API 调用配额

        Raises:
            HTTPException: 429 如果超过配额
        """
        tid = tenant_id or get_effective_tenant_id()
        if tid is None:
            return

        if not self.quota_service.check_quota(tid, 'api_call'):
            quota = self.quota_service.get_quota(tid)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "QuotaExceeded",
                    "message": f"今日API调用已达上限 ({quota.max_api_calls_per_day if quota else 'N/A'})",
                    "resource": "api_call",
                    "quota_type": "max_api_calls_per_day",
                }
            )

    def check_training_concurrency(self, tenant_id: Optional[int] = None) -> None:
        """
        检查训练并发配额

        Raises:
            HTTPException: 429 如果超过并发上限
        """
        tid = tenant_id or get_effective_tenant_id()
        if tid is None:
            return

        try:
            from app.utils.database import get_db, TrainingLog
            with get_db() as db:
                if db is None:
                    return
                running_count = db.query(TrainingLog).filter(
                    TrainingLog.tenant_id == tid,
                    TrainingLog.status.in_(['pending', 'running']),
                ).count()

                quota = self.quota_service.get_quota(tid)
                if quota is None:
                    return

                max_concurrent = getattr(quota, 'max_training_concurrent', 2)
                if running_count >= max_concurrent:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "QuotaExceeded",
                            "message": f"训练并发数已达上限 ({max_concurrent})",
                            "resource": "training_concurrent",
                            "quota_type": "max_training_concurrent",
                            "current_running": running_count,
                        }
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"训练并发检查失败: {e}")

    def check_all_for_training(self, tenant_id: Optional[int] = None) -> None:
        """
        训练操作前的全面配额检查

        Raises:
            HTTPException: 429 如果任一配额超限
        """
        self.check_model_quota(tenant_id)
        self.check_training_concurrency(tenant_id)
        self.check_storage_quota(tenant_id, additional_mb=100)


def get_tenant_model_path(base_path: str, tenant_id: Optional[int], model_filename: str) -> str:
    """
    生成租户隔离的模型文件路径

    路径格式: trained_models/{tenant_id}/bolt_lstm_{id}.pt

    Args:
        base_path: 基础模型保存路径 (e.g. './trained_models')
        tenant_id: 租户ID
        model_filename: 模型文件名 (e.g. 'bolt_lstm_B001.pt')

    Returns:
        租户隔离的完整模型文件路径
    """
    if tenant_id is None:
        return os.path.join(base_path, model_filename)

    tenant_dir = os.path.join(base_path, str(tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)
    return os.path.join(tenant_dir, model_filename)


def resolve_model_filename(model_type: str, node_id: str) -> str:
    """
    根据模型类型和节点ID生成模型文件名

    Args:
        model_type: 模型类型 (bolt/flange)
        node_id: 节点ID

    Returns:
        模型文件名
    """
    if model_type == 'bolt':
        return f"bolt_lstm_{node_id}.pt"
    elif model_type == 'flange':
        return f"flange_attention_{node_id}.pt"
    else:
        return f"{model_type}_{node_id}.pt"


quota_enforcer = QuotaEnforcer()
