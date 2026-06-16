from typing import Optional, Dict, Any, List, Set
from datetime import datetime

from strawberry.types import Info
from strawberry.fastapi import GraphQLRouter
from fastapi import Request, HTTPException
from loguru import logger


ROLE_FIELD_PERMISSIONS: Dict[str, Set[str]] = {
    "tenant_admin": {
        "prediction", "health", "rul", "recent_anomalies",
        "work_orders", "knowledge_recommendations",
    },
    "admin": {
        "prediction", "health", "rul", "recent_anomalies",
        "work_orders", "knowledge_recommendations",
    },
    "operator": {
        "prediction", "health", "rul", "recent_anomalies",
        "work_orders",
    },
    "viewer": {
        "prediction", "health",
    },
    "api_key": {
        "prediction", "health", "rul", "recent_anomalies",
        "work_orders", "knowledge_recommendations",
    },
}

ANONYMOUS_FIELDS: Set[str] = {"prediction", "health"}


def get_tenant_context_from_request(request: Request) -> Dict[str, Any]:
    api_key = request.headers.get("X-Tenant-API-Key")
    token = request.headers.get("X-Tenant-Token")

    if api_key:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        key_info = svc.validate_api_key(api_key)
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

    if token:
        from app.api.auth import verify_tenant_token
        token_info = verify_tenant_token(token)
        if token_info:
            return {
                "tenant_id": token_info["tenant_id"],
                "user_id": token_info["user_id"],
                "username": token_info["username"],
                "role": token_info["role"],
                "permissions": _role_to_permissions(token_info["role"]),
                "auth_method": "token",
            }

    legacy_key = request.headers.get("X-API-Key")
    if legacy_key:
        from app.api.auth import api_key_manager
        key_info = api_key_manager.validate_key(legacy_key)
        if key_info:
            return {
                "tenant_id": None,
                "user_id": None,
                "role": "api_key",
                "permissions": key_info.get("permissions", ["read"]),
                "auth_method": "legacy_api_key",
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


def get_allowed_fields(role: str) -> Set[str]:
    return ROLE_FIELD_PERMISSIONS.get(role, ANONYMOUS_FIELDS)


def filter_fields(
    data: Dict[str, Any],
    allowed_fields: Set[str],
    all_field_names: Set[str],
) -> Dict[str, Any]:
    result = {}
    for key in all_field_names:
        if key in allowed_fields and key in data:
            result[key] = data[key]
        elif key in allowed_fields and key not in data:
            result[key] = None
    return result


def enforce_tenant_isolation(
    tenant_id: Optional[int],
    data: Dict[str, Any],
) -> Dict[str, Any]:
    if tenant_id is None:
        return data
    if "tenant_id" in data and data["tenant_id"] is not None:
        if data["tenant_id"] != tenant_id:
            logger.warning(
                f"Tenant isolation violation: expected={tenant_id}, "
                f"found={data['tenant_id']}"
            )
            return {}
    return data
