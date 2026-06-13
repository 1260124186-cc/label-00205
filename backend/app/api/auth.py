"""
API认证授权模块

提供API接口的认证和授权功能。

功能:
1. API密钥认证
2. JWT令牌认证
3. 速率限制
4. 权限控制

使用示例:
    from app.api.auth import require_api_key, RateLimiter
    
    @router.post("/predict")
    @require_api_key
    async def predict():
        pass
"""

import os
import time
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from functools import wraps
from collections import defaultdict
from dataclasses import dataclass

from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.utils.config import config


# API Key Header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass
class RateLimitInfo:
    """速率限制信息"""
    requests: int
    window_start: float
    blocked_until: Optional[float] = None


class RateLimiter:
    """
    速率限制器
    
    限制API请求频率，防止滥用。
    
    Attributes:
        requests_per_minute: 每分钟最大请求数
        requests_per_hour: 每小时最大请求数
        block_duration: 超限后的封禁时长（秒）
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.block_duration = block_duration
        
        # 请求计数器 {client_id: {window: RateLimitInfo}}
        self._minute_counters: Dict[str, RateLimitInfo] = defaultdict(
            lambda: RateLimitInfo(requests=0, window_start=time.time())
        )
        self._hour_counters: Dict[str, RateLimitInfo] = defaultdict(
            lambda: RateLimitInfo(requests=0, window_start=time.time())
        )
        
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用API Key，否则使用IP
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return hashlib.md5(api_key.encode()).hexdigest()[:16]
        
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
    
    def check_rate_limit(self, request: Request) -> bool:
        """
        检查速率限制
        
        Args:
            request: 请求对象
            
        Returns:
            bool: 是否允许请求
            
        Raises:
            HTTPException: 超过速率限制
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # 检查分钟限制
        minute_info = self._minute_counters[client_id]
        if current_time - minute_info.window_start > 60:
            # 重置窗口
            minute_info.requests = 0
            minute_info.window_start = current_time
        
        minute_info.requests += 1
        
        if minute_info.requests > self.requests_per_minute:
            logger.warning(f"速率限制触发(分钟): {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"请求过于频繁，请{self.block_duration}秒后重试",
                    "retry_after": self.block_duration
                }
            )
        
        # 检查小时限制
        hour_info = self._hour_counters[client_id]
        if current_time - hour_info.window_start > 3600:
            hour_info.requests = 0
            hour_info.window_start = current_time
        
        hour_info.requests += 1
        
        if hour_info.requests > self.requests_per_hour:
            logger.warning(f"速率限制触发(小时): {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": "已达到每小时请求限制，请稍后重试",
                    "retry_after": 3600 - (current_time - hour_info.window_start)
                }
            )
        
        return True
    
    def get_remaining(self, request: Request) -> Dict[str, int]:
        """获取剩余请求次数"""
        client_id = self._get_client_id(request)
        
        minute_info = self._minute_counters.get(client_id)
        hour_info = self._hour_counters.get(client_id)
        
        return {
            "minute_remaining": max(0, self.requests_per_minute - (minute_info.requests if minute_info else 0)),
            "hour_remaining": max(0, self.requests_per_hour - (hour_info.requests if hour_info else 0))
        }


class APIKeyManager:
    """
    API密钥管理器
    
    管理API密钥的生成、验证和权限控制。
    """
    
    def __init__(self):
        """初始化API密钥管理器"""
        auth_config = config.get('auth', {})
        self.enabled = auth_config.get('enabled', False)
        self.master_key = auth_config.get('master_key', '')
        
        # 从配置加载有效的API密钥
        self._valid_keys: Dict[str, Dict[str, Any]] = {}
        
        for key_config in auth_config.get('api_keys', []):
            self._valid_keys[key_config['key']] = {
                'name': key_config.get('name', 'unnamed'),
                'permissions': key_config.get('permissions', ['read']),
                'rate_limit': key_config.get('rate_limit', 1000),
                'created_at': key_config.get('created_at', datetime.now().isoformat())
            }
        
        # 添加主密钥
        if self.master_key:
            self._valid_keys[self.master_key] = {
                'name': 'master',
                'permissions': ['read', 'write', 'admin'],
                'rate_limit': float('inf'),
                'created_at': datetime.now().isoformat()
            }
    
    @staticmethod
    def generate_api_key() -> str:
        """
        生成新的API密钥
        
        Returns:
            str: 32字符的API密钥
        """
        return secrets.token_hex(16)
    
    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        验证API密钥
        
        Args:
            api_key: API密钥
            
        Returns:
            Dict: 密钥信息，如果无效则返回None
        """
        if not self.enabled:
            return {'name': 'anonymous', 'permissions': ['read', 'write']}
        
        return self._valid_keys.get(api_key)
    
    def has_permission(self, api_key: str, permission: str) -> bool:
        """
        检查权限
        
        Args:
            api_key: API密钥
            permission: 所需权限
            
        Returns:
            bool: 是否有权限
        """
        key_info = self.validate_key(api_key)
        if not key_info:
            return False
        
        return permission in key_info.get('permissions', [])


# 全局实例
rate_limiter = RateLimiter()
api_key_manager = APIKeyManager()


async def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
    request: Request = None
) -> Dict[str, Any]:
    """
    验证API密钥依赖
    
    Usage:
        @router.get("/protected")
        async def protected(key_info: Dict = Depends(verify_api_key)):
            pass
    """
    if not api_key_manager.enabled:
        return {'name': 'anonymous', 'permissions': ['read', 'write']}
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "message": "缺少API密钥，请在请求头中提供X-API-Key"
            }
        )
    
    key_info = api_key_manager.validate_key(api_key)
    
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "message": "无效的API密钥"
            }
        )
    
    return key_info


async def check_rate_limit(request: Request) -> bool:
    """
    速率限制依赖
    
    Usage:
        @router.get("/api")
        async def api(
            _: bool = Depends(check_rate_limit)
        ):
            pass
    """
    return rate_limiter.check_rate_limit(request)


def require_api_key(func: Callable) -> Callable:
    """
    API密钥装饰器
    
    Usage:
        @router.post("/predict")
        @require_api_key
        async def predict():
            pass
    """
    @wraps(func)
    async def wrapper(*args, request: Request = None, **kwargs):
        api_key = request.headers.get("X-API-Key") if request else None
        key_info = api_key_manager.validate_key(api_key)
        
        if api_key_manager.enabled and not key_info:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_permission(permission: str) -> Callable:
    """
    权限检查装饰器
    
    Usage:
        @router.post("/admin")
        @require_permission("admin")
        async def admin_action():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            api_key = request.headers.get("X-API-Key") if request else None
            
            if not api_key_manager.has_permission(api_key, permission):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Forbidden",
                        "message": f"缺少权限: {permission}"
                    }
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================
# 多租户认证与配额执行
# ============================================================

TENANT_API_KEY_HEADER = APIKeyHeader(name="X-Tenant-API-Key", auto_error=False)
TENANT_TOKEN_HEADER = APIKeyHeader(name="X-Tenant-Token", auto_error=False)

_tenant_tokens: Dict[str, Dict[str, Any]] = {}


def generate_tenant_token(tenant_id: int, user_id: int, username: str, role: str) -> str:
    token = secrets.token_hex(32)
    _tenant_tokens[token] = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "username": username,
        "role": role,
        "created_at": time.time(),
        "expires_at": time.time() + 86400,
    }
    return token


def verify_tenant_token(token: str) -> Optional[Dict[str, Any]]:
    info = _tenant_tokens.get(token)
    if not info:
        return None
    if time.time() > info["expires_at"]:
        _tenant_tokens.pop(token, None)
        return None
    return info


def revoke_tenant_token(token: str) -> None:
    _tenant_tokens.pop(token, None)


async def get_tenant_context(
    request: Request,
    tenant_api_key: Optional[str] = Security(TENANT_API_KEY_HEADER),
    tenant_token: Optional[str] = Security(TENANT_TOKEN_HEADER),
) -> Dict[str, Any]:
    """
    解析租户上下文依赖

    支持两种认证方式:
    1. X-Tenant-API-Key: 租户 API Key 认证
    2. X-Tenant-Token: 登录令牌认证

    优先使用 API Key, 其次使用 Token。
    无凭据时返回匿名上下文。
    """
    if tenant_api_key:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        key_info = svc.validate_api_key(tenant_api_key)
        if key_info:
            from app.services.tenant import QuotaService
            QuotaService().increment_api_calls(key_info["tenant_id"])
            return {
                "tenant_id": key_info["tenant_id"],
                "user_id": key_info.get("user_id"),
                "role": "api_key",
                "permissions": key_info.get("permissions", ["read"]),
                "auth_method": "api_key",
            }

    if tenant_token:
        token_info = verify_tenant_token(tenant_token)
        if token_info:
            return {
                "tenant_id": token_info["tenant_id"],
                "user_id": token_info["user_id"],
                "username": token_info["username"],
                "role": token_info["role"],
                "permissions": _role_to_permissions(token_info["role"]),
                "auth_method": "token",
            }

    return {
        "tenant_id": None,
        "user_id": None,
        "role": "anonymous",
        "permissions": [],
        "auth_method": "none",
    }


def _role_to_permissions(role: str) -> List[str]:
    mapping = {
        "tenant_admin": ["read", "write", "admin", "tenant_admin"],
        "admin": ["read", "write", "admin"],
        "operator": ["read", "write"],
        "viewer": ["read"],
    }
    return mapping.get(role, ["read"])


def require_tenant_auth(func: Callable) -> Callable:
    """
    要求租户认证装饰器

    Usage:
        @router.post("/predict")
        @require_tenant_auth
        async def predict():
            pass
    """
    @wraps(func)
    async def wrapper(*args, request: Request = None, **kwargs):
        api_key = None
        token = None
        if request:
            api_key = request.headers.get("X-Tenant-API-Key")
            token = request.headers.get("X-Tenant-Token")

        if api_key:
            from app.services.tenant import TenantAPIKeyService
            svc = TenantAPIKeyService()
            key_info = svc.validate_api_key(api_key)
            if not key_info:
                raise HTTPException(
                    status_code=401,
                    detail={"error": "Unauthorized", "message": "无效的租户API密钥"},
                )
            return await func(*args, **kwargs)

        if token:
            token_info = verify_tenant_token(token)
            if not token_info:
                raise HTTPException(
                    status_code=401,
                    detail={"error": "Unauthorized", "message": "无效或过期的租户令牌"},
                )
            return await func(*args, **kwargs)

        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "缺少租户认证凭据"},
        )

    return wrapper


def require_tenant_role(*roles: str) -> Callable:
    """
    要求特定租户角色装饰器

    Usage:
        @router.post("/admin/config")
        @require_tenant_role("tenant_admin", "admin")
        async def admin_config():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            token = request.headers.get("X-Tenant-Token") if request else None
            api_key_str = request.headers.get("X-Tenant-API-Key") if request else None

            user_role = None
            if token:
                token_info = verify_tenant_token(token)
                if token_info:
                    user_role = token_info["role"]
            elif api_key_str:
                from app.services.tenant import TenantAPIKeyService
                svc = TenantAPIKeyService()
                key_info = svc.validate_api_key(api_key_str)
                if key_info:
                    user_role = "api_key"

            if user_role not in roles and user_role != "tenant_admin":
                raise HTTPException(
                    status_code=403,
                    detail={"error": "Forbidden", "message": f"需要角色: {', '.join(roles)}"},
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def check_tenant_quota(resource: str) -> Callable:
    """
    租户配额检查装饰器

    Usage:
        @router.post("/model/train")
        @check_tenant_quota("model")
        async def train():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            tenant_id = None
            if request:
                token = request.headers.get("X-Tenant-Token")
                api_key_str = request.headers.get("X-Tenant-API-Key")
                if token:
                    token_info = verify_tenant_token(token)
                    if token_info:
                        tenant_id = token_info["tenant_id"]
                elif api_key_str:
                    from app.services.tenant import TenantAPIKeyService
                    svc = TenantAPIKeyService()
                    key_info = svc.validate_api_key(api_key_str)
                    if key_info:
                        tenant_id = key_info["tenant_id"]

            if tenant_id:
                from app.services.tenant import QuotaService
                quota_svc = QuotaService()
                if not quota_svc.check_quota(tenant_id, resource):
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "QuotaExceeded",
                            "message": f"租户 {resource} 配额已用尽",
                        },
                    )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
