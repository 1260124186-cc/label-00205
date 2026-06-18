"""
中间件模块

提供请求级别的中间件功能：
1. Request ID 生成和传递
2. 请求指标采集（Prometheus）
3. 结构化日志上下文

使用示例:
    from app.middleware import RequestContextMiddleware, get_request_id

    # 在 FastAPI 应用中添加中间件
    app.add_middleware(RequestContextMiddleware)

    # 获取当前请求 ID
    request_id = get_request_id()
"""

import time
import uuid
import json
import contextvars
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

from app.core.prometheus import metrics

# 请求上下文变量
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')
_bolt_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('bolt_id', default='')
_request_start_time_var: contextvars.ContextVar[float] = contextvars.ContextVar('request_start_time', default=0.0)

# 租户上下文变量
_tenant_id_var: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar('tenant_id', default=None)
_user_id_var: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar('user_id', default=None)
_user_role_var: contextvars.ContextVar[str] = contextvars.ContextVar('user_role', default='')
_is_super_admin_var: contextvars.ContextVar[bool] = contextvars.ContextVar('is_super_admin', default=False)
_is_audit_mode_var: contextvars.ContextVar[bool] = contextvars.ContextVar('is_audit_mode', default=False)
_audit_tenant_id_var: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar('audit_tenant_id', default=None)


def get_request_id() -> str:
    """获取当前请求的 request_id"""
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求的 request_id"""
    _request_id_var.set(request_id)


def get_bolt_id() -> str:
    """获取当前请求关联的 bolt_id"""
    return _bolt_id_var.get()


def set_bolt_id(bolt_id: str) -> None:
    """设置当前请求关联的 bolt_id"""
    _bolt_id_var.set(bolt_id)


def get_tenant_id() -> Optional[int]:
    """获取当前请求的 tenant_id（考虑审计模式）"""
    if _is_audit_mode_var.get():
        return _audit_tenant_id_var.get()
    return _tenant_id_var.get()


def set_tenant_id(tenant_id: Optional[int]) -> None:
    """设置当前请求的 tenant_id"""
    _tenant_id_var.set(tenant_id)


def get_user_id() -> Optional[int]:
    """获取当前请求的 user_id"""
    return _user_id_var.get()


def set_user_id(user_id: Optional[int]) -> None:
    """设置当前请求的 user_id"""
    _user_id_var.set(user_id)


def get_user_role() -> str:
    """获取当前请求的 user_role"""
    return _user_role_var.get()


def set_user_role(role: str) -> None:
    """设置当前请求的 user_role"""
    _user_role_var.set(role)


def is_super_admin() -> bool:
    """检查当前用户是否为超级管理员"""
    return _is_super_admin_var.get()


def set_is_super_admin(value: bool) -> None:
    """设置当前用户是否为超级管理员"""
    _is_super_admin_var.set(value)


def is_audit_mode() -> bool:
    """检查当前是否为审计模式"""
    return _is_audit_mode_var.get()


def set_audit_mode(audit_tenant_id: Optional[int]) -> None:
    """设置审计模式和目标租户ID"""
    _is_audit_mode_var.set(True)
    _audit_tenant_id_var.set(audit_tenant_id)


def clear_audit_mode() -> None:
    """清除审计模式"""
    _is_audit_mode_var.set(False)
    _audit_tenant_id_var.set(None)


def get_audit_tenant_id() -> Optional[int]:
    """获取审计模式下的目标租户ID"""
    return _audit_tenant_id_var.get()


def get_effective_tenant_id() -> Optional[int]:
    """获取有效的租户ID（审计模式下返回审计租户，否则返回当前租户）"""
    return get_tenant_id()


def get_request_context() -> Dict[str, Any]:
    """获取请求上下文字典（用于日志）"""
    return {
        'request_id': get_request_id(),
        'bolt_id': get_bolt_id(),
        'tenant_id': get_effective_tenant_id(),
        'user_id': get_user_id(),
        'user_role': get_user_role(),
        'is_super_admin': is_super_admin(),
        'is_audit_mode': is_audit_mode(),
    }


def set_tenant_context(
    tenant_id: Optional[int],
    user_id: Optional[int] = None,
    role: str = '',
    is_super_admin: bool = False,
) -> None:
    """批量设置租户上下文"""
    set_tenant_id(tenant_id)
    set_user_id(user_id)
    set_user_role(role)
    set_is_super_admin(is_super_admin)


def clear_tenant_context() -> None:
    """清除租户上下文"""
    set_tenant_id(None)
    set_user_id(None)
    set_user_role('')
    set_is_super_admin(False)
    clear_audit_mode()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件

    为每个请求生成唯一的 request_id，并记录请求指标。

    功能:
    1. 生成/传递 X-Request-ID
    2. 记录请求开始时间
    3. 采集 HTTP 请求指标（Prometheus）
    4. 计算请求耗时
    """

    async def dispatch(self, request: Request, call_next):
        # 从请求头获取或生成 request_id
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        _request_id_var.set(request_id)

        # 记录开始时间
        start_time = time.time()
        _request_start_time_var.set(start_time)

        # 获取请求路径（去掉查询参数）
        path = request.url.path
        method = request.method

        # 结构化日志 - 请求开始
        logger.bind(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=request.client.host if request.client else 'unknown'
        ).info(f"Request started: {method} {path}")

        try:
            # 处理请求
            response = await call_next(request)

            # 计算耗时
            duration = time.time() - start_time

            # 获取状态码
            status_code = str(response.status_code)

            # 添加 request_id 到响应头
            response.headers['X-Request-ID'] = request_id

            # 记录 Prometheus 指标
            metrics.record_http_request(
                method=method,
                path=path,
                status_code=status_code,
                duration=duration
            )

            # 结构化日志 - 请求完成
            logger.bind(
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2)
            ).info(f"Request completed: {method} {path} - {status_code}")

            return response

        except Exception as e:
            # 计算耗时
            duration = time.time() - start_time

            # 记录错误指标
            metrics.record_http_request(
                method=method,
                path=path,
                status_code="500",
                duration=duration
            )

            # 结构化日志 - 请求错误
            logger.bind(
                request_id=request_id,
                method=method,
                path=path,
                duration_ms=round(duration * 1000, 2),
                error=str(e)
            ).exception(f"Request failed: {method} {path}")

            raise


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    租户上下文中间件

    为每个请求注入租户上下文：
    1. 从 JWT (Authorization: Bearer) 或 X-Tenant-API-Key 头解析租户ID
    2. 支持超级管理员审计模式（X-Audit-Tenant-Id 头）
    3. 将租户ID注入 contextvars，供下游业务代码使用

    认证优先级:
    1. X-Tenant-API-Key: 租户 API Key 认证
    2. Authorization: Bearer JWT 令牌认证
    3. 支持超级管理员通过 X-Audit-Tenant-Id 进入审计模式

    安全策略:
    - 跨租户访问返回 404（非 403，防止枚举攻击
    - 超级管理员审计模式为只读
    """

    PUBLIC_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"}

    SUPER_ADMIN_ROLES = {"super_admin", "platform_admin"}

    WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        clear_tenant_context()

        tenant_id = None
        user_id = None
        user_role = ""
        is_super_admin_flag = False

        try:
            tenant_id, user_id, user_role, is_super_admin_flag = await self._resolve_tenant_context(request)

            if tenant_id:
                set_tenant_context(tenant_id, user_id, user_role, is_super_admin_flag)

                audit_tenant_id_header = request.headers.get("X-Audit-Tenant-Id")
                if audit_tenant_id_header and is_super_admin_flag:
                    try:
                        audit_tenant_id = int(audit_tenant_id_header)
                        from app.utils.database import get_db, Tenant
                        with get_db() as db:
                            if db is not None:
                                target_tenant = db.query(Tenant).filter(
                                    Tenant.id == audit_tenant_id,
                                    Tenant.status == "active"
                                ).first()
                                if target_tenant:
                                    set_audit_mode(audit_tenant_id)
                                    logger.bind(
                                        request_id=get_request_id(),
                                        tenant_id=tenant_id,
                                        audit_tenant_id=audit_tenant_id
                                    ).info(f"Super admin audit mode: tenant_id={audit_tenant_id}")
                                else:
                                    logger.bind(
                                        request_id=get_request_id(),
                                        audit_tenant_id=audit_tenant_id
                                    ).warning(f"Audit target tenant not found or inactive: {audit_tenant_id}")
                    except (ValueError, TypeError):
                        pass

                if request.method in self.WRITE_METHODS and is_audit_mode():
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=403,
                        detail={"error": "Forbidden", "message": "审计模式为只读，不允许修改操作"}
                    )

                if request.method in self.WRITE_METHODS and not is_super_admin_flag:
                    self._check_api_quota(tenant_id)

            logger.bind(
                request_id=get_request_id(),
                tenant_id=get_effective_tenant_id(),
                user_id=user_id,
                user_role=user_role,
                is_audit_mode=is_audit_mode()
            ).debug(f"Tenant context resolved: tenant_id={get_effective_tenant_id()}")

        except Exception as e:
            if isinstance(e, Exception) and e.__class__.__name__ == 'HTTPException':
                raise
            logger.bind(
                request_id=get_request_id(),
                error=str(e)
            ).warning(f"Failed to resolve tenant context: {e}")

        response = await call_next(request)

        clear_tenant_context()

        return response

    def _check_api_quota(self, tenant_id: int) -> None:
        """检查API调用配额"""
        try:
            from app.services.tenant import QuotaService
            qs = QuotaService()
            quota = qs.get_quota(tenant_id)
            if quota and not qs.check_quota(tenant_id, 'api_call'):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "QuotaExceeded",
                        "message": f"今日API调用已达上限 ({quota.max_api_calls_per_day})",
                        "resource": "api_call",
                    }
                )
        except Exception as e:
            if e.__class__.__name__ == 'HTTPException':
                raise

    async def _resolve_tenant_context(
        self, request: Request
    ) -> tuple[Optional[int], Optional[int], str, bool]:
        api_key = request.headers.get("X-Tenant-API-Key")
        if api_key:
            try:
                from app.services.tenant import TenantAPIKeyService
                svc = TenantAPIKeyService()
                key_info = svc.validate_api_key(api_key)
                if key_info:
                    from app.services.tenant import QuotaService
                    QuotaService().increment_api_calls(key_info["tenant_id"])
                    return key_info["tenant_id"], key_info.get("user_id"), "api_key", False
            except Exception as e:
                logger.warning(f"Tenant API Key validation failed: {e}")

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header[7:]
                from app.services.sso.jwt_manager import jwt_manager
                payload = jwt_manager.verify_token(token, "access")
                if payload:
                    subject = jwt_manager.get_subject(payload)
                    if subject:
                        tenant_id = subject.get("tenant_id")
                        user_id = subject.get("user_id")
                        role = subject.get("role", "")
                        is_super = role in self.SUPER_ADMIN_ROLES
                        return tenant_id, user_id, role, is_super
            except Exception as e:
                logger.warning(f"JWT validation failed: {e}")

        tenant_token = request.headers.get("X-Tenant-Token")
        if tenant_token:
            try:
                from app.api.auth import verify_tenant_token
                token_info = verify_tenant_token(tenant_token)
                if token_info:
                    role = token_info.get("role", "")
                    is_super = role in self.SUPER_ADMIN_ROLES
                    return token_info["tenant_id"], token_info.get("user_id"), role, is_super
            except Exception as e:
                logger.warning(f"Tenant token validation failed: {e}")

        return None, None, "", False


class StructuredLogFilter:
    """
    结构化日志过滤器

    为 loguru 日志添加上下文信息。
    """

    @staticmethod
    def patch(record: Dict[str, Any]) -> None:
        """
        为日志记录添加上下文信息

        Args:
            record: loguru 日志记录字典
        """
        request_id = get_request_id()
        if request_id:
            record['extra']['request_id'] = request_id

        bolt_id = get_bolt_id()
        if bolt_id:
            record['extra']['bolt_id'] = bolt_id

        tenant_id = get_effective_tenant_id()
        if tenant_id is not None:
            record['extra']['tenant_id'] = tenant_id

        user_id = get_user_id()
        if user_id is not None:
            record['extra']['user_id'] = user_id

        user_role = get_user_role()
        if user_role:
            record['extra']['user_role'] = user_role

        if is_super_admin():
            record['extra']['is_super_admin'] = True

        if is_audit_mode():
            record['extra']['is_audit_mode'] = True


def setup_structured_logging() -> None:
    """
    配置结构化日志

    为 loguru 添加上下文信息。
    """
    import sys
    from loguru import logger

    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<yellow>request_id={extra[request_id]}</yellow> | "
        "<yellow>tenant_id={extra[tenant_id]}</yellow> | "
        "<yellow>user_id={extra[user_id]}</yellow> | "
        "<yellow>role={extra[user_role]}</yellow> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        backtrace=True,
        diagnose=True
    )

    logger.configure(
        extra={
            "request_id": "",
            "bolt_id": "",
            "tenant_id": "",
            "user_id": "",
            "user_role": "",
            "is_super_admin": "",
            "is_audit_mode": "",
        }
    )

from app.middleware.tenant_isolation import (
    TenantIsolationMixin,
    enforce_tenant_ownership,
    require_tenant_context,
    require_write_permission,
    QuotaEnforcer,
    quota_enforcer,
    get_tenant_model_path,
    resolve_model_filename,
)

logger.info("Structured logging initialized")
