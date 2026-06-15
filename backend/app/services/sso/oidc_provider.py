import json
import secrets
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from loguru import logger

from app.utils.database import get_db, SSOProvider
from app.utils.config import config


class OIDCProvider:
    """
    OIDC (OpenID Connect) 协议支持

    功能:
    1. 生成授权 URL (Authorization Request)
    2. 处理回调 (Token Exchange)
    3. 验证 ID Token
    4. 获取用户信息 (UserInfo)
    5. 发现端点 (Discovery)
    """

    def __init__(self):
        self._discovery_cache: Dict[int, Dict[str, Any]] = {}
        self._jwks_cache: Dict[int, Dict[str, Any]] = {}

    def get_authorization_url(
        self,
        provider_id: int,
        redirect_uri: str,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        生成 OIDC 授权 URL

        Args:
            provider_id: SSO 提供者ID
            redirect_uri: 回调 URI
            state: 状态参数（防 CSRF）
            nonce: 随机数（防重放）
            extra_params: 额外参数

        Returns:
            包含授权 URL 和 state/nonce 的字典
        """
        try:
            provider = self._get_provider(provider_id)
            if not provider:
                raise ValueError(f"SSO 提供者不存在: {provider_id}")

            if state is None:
                state = secrets.token_urlsafe(32)

            if nonce is None:
                nonce = secrets.token_urlsafe(32)

            scopes = self._parse_json(provider.scopes, ['openid', 'email', 'profile'])
            scope_str = ' '.join(scopes)

            params = {
                'response_type': 'code',
                'client_id': provider.client_id,
                'redirect_uri': redirect_uri,
                'scope': scope_str,
                'state': state,
                'nonce': nonce,
            }

            if extra_params:
                params.update(extra_params)

            # 使用发现端点获取授权 URL，或使用配置的 URL
            auth_endpoint = provider.authorization_endpoint
            if not auth_endpoint:
                discovery = self._get_discovery(provider)
                if discovery:
                    auth_endpoint = discovery.get('authorization_endpoint')

            if not auth_endpoint:
                raise ValueError("授权端点未配置且无法从发现端点获取")

            auth_url = f"{auth_endpoint}?{urlencode(params)}"

            return {
                'authorization_url': auth_url,
                'state': state,
                'nonce': nonce,
                'provider_id': provider_id,
            }

        except Exception as e:
            logger.error(f"生成 OIDC 授权 URL 失败: {e}")
            raise

    def handle_callback(
        self,
        provider_id: int,
        code: str,
        redirect_uri: str,
        state: Optional[str] = None,
        expected_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        处理 OIDC 回调

        Args:
            provider_id: SSO 提供者ID
            code: 授权码
            redirect_uri: 回调 URI
            state: 返回的 state
            expected_state: 期望的 state（验证用）

        Returns:
            包含令牌和用户信息的字典
        """
        import httpx

        try:
            provider = self._get_provider(provider_id)
            if not provider:
                raise ValueError(f"SSO 提供者不存在: {provider_id}")

            # 验证 state
            if expected_state and state != expected_state:
                raise ValueError("state 验证失败")

            # 获取令牌端点
            token_endpoint = provider.token_endpoint
            if not token_endpoint:
                discovery = self._get_discovery(provider)
                if discovery:
                    token_endpoint = discovery.get('token_endpoint')

            if not token_endpoint:
                raise ValueError("令牌端点未配置且无法从发现端点获取")

            # 换取令牌
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
                'client_id': provider.client_id,
                'client_secret': provider.client_secret,
            }

            response = httpx.post(
                token_endpoint,
                data=token_data,
                headers={'Accept': 'application/json'},
                timeout=30,
            )
            response.raise_for_status()
            token_response = response.json()

            # 提取令牌
            id_token = token_response.get('id_token')
            access_token = token_response.get('access_token')
            refresh_token = token_response.get('refresh_token')
            expires_in = token_response.get('expires_in')

            # 验证 ID Token
            id_token_payload = None
            if id_token:
                id_token_payload = self._verify_id_token(provider, id_token)

            # 获取用户信息
            user_info = None
            if access_token:
                user_info = self._get_user_info(provider, access_token)

            # 提取用户信息
            user_info = user_info or id_token_payload or {}

            # 提取用户组
            groups = self._extract_groups(user_info)

            # 提取用户唯一标识
            idp_user_id = user_info.get('sub') or user_info.get('oid') or user_info.get('email')
            if not idp_user_id:
                raise ValueError("无法获取用户唯一标识")

            return {
                'idp_user_id': str(idp_user_id),
                'idp_username': user_info.get('preferred_username') or user_info.get('email') or str(idp_user_id),
                'idp_email': user_info.get('email', ''),
                'idp_display_name': user_info.get('name') or user_info.get('display_name', ''),
                'idp_attributes': user_info,
                'idp_groups': groups,
                'id_token': id_token,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'id_token_payload': id_token_payload,
                'provider_id': provider_id,
                'provider_type': 'oidc',
            }

        except Exception as e:
            logger.error(f"处理 OIDC 回调失败: {e}")
            raise

    def _verify_id_token(self, provider: SSOProvider, id_token: str) -> Optional[Dict[str, Any]]:
        """
        验证 ID Token

        Args:
            provider: SSO 提供者
            id_token: ID Token

        Returns:
            解码后的载荷
        """
        try:
            from jose import jwt, JWTError

            # 获取 JWKS
            jwks = self._get_jwks(provider)
            if not jwks:
                logger.warning("无法获取 JWKS，跳过签名验证")
                # 不验证签名，仅解码
                try:
                    return jwt.get_unverified_claims(id_token)
                except JWTError:
                    return None

            # 获取无签名的头部以找到 kid
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get('kid')

            # 找到对应的公钥
            public_key = None
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    public_key = self._jwk_to_pem(key)
                    break

            if not public_key:
                logger.warning(f"未找到对应的公钥 kid={kid}，跳过签名验证")
                try:
                    return jwt.get_unverified_claims(id_token)
                except JWTError:
                    return None

            # 验证签名和标准声明
            algorithm = unverified_header.get('alg', 'RS256')
            try:
                payload = jwt.decode(
                    id_token,
                    public_key,
                    algorithms=[algorithm],
                    audience=provider.client_id,
                    options={
                        'verify_aud': True,
                        'verify_exp': True,
                        'verify_iat': True,
                    }
                )
                return payload
            except JWTError as e:
                logger.warning(f"ID Token 验证失败: {e}")
                return None

        except Exception as e:
            logger.warning(f"验证 ID Token 异常: {e}")
            return None

    def _get_user_info(self, provider: SSOProvider, access_token: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息

        Args:
            provider: SSO 提供者
            access_token: 访问令牌

        Returns:
            用户信息字典
        """
        import httpx

        try:
            userinfo_endpoint = provider.userinfo_endpoint
            if not userinfo_endpoint:
                discovery = self._get_discovery(provider)
                if discovery:
                    userinfo_endpoint = discovery.get('userinfo_endpoint')

            if not userinfo_endpoint:
                return None

            response = httpx.get(
                userinfo_endpoint,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.warning(f"获取用户信息失败: {e}")
            return None

    def _get_discovery(self, provider: SSOProvider) -> Optional[Dict[str, Any]]:
        """
        获取 OIDC Discovery 文档

        Args:
            provider: SSO 提供者

        Returns:
            Discovery 文档内容
        """
        import httpx

        try:
            if not provider.issuer_url:
                return None

            # 检查缓存
            if provider.id in self._discovery_cache:
                return self._discovery_cache[provider.id]

            discovery_url = f"{provider.issuer_url.rstrip('/')}/.well-known/openid-configuration"

            response = httpx.get(discovery_url, timeout=30)
            response.raise_for_status()
            discovery = response.json()

            self._discovery_cache[provider.id] = discovery
            return discovery

        except Exception as e:
            logger.warning(f"获取 Discovery 文档失败: {e}")
            return None

    def _get_jwks(self, provider: SSOProvider) -> Optional[Dict[str, Any]]:
        """
        获取 JWKS (JSON Web Key Set)

        Args:
            provider: SSO 提供者

        Returns:
            JWKS 内容
        """
        import httpx

        try:
            # 检查缓存
            if provider.id in self._jwks_cache:
                return self._jwks_cache[provider.id]

            jwks_uri = provider.jwks_uri
            if not jwks_uri:
                discovery = self._get_discovery(provider)
                if discovery:
                    jwks_uri = discovery.get('jwks_uri')

            if not jwks_uri:
                return None

            response = httpx.get(jwks_uri, timeout=30)
            response.raise_for_status()
            jwks = response.json()

            self._jwks_cache[provider.id] = jwks
            return jwks

        except Exception as e:
            logger.warning(f"获取 JWKS 失败: {e}")
            return None

    @staticmethod
    def _jwk_to_pem(jwk: Dict[str, Any]) -> Optional[str]:
        """
        将 JWK 转换为 PEM 格式公钥

        Args:
            jwk: JWK 字典

        Returns:
            PEM 格式公钥
        """
        try:
            from jose.backends import RSAKey

            key = RSAKey(algorithm=jwk.get('alg', 'RS256'), key=jwk)
            return key.public_key().to_pem().decode('utf-8')

        except Exception as e:
            logger.warning(f"JWK 转换失败: {e}")
            return None

    @staticmethod
    def _extract_groups(user_info: Dict[str, Any]) -> List[str]:
        """
        从用户信息中提取用户组

        支持多种字段:
        - groups
        - roles
        - memberOf
        - group
        - https://.../groups (Azure AD 风格)

        Args:
            user_info: 用户信息

        Returns:
            用户组列表
        """
        group_fields = [
            'groups',
            'roles',
            'memberOf',
            'group',
            'groups_list',
            'user_groups',
        ]

        # 检查标准字段
        for field in group_fields:
            if field in user_info:
                groups = user_info[field]
                if isinstance(groups, list):
                    return [str(g) for g in groups]
                if isinstance(groups, str):
                    return [g.strip() for g in groups.split(',') if g.strip()]

        # 检查命名空间字段（Azure AD / Okta 风格）
        for key in user_info:
            if key.endswith('/groups') or key.endswith('/roles'):
                groups = user_info[key]
                if isinstance(groups, list):
                    return [str(g) for g in groups]

        return []

    def _get_provider(self, provider_id: int) -> Optional[SSOProvider]:
        """获取 SSO 提供者"""
        try:
            with get_db() as db:
                if db is None:
                    return None
                return db.query(SSOProvider).filter(
                    SSOProvider.id == provider_id,
                    SSOProvider.status == 'active',
                ).first()
        except Exception as e:
            logger.error(f"获取 SSO 提供者失败: {e}")
            return None

    @staticmethod
    def _parse_json(value: Optional[str], default: Any) -> Any:
        """解析 JSON 字符串"""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default


oidc_provider = OIDCProvider()
