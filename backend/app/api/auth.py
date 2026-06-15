"""
API认证授权模块

提供API接口的认证和授权功能。

功能:
1. API密钥认证（X-API-Key header）
2. 权限粒度控制: read / write / admin
3. 按Key配置的速率限制，超限返回429
4. 密钥轮换、过期时间
5. 审计日志（谁、何时、调用了什么接口）
6. 健康检查 /health 公开免鉴权

权限映射:
- read:   预测查询、健康检查、模型信息查询
- write:  训练、策略配置、标注导入、告警规则管理
- admin:  模型版本管理、备份、API密钥管理、审计

使用示例:
    from app.api.auth import verify_api_key, require_permission

    @router.get("/protected")
    async def protected(key_info: Dict = Depends(verify_api_key)):
        pass

    @router.post("/admin", dependencies=[Depends(require_permission("admin"))])
    async def admin_action():
        pass
"""

import os
import time
import hashlib
import secrets
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from functools import wraps
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.utils.config import config


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

PERMISSION_HIERARCHY = {"read": 0, "write": 1, "admin": 2}

ENDPOINT_PERMISSION_MAP = {
    "read": [
        "/predict/bolt", "/predict/flange", "/predict/batch",
        "/risk/assess", "/forecast/monthly",
        "/model/info", "/model/versions", "/model/train/status",
        "/model/train/sessions",
        "/health", "/strategy/config",
        "/strategy/config/list", "/strategy/config/audit",
        "/alert/rules", "/alert/events",
        "/alert/subscriptions", "/notification/channels",
        "/notification/logs", "/work-orders",
        "/audit/records", "/data-quality/check",
        "/data-quality/score", "/data-quality/history",
        "/data-quality/problem-sensors", "/data-quality/anomalies",
        "/data-quality/report/latest",
        "/federated/server/status", "/federated/client/status",
        "/federated/round/status", "/federated/model/history",
        "/anomaly/list", "/anomaly/statistics",
        "/cmms/configs", "/cmms/sync-logs",
    ],
    "write": [
        "/model/train", "/model/train/enhanced",
        "/strategy/config", "/strategy/config/rollback",
        "/strategy/config/override",
        "/alert/rules", "/alert/events",
        "/alert/upgrade/trigger", "/alert/subscriptions",
        "/notification/channels", "/work-orders",
        "/work-orders/disposals", "/work-orders/retests",
        "/model/label/import",
        "/federated/client/register", "/federated/round/start",
        "/federated/round/aggregate", "/federated/client/model/download",
        "/federated/client/update/upload", "/federated/client/train/local",
        "/federated/config/privacy", "/federated/config/aggregator",
        "/data-quality/batch-check", "/data-quality/adjust-confidence",
        "/data-quality/report/generate",
        "/anomaly/confirm", "/anomaly/false-positive",
        "/cmms/sync/work-order", "/cmms/webhook",
    ],
    "admin": [
        "/model/activate", "/model/rollback",
        "/model/versions/cleanup",
        "/audit/cleanup", "/audit/export",
        "/audit/records/retention",
    ],
}

PUBLIC_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


def _get_required_permission(path: str, method: str) -> Optional[str]:
    if path in PUBLIC_PATHS:
        return None
    for perm in ("admin", "write", "read"):
        for prefix in ENDPOINT_PERMISSION_MAP.get(perm, []):
            if path.startswith(prefix):
                return perm
    return "read"


@dataclass
class RateLimitInfo:
    requests: int
    window_start: float
    blocked_until: Optional[float] = None


class PerKeyRateLimiter:
    def __init__(self, default_rate_limit: int = 1000):
        self.default_rate_limit = default_rate_limit
        self._hour_counters: Dict[str, RateLimitInfo] = {}
        self._key_limits: Dict[str, int] = {}
        self._lock = threading.Lock()

    def set_key_limit(self, key_id: str, limit: int):
        with self._lock:
            self._key_limits[key_id] = limit

    def remove_key_limit(self, key_id: str):
        with self._lock:
            self._key_limits.pop(key_id, None)
            self._hour_counters.pop(key_id, None)

    def check_rate_limit(self, key_id: str) -> None:
        with self._lock:
            limit = self._key_limits.get(key_id, self.default_rate_limit)
            current_time = time.time()
            info = self._hour_counters.get(key_id)
            if info is None:
                info = RateLimitInfo(requests=0, window_start=current_time)
                self._hour_counters[key_id] = info

            if current_time - info.window_start > 3600:
                info.requests = 0
                info.window_start = current_time

            info.requests += 1

            if info.requests > limit:
                retry_after = int(3600 - (current_time - info.window_start))
                logger.warning(f"速率限制触发: key={key_id}, limit={limit}/h, used={info.requests}")
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "RateLimitExceeded",
                        "message": f"已达到每小时请求限制({limit} req/h)，请稍后重试",
                        "retry_after": max(1, retry_after),
                        "limit": limit,
                        "remaining": 0,
                    },
                )

    def get_remaining(self, key_id: str) -> Dict[str, int]:
        with self._lock:
            limit = self._key_limits.get(key_id, self.default_rate_limit)
            info = self._hour_counters.get(key_id)
            used = info.requests if info and (time.time() - info.window_start <= 3600) else 0
            return {"limit": limit, "remaining": max(0, limit - used), "used": used}

    def get_status(self, key_id: str, limit: int) -> Dict[str, int]:
        with self._lock:
            info = self._hour_counters.get(key_id)
            used = info.requests if info and (time.time() - info.window_start <= 3600) else 0
            return {"remaining": max(0, limit - used), "used": used}


class APIKeyManager:
    def __init__(self):
        auth_config = config.get('auth', {})
        self.enabled = auth_config.get('enabled', False)
        self.master_key = auth_config.get('master_key', '')

        self._valid_keys: Dict[str, Dict[str, Any]] = {}
        self._key_expiry: Dict[str, Optional[datetime]] = {}
        self._rotation_pairs: Dict[str, str] = {}

        for key_config in auth_config.get('api_keys', []):
            key_str = key_config['key']
            expires_at = None
            if key_config.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(key_config['expires_at'])
                except (ValueError, TypeError):
                    pass
            self._valid_keys[key_str] = {
                'key_id': key_config.get('key_id', hashlib.md5(key_str.encode()).hexdigest()[:12]),
                'name': key_config.get('name', 'unnamed'),
                'permissions': key_config.get('permissions', ['read']),
                'rate_limit': key_config.get('rate_limit', 1000),
                'created_at': key_config.get('created_at', datetime.now().isoformat()),
                'expires_at': expires_at.isoformat() if expires_at else None,
            }
            self._key_expiry[key_str] = expires_at

        if self.master_key:
            self._valid_keys[self.master_key] = {
                'key_id': 'master',
                'name': 'master',
                'permissions': ['read', 'write', 'admin'],
                'rate_limit': 0,
                'created_at': datetime.now().isoformat(),
                'expires_at': None,
            }
            self._key_expiry[self.master_key] = None

    def add_key(self, key_str: str, key_info: Dict[str, Any], expires_at: Optional[datetime] = None):
        self._valid_keys[key_str] = key_info
        self._key_expiry[key_str] = expires_at

    def revoke_key(self, key_str: str) -> bool:
        if key_str in self._valid_keys:
            del self._valid_keys[key_str]
            self._key_expiry.pop(key_str, None)
            self._rotation_pairs.pop(key_str, None)
            return True
        return False

    def rotate_key(self, old_key: str) -> Optional[tuple]:
        old_info = self._valid_keys.get(old_key)
        if not old_info:
            return None
        new_key = secrets.token_hex(16)
        new_info = dict(old_info)
        new_info['key_id'] = hashlib.md5(new_key.encode()).hexdigest()[:12]
        new_info['created_at'] = datetime.now().isoformat()
        old_expiry = self._key_expiry.get(old_key)
        grace_expires = datetime.now() + timedelta(hours=1)
        self._valid_keys[new_key] = new_info
        self._key_expiry[new_key] = old_expiry
        self._rotation_pairs[old_key] = new_key
        self._rotation_pairs[new_key] = old_key
        return new_key, new_info, grace_expires

    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return {'name': 'anonymous', 'permissions': ['read', 'write', 'admin'], 'key_id': 'anonymous'}

        key_info = self._valid_keys.get(api_key)
        if not key_info:
            return None

        expires_at = self._key_expiry.get(api_key)
        if expires_at and datetime.now() > expires_at:
            logger.warning(f"API密钥已过期: {key_info.get('name', 'unknown')}")
            return None

        return key_info

    def has_permission(self, api_key: str, permission: str) -> bool:
        key_info = self.validate_key(api_key)
        if not key_info:
            return False
        key_perms = key_info.get('permissions', [])
        required_level = PERMISSION_HIERARCHY.get(permission, 99)
        for p in key_perms:
            if PERMISSION_HIERARCHY.get(p, -1) >= required_level:
                return True
        return permission in key_perms

    def get_key_rate_limit(self, api_key: str) -> int:
        key_info = self._valid_keys.get(api_key)
        if key_info:
            return key_info.get('rate_limit', 1000)
        return 1000

    def list_keys(self) -> List[Dict[str, Any]]:
        result = []
        for key_str, info in self._valid_keys.items():
            display = dict(info)
            display['key_preview'] = key_str[:8] + '...' + key_str[-4:]
            display['expires_at'] = self._key_expiry.get(key_str)
            display['is_expired'] = False
            exp = self._key_expiry.get(key_str)
            if exp and datetime.now() > exp:
                display['is_expired'] = True
            result.append(display)
        return result

    @staticmethod
    def generate_api_key() -> str:
        return secrets.token_hex(16)


per_key_rate_limiter = PerKeyRateLimiter(default_rate_limit=1000)
api_key_manager = APIKeyManager()


class AuditLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._buffer: List[Dict[str, Any]] = []
            cls._instance._lock = threading.Lock()
        return cls._instance

    def log(
        self,
        key_id: str,
        key_name: str,
        method: str,
        path: str,
        status_code: int,
        client_ip: str = "",
        request_id: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "key_id": key_id,
            "key_name": key_name,
            "method": method,
            "path": path,
            "status_code": status_code,
            "client_ip": client_ip,
            "request_id": request_id,
            "extra": extra or {},
        }
        with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) > 1000:
                self._flush()

        logger.bind(
            key_id=key_id,
            method=method,
            path=path,
            status_code=status_code,
        ).info(f"API_AUDIT: {key_name}({key_id}) {method} {path} -> {status_code}")

    def _flush(self):
        try:
            from app.utils.database import get_db
            with get_db() as db:
                if db is None:
                    return
                for entry in self._buffer:
                    self._write_to_db(db, entry)
                db.commit()
        except Exception as e:
            logger.warning(f"审计日志刷写失败: {e}")
        finally:
            self._buffer.clear()

    @staticmethod
    def _write_to_db(db, entry: Dict[str, Any]):
        try:
            from app.utils.database import APIAuditLog
            record = APIAuditLog(
                key_id=entry.get("key_id", ""),
                key_name=entry.get("key_name", ""),
                method=entry.get("method", ""),
                path=entry.get("path", ""),
                status_code=entry.get("status_code", 0),
                client_ip=entry.get("client_ip", ""),
                request_id=entry.get("request_id", ""),
                extra_info=json.dumps(entry.get("extra", {}), ensure_ascii=False, default=str),
                create_time=datetime.now(),
            )
            db.add(record)
        except Exception as e:
            logger.warning(f"写入审计日志失败: {e}")

    def flush(self):
        with self._lock:
            self._flush()

    def query_logs(
        self,
        key_id: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple:
        try:
            from app.utils.database import get_db, APIAuditLog
            with get_db() as db:
                if db is None:
                    return [], 0
                query = db.query(APIAuditLog)
                if key_id:
                    query = query.filter(APIAuditLog.key_id == key_id)
                if method:
                    query = query.filter(APIAuditLog.method == method)
                if path:
                    query = query.filter(APIAuditLog.path.contains(path))
                if start_time:
                    query = query.filter(APIAuditLog.create_time >= start_time)
                if end_time:
                    query = query.filter(APIAuditLog.create_time <= end_time)
                total = query.count()
                records = query.order_by(
                    APIAuditLog.create_time.desc()
                ).offset(offset).limit(limit).all()
                return records, total
        except Exception as e:
            logger.error(f"查询审计日志失败: {e}")
            return [], 0


audit_logger = AuditLogger()


async def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
    request: Request = None,
) -> Dict[str, Any]:
    if not api_key_manager.enabled:
        return {
            'name': 'anonymous',
            'permissions': ['read', 'write', 'admin'],
            'key_id': 'anonymous',
        }

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "message": "缺少API密钥，请在请求头中提供 X-API-Key",
            },
        )

    key_info = api_key_manager.validate_key(api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "message": "无效或已过期的API密钥",
            },
        )

    rate_limit = key_info.get('rate_limit', 1000)
    if rate_limit and rate_limit > 0:
        key_id = key_info.get('key_id', 'unknown')
        per_key_rate_limiter.set_key_limit(key_id, rate_limit)
        try:
            per_key_rate_limiter.check_rate_limit(key_id)
        except HTTPException:
            audit_logger.log(
                key_id=key_info.get('key_id', ''),
                key_name=key_info.get('name', ''),
                method=request.method if request else '',
                path=str(request.url.path) if request else '',
                status_code=429,
                client_ip=request.client.host if request and request.client else '',
                extra={"reason": "rate_limit_exceeded"},
            )
            raise

    path = str(request.url.path) if request else ""
    required_perm = _get_required_permission(path, request.method if request else "GET")
    if required_perm and required_perm not in key_info.get('permissions', []):
        has_higher = any(
            PERMISSION_HIERARCHY.get(p, -1) >= PERMISSION_HIERARCHY.get(required_perm, 99)
            for p in key_info.get('permissions', [])
        )
        if not has_higher:
            audit_logger.log(
                key_id=key_info.get('key_id', ''),
                key_name=key_info.get('name', ''),
                method=request.method if request else '',
                path=path,
                status_code=403,
                client_ip=request.client.host if request and request.client else '',
                extra={"required": required_perm, "actual": key_info.get('permissions', [])},
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": f"缺少权限: {required_perm}（当前权限: {key_info.get('permissions', [])}）",
                    "required": required_perm,
                    "actual": key_info.get('permissions', []),
                },
            )

    return key_info


def require_permission(permission: str) -> Callable:
    async def _check_permission(
        key_info: Dict[str, Any] = Depends(verify_api_key),
    ) -> Dict[str, Any]:
        key_perms = key_info.get('permissions', [])
        required_level = PERMISSION_HIERARCHY.get(permission, 99)
        has_access = permission in key_perms or any(
            PERMISSION_HIERARCHY.get(p, -1) >= required_level
            for p in key_perms
        )
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": f"缺少权限: {permission}（当前权限: {key_perms}）",
                    "required": permission,
                    "actual": key_perms,
                },
            )
        return key_info
    return _check_permission


class RateLimiter:
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        block_duration: int = 300,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.block_duration = block_duration
        self._minute_counters: Dict[str, RateLimitInfo] = defaultdict(
            lambda: RateLimitInfo(requests=0, window_start=time.time())
        )
        self._hour_counters: Dict[str, RateLimitInfo] = defaultdict(
            lambda: RateLimitInfo(requests=0, window_start=time.time())
        )

    def _get_client_id(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return hashlib.md5(api_key.encode()).hexdigest()[:16]
        client_ip = request.client.host if request.client else "unknown"
        return client_ip

    def check_rate_limit(self, request: Request) -> bool:
        client_id = self._get_client_id(request)
        current_time = time.time()
        minute_info = self._minute_counters[client_id]
        if current_time - minute_info.window_start > 60:
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
                    "retry_after": self.block_duration,
                },
            )
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
                    "retry_after": 3600 - (current_time - hour_info.window_start),
                },
            )
        return True

    def get_remaining(self, request: Request) -> Dict[str, int]:
        client_id = self._get_client_id(request)
        minute_info = self._minute_counters.get(client_id)
        hour_info = self._hour_counters.get(client_id)
        return {
            "minute_remaining": max(0, self.requests_per_minute - (minute_info.requests if minute_info else 0)),
            "hour_remaining": max(0, self.requests_per_hour - (hour_info.requests if hour_info else 0)),
        }


rate_limiter = RateLimiter()


async def check_rate_limit(request: Request) -> bool:
    return rate_limiter.check_rate_limit(request)


def require_api_key(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, request: Request = None, **kwargs):
        api_key = request.headers.get("X-API-Key") if request else None
        key_info = api_key_manager.validate_key(api_key)
        if api_key_manager.enabled and not key_info:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return await func(*args, **kwargs)
    return wrapper


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
