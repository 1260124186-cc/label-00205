"""
统一认证模块

整合多种认证方式：
1. X-API-Key: 全局 API Key（原有）
2. X-Tenant-API-Key: 租户 API Key（原有）
3. X-Tenant-Token: 租户登录 Token（原有）
4. Authorization: Bearer JWT（新增，SSO 登录用）
5. X-Service-Account-Key: 服务账号 API Key（新增）

优先级（先匹配先通过）：
1. Bearer JWT（Authorization header）
2. 服务账号 API Key
3. 租户 API Key
4. 租户 Token
5. 全局 API Key
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.utils.config import config
from app.services.sso import JWTManager, jwt_manager
from app.services.sso import SessionManager, session_manager
from app.services.sso import ServiceAccountService, service_account_service


JWT_BEARER = HTTPBearer(auto_error=False)
SERVICE_ACCOUNT_KEY_HEADER = APIKeyHeader(name="X-Service-Account-Key", auto_error=False)


class UnifiedAuth:
    """
    统一认证处理器

    支持多种认证方式并存，提供统一的身份上下文。
    """

    def __init__(self):
        auth_config = config.get('auth', {})
        self.enabled = auth_config.get('enabled', False)
        self.sso_enabled = auth_config.get('sso_enabled', True)
        self.service_account_enabled = auth_config.get('service_account_enabled', True)

    def resolve_identity(
        self,
        request: Request,
        bearer_credentials: Optional[HTTPAuthorizationCredentials] = None,
        service_account_key: Optional[str] = None,
        tenant_api_key: Optional[str] = None,
        tenant_token: Optional[str] = None,
        global_api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        解析请求身份，支持多种认证方式

        Args:
            request: 请求对象
            bearer_credentials: Bearer Token 凭证
            service_account_key: 服务账号 API Key
            tenant_api_key: 租户 API Key
            tenant_token: 租户 Token
            global_api_key: 全局 API Key

        Returns:
            统一的身份上下文字典
        """
        client_ip = request.client.host if request and request.client else ''

        # 1. 尝试 JWT Bearer 认证（SSO 登录用户）
        if self.sso_enabled and bearer_credentials and bearer_credentials.credentials:
            identity = self._verify_jwt(bearer_credentials.credentials)
            if identity:
                identity['auth_method'] = 'jwt'
                identity['client_ip'] = client_ip
                return identity

        # 2. 尝试服务账号 API Key 认证
        if self.service_account_enabled and service_account_key:
            identity = self._verify_service_account(service_account_key, client_ip)
            if identity:
                identity['auth_method'] = 'service_account'
                identity['client_ip'] = client_ip
                return identity

        # 3. 尝试租户 API Key 认证（原有）
        if tenant_api_key:
            identity = self._verify_tenant_api_key(tenant_api_key)
            if identity:
                identity['auth_method'] = 'tenant_api_key'
                identity['client_ip'] = client_ip
                return identity

        # 4. 尝试租户 Token 认证（原有）
        if tenant_token:
            identity = self._verify_tenant_token(tenant_token)
            if identity:
                identity['auth_method'] = 'tenant_token'
                identity['client_ip'] = client_ip
                return identity

        # 5. 尝试全局 API Key 认证（原有）
        if global_api_key:
            identity = self._verify_global_api_key(global_api_key)
            if identity:
                identity['auth_method'] = 'global_api_key'
                identity['client_ip'] = client_ip
                return identity

        # 认证关闭时返回匿名权限
        if not self.enabled:
            return {
                'authenticated': False,
                'is_anonymous': True,
                'tenant_id': None,
                'user_id': None,
                'username': 'anonymous',
                'role': 'anonymous',
                'permissions': ['read', 'write', 'admin', 'tenant_admin'],
                'auth_method': 'none',
                'client_ip': client_ip,
            }

        return {
            'authenticated': False,
            'is_anonymous': True,
            'tenant_id': None,
            'user_id': None,
            'username': None,
            'role': None,
            'permissions': [],
            'auth_method': 'none',
            'client_ip': client_ip,
        }

    def _verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证 JWT 令牌

        Args:
            token: JWT 令牌

        Returns:
            身份信息
        """
        try:
            payload = jwt_manager.verify_token(token, token_type='access')
            if not payload:
                return None

            sub = payload.get('sub')
            tenant_id = payload.get('tenant_id')
            session_id = payload.get('session_id')
            role = payload.get('role', 'viewer')

            if not sub or not tenant_id:
                return None

            # 验证会话是否有效
            session_info = session_manager.validate_session(session_id) if session_id else None
            if session_id and not session_info:
                logger.warning(f"JWT 会话已失效: session_id={session_id}")
                return None

            user_id = sub
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)

            return {
                'authenticated': True,
                'is_anonymous': False,
                'tenant_id': tenant_id,
                'user_id': user_id,
                'username': payload.get('username', ''),
                'role': role,
                'permissions': self._role_to_permissions(role),
                'session_id': session_id,
                'jti': payload.get('jti'),
                'token_type': 'access',
                'is_service_account': False,
                'sso_provider_id': payload.get('sso_provider_id'),
            }

        except Exception as e:
            logger.warning(f"JWT 验证失败: {e}")
            return None

    def _verify_service_account(self, api_key: str, client_ip: str) -> Optional[Dict[str, Any]]:
        """
        验证服务账号 API Key

        Args:
            api_key: API Key
            client_ip: 客户端 IP

        Returns:
            身份信息
        """
        try:
            sa_info = service_account_service.validate_service_account_key(
                api_key_plain=api_key,
                client_ip=client_ip,
            )
            if not sa_info:
                return None

            return {
                'authenticated': True,
                'is_anonymous': False,
                'tenant_id': sa_info['tenant_id'],
                'user_id': None,
                'username': sa_info['account_name'],
                'role': sa_info['role'],
                'permissions': sa_info['permissions'],
                'service_account_id': sa_info['service_account_id'],
                'service_account_name': sa_info['account_name'],
                'key_id': sa_info.get('key_id'),
                'rate_limit': sa_info.get('rate_limit'),
                'allowed_scopes': sa_info.get('allowed_scopes', []),
                'is_service_account': True,
            }

        except Exception as e:
            logger.warning(f"服务账号验证失败: {e}")
            return None

    def _verify_tenant_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        验证租户 API Key

        Args:
            api_key: 租户 API Key

        Returns:
            身份信息
        """
        try:
            from app.services.tenant import TenantAPIKeyService, QuotaService

            svc = TenantAPIKeyService()
            key_info = svc.validate_api_key(api_key)
            if not key_info:
                return None

            QuotaService().increment_api_calls(key_info["tenant_id"])

            return {
                'authenticated': True,
                'is_anonymous': False,
                'tenant_id': key_info['tenant_id'],
                'user_id': key_info.get('user_id'),
                'username': key_info.get('name', 'api_key'),
                'role': 'api_key',
                'permissions': key_info.get('permissions', ['read']),
                'key_id': key_info.get('key_id'),
                'is_service_account': False,
            }

        except Exception as e:
            logger.warning(f"租户 API Key 验证失败: {e}")
            return None

    def _verify_tenant_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证租户 Token

        Args:
            token: 租户 Token

        Returns:
            身份信息
        """
        try:
            from app.api.auth import verify_tenant_token

            token_info = verify_tenant_token(token)
            if not token_info:
                return None

            role = token_info.get('role', 'viewer')

            return {
                'authenticated': True,
                'is_anonymous': False,
                'tenant_id': token_info['tenant_id'],
                'user_id': token_info['user_id'],
                'username': token_info['username'],
                'role': role,
                'permissions': self._role_to_permissions(role),
                'is_service_account': False,
            }

        except Exception as e:
            logger.warning(f"租户 Token 验证失败: {e}")
            return None

    def _verify_global_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        验证全局 API Key

        Args:
            api_key: 全局 API Key

        Returns:
            身份信息
        """
        try:
            from app.api.auth import api_key_manager

            key_info = api_key_manager.validate_key(api_key)
            if not key_info:
                return None

            return {
                'authenticated': True,
                'is_anonymous': False,
                'tenant_id': None,
                'user_id': None,
                'username': key_info.get('name', 'api_key'),
                'role': 'global_api_key',
                'permissions': key_info.get('permissions', ['read']),
                'key_id': key_info.get('key_id'),
                'is_service_account': False,
            }

        except Exception as e:
            logger.warning(f"全局 API Key 验证失败: {e}")
            return None

    @staticmethod
    def _role_to_permissions(role: str) -> List[str]:
        """角色到权限的映射"""
        mapping = {
            'tenant_admin': ['read', 'write', 'admin', 'tenant_admin'],
            'admin': ['read', 'write', 'admin'],
            'operator': ['read', 'write'],
            'viewer': ['read'],
            'api_key': ['read'],
        }
        return mapping.get(role, ['read'])


unified_auth = UnifiedAuth()


async def get_current_identity(
    request: Request,
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Security(JWT_BEARER),
    service_account_key: Optional[str] = Security(SERVICE_ACCOUNT_KEY_HEADER),
    tenant_api_key: Optional[str] = Security(
        APIKeyHeader(name="X-Tenant-API-Key", auto_error=False)
    ),
    tenant_token: Optional[str] = Security(
        APIKeyHeader(name="X-Tenant-Token", auto_error=False)
    ),
    global_api_key: Optional[str] = Security(
        APIKeyHeader(name="X-API-Key", auto_error=False)
    ),
) -> Dict[str, Any]:
    """
    获取当前请求的身份上下文（统一认证入口）

    支持多种认证方式，自动检测并返回统一格式的身份信息。

    Args:
        request: 请求对象
        bearer_credentials: Bearer JWT 凭证
        service_account_key: 服务账号 API Key
        tenant_api_key: 租户 API Key
        tenant_token: 租户 Token
        global_api_key: 全局 API Key

    Returns:
        身份上下文字典，包含：
        - authenticated: 是否已认证
        - is_anonymous: 是否匿名
        - tenant_id: 租户ID
        - user_id: 用户ID
        - username: 用户名
        - role: 角色
        - permissions: 权限列表
        - auth_method: 认证方式
        - is_service_account: 是否服务账号
    """
    return unified_auth.resolve_identity(
        request=request,
        bearer_credentials=bearer_credentials,
        service_account_key=service_account_key,
        tenant_api_key=tenant_api_key,
        tenant_token=tenant_token,
        global_api_key=global_api_key,
    )


async def require_authenticated(
    identity: Dict[str, Any] = Depends(get_current_identity),
) -> Dict[str, Any]:
    """
    要求已认证的依赖项

    如果未认证，抛出 401 错误。

    Args:
        identity: 身份上下文

    Returns:
        身份上下文

    Raises:
        HTTPException: 401 未认证
    """
    if not identity.get('authenticated'):
        raise HTTPException(
            status_code=401,
            detail={
                'error': 'Unauthorized',
                'message': '需要认证',
                'auth_method': identity.get('auth_method'),
            },
        )
    return identity


async def require_tenant_context(
    identity: Dict[str, Any] = Depends(require_authenticated),
) -> Dict[str, Any]:
    """
    要求租户上下文的依赖项

    已认证且有租户ID。

    Args:
        identity: 身份上下文

    Returns:
        身份上下文

    Raises:
        HTTPException: 401 或 403
    """
    if not identity.get('tenant_id'):
        raise HTTPException(
            status_code=403,
            detail={
                'error': 'Forbidden',
                'message': '需要租户上下文',
            },
        )
    return identity


def require_role(*roles: str):
    """
    要求特定角色的依赖项工厂函数

    Args:
        *roles: 允许的角色列表

    Returns:
        依赖项函数
    """
    async def _check_role(
        identity: Dict[str, Any] = Depends(require_authenticated),
    ) -> Dict[str, Any]:
        user_role = identity.get('role')
        if user_role not in roles and user_role != 'tenant_admin':
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'Forbidden',
                    'message': f'需要角色: {", ".join(roles)}',
                    'current_role': user_role,
                },
            )
        return identity
    return _check_role


def require_permission(permission: str):
    """
    要求特定权限的依赖项工厂函数

    Args:
        permission: 需要的权限

    Returns:
        依赖项函数
    """
    permission_hierarchy = {'read': 0, 'write': 1, 'admin': 2, 'tenant_admin': 3}

    async def _check_permission(
        identity: Dict[str, Any] = Depends(require_authenticated),
    ) -> Dict[str, Any]:
        permissions = identity.get('permissions', [])
        required_level = permission_hierarchy.get(permission, 99)
        has_access = any(
            permission_hierarchy.get(p, -1) >= required_level
            for p in permissions
        ) or permission in permissions

        if not has_access:
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'Forbidden',
                    'message': f'缺少权限: {permission}',
                    'current_permissions': permissions,
                    'required': permission,
                },
            )
        return identity
    return _check_permission
