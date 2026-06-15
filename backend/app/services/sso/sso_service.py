import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.utils.database import (
    get_db,
    SSOProvider,
    UserSSOLink,
    TenantUser,
    Tenant,
    TenantQuota,
)
from app.utils.config import config


class SSOService:
    """
    SSO 统一身份认证服务

    功能:
    1. SSO 提供者配置管理
    2. JIT (Just-In-Time) 自动建号
    3. 角色映射（IdP groups -> 本地角色）
    4. 用户属性映射
    5. SSO 关联管理
    """

    # ============================================================
    # SSO 提供者管理
    # ============================================================

    def create_provider(
        self,
        tenant_id: int,
        provider_name: str,
        provider_type: str,
        **kwargs,
    ) -> Optional[SSOProvider]:
        """
        创建 SSO 提供者

        Args:
            tenant_id: 租户ID
            provider_name: 提供者名称
            provider_type: 协议类型 oidc/saml
            **kwargs: 其他配置参数

        Returns:
            SSO 提供者实例
        """
        if provider_type not in ('oidc', 'saml'):
            raise ValueError(f"无效的提供者类型: {provider_type}")

        try:
            with get_db() as db:
                if db is None:
                    return None

                provider = SSOProvider(
                    tenant_id=tenant_id,
                    provider_name=provider_name,
                    provider_type=provider_type,
                    status=kwargs.get('status', 'inactive'),
                    is_default=kwargs.get('is_default', False),
                    sort_order=kwargs.get('sort_order', 0),
                    issuer_url=kwargs.get('issuer_url'),
                    client_id=kwargs.get('client_id'),
                    client_secret=kwargs.get('client_secret'),
                    authorization_endpoint=kwargs.get('authorization_endpoint'),
                    token_endpoint=kwargs.get('token_endpoint'),
                    userinfo_endpoint=kwargs.get('userinfo_endpoint'),
                    jwks_uri=kwargs.get('jwks_uri'),
                    scopes=json.dumps(kwargs.get('scopes', ['openid', 'email', 'profile']), ensure_ascii=False),
                    saml_entity_id=kwargs.get('saml_entity_id'),
                    saml_sso_url=kwargs.get('saml_sso_url'),
                    saml_slo_url=kwargs.get('saml_slo_url'),
                    saml_idp_cert=kwargs.get('saml_idp_cert'),
                    saml_name_id_format=kwargs.get('saml_name_id_format'),
                    attribute_mapping=json.dumps(kwargs.get('attribute_mapping', {}), ensure_ascii=False) if kwargs.get('attribute_mapping') else None,
                    role_mapping=json.dumps(kwargs.get('role_mapping', {}), ensure_ascii=False) if kwargs.get('role_mapping') else None,
                    jit_enabled=kwargs.get('jit_enabled', True),
                    jit_default_role=kwargs.get('jit_default_role', 'viewer'),
                    jit_auto_activate=kwargs.get('jit_auto_activate', True),
                    session_max_age=kwargs.get('session_max_age', 86400),
                    session_idle_timeout=kwargs.get('session_idle_timeout', 3600),
                    extra_config=json.dumps(kwargs.get('extra_config', {}), ensure_ascii=False) if kwargs.get('extra_config') else None,
                )

                db.add(provider)
                db.flush()
                return provider

        except Exception as e:
            logger.error(f"创建 SSO 提供者失败: {e}")
            return None

    def get_provider(self, provider_id: int) -> Optional[SSOProvider]:
        """获取 SSO 提供者"""
        try:
            with get_db() as db:
                if db is None:
                    return None
                return db.query(SSOProvider).filter(SSOProvider.id == provider_id).first()
        except Exception as e:
            logger.error(f"获取 SSO 提供者失败: {e}")
            return None

    def list_providers(
        self,
        tenant_id: int,
        provider_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[SSOProvider]:
        """列出租户的 SSO 提供者"""
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(SSOProvider).filter(SSOProvider.tenant_id == tenant_id)

                if provider_type:
                    query = query.filter(SSOProvider.provider_type == provider_type)

                if status:
                    query = query.filter(SSOProvider.status == status)

                return query.order_by(SSOProvider.sort_order, SSOProvider.id).all()

        except Exception as e:
            logger.error(f"列出 SSO 提供者失败: {e}")
            return []

    def get_default_provider(self, tenant_id: int) -> Optional[SSOProvider]:
        """获取默认 SSO 提供者"""
        try:
            with get_db() as db:
                if db is None:
                    return None

                provider = db.query(SSOProvider).filter(
                    SSOProvider.tenant_id == tenant_id,
                    SSOProvider.is_default == True,
                    SSOProvider.status == 'active',
                ).first()

                if not provider:
                    provider = db.query(SSOProvider).filter(
                        SSOProvider.tenant_id == tenant_id,
                        SSOProvider.status == 'active',
                    ).order_by(SSOProvider.sort_order, SSOProvider.id).first()

                return provider

        except Exception as e:
            logger.error(f"获取默认 SSO 提供者失败: {e}")
            return None

    def update_provider(self, provider_id: int, **kwargs) -> Optional[SSOProvider]:
        """更新 SSO 提供者配置"""
        try:
            with get_db() as db:
                if db is None:
                    return None

                provider = db.query(SSOProvider).filter(
                    SSOProvider.id == provider_id
                ).first()

                if not provider:
                    return None

                for key, value in kwargs.items():
                    if value is not None and hasattr(provider, key):
                        if key in ('scopes', 'attribute_mapping', 'role_mapping', 'extra_config'):
                            if isinstance(value, (dict, list)):
                                setattr(provider, key, json.dumps(value, ensure_ascii=False))
                            else:
                                setattr(provider, key, value)
                        else:
                            setattr(provider, key, value)

                return provider

        except Exception as e:
            logger.error(f"更新 SSO 提供者失败: {e}")
            return None

    def delete_provider(self, provider_id: int) -> bool:
        """删除 SSO 提供者"""
        try:
            with get_db() as db:
                if db is None:
                    return False

                provider = db.query(SSOProvider).filter(
                    SSOProvider.id == provider_id
                ).first()

                if not provider:
                    return False

                provider.status = 'inactive'
                return True

        except Exception as e:
            logger.error(f"删除 SSO 提供者失败: {e}")
            return False

    # ============================================================
    # JIT 建号与用户映射
    # ============================================================

    def jit_provision_user(
        self,
        tenant_id: int,
        sso_provider_id: int,
        idp_user_id: str,
        idp_attributes: Dict[str, Any],
        idp_groups: Optional[List[str]] = None,
    ) -> Tuple[Optional[TenantUser], bool]:
        """
        JIT (Just-In-Time) 自动建号

        如果用户已存在，则更新信息；如果不存在，则创建新用户。

        Args:
            tenant_id: 租户ID
            sso_provider_id: SSO 提供者ID
            idp_user_id: IdP 用户唯一标识
            idp_attributes: IdP 用户属性
            idp_groups: IdP 用户组列表

        Returns:
            (用户对象, 是否新建)
        """
        try:
            with get_db() as db:
                if db is None:
                    return None, False

                provider = db.query(SSOProvider).filter(
                    SSOProvider.id == sso_provider_id
                ).first()

                if not provider:
                    logger.warning(f"SSO 提供者不存在: {sso_provider_id}")
                    return None, False

                if not provider.jit_enabled:
                    logger.warning(f"SSO 提供者未启用 JIT: {sso_provider_id}")
                    return None, False

                # 检查用户是否已关联
                sso_link = db.query(UserSSOLink).filter(
                    UserSSOLink.sso_provider_id == sso_provider_id,
                    UserSSOLink.idp_user_id == idp_user_id,
                ).first()

                if sso_link:
                    # 用户已存在，更新信息
                    user = db.query(TenantUser).filter(
                        TenantUser.id == sso_link.user_id,
                        TenantUser.tenant_id == tenant_id,
                    ).first()

                    if user:
                        self._update_user_from_idp(user, provider, idp_attributes, idp_groups)
                        self._update_sso_link(sso_link, idp_attributes, idp_groups)
                        return user, False

                # JIT 创建新用户
                attribute_mapping = self._parse_json(provider.attribute_mapping, {})
                role_mapping = self._parse_json(provider.role_mapping, {})

                username = self._map_attribute(idp_attributes, attribute_mapping.get('username', 'preferred_username'), idp_user_id)
                email = self._map_attribute(idp_attributes, attribute_mapping.get('email', 'email'), '')
                display_name = self._map_attribute(idp_attributes, attribute_mapping.get('display_name', 'name'), username)

                # 角色映射
                role = self._map_role(idp_groups, role_mapping, provider.jit_default_role)

                # 检查用户名是否已存在
                existing_user = db.query(TenantUser).filter(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.username == username,
                ).first()

                if existing_user:
                    # 用户名已存在，使用 IdP 用户 ID 作为用户名
                    username = f"{idp_user_id}@{provider.provider_name}"
                    existing_user2 = db.query(TenantUser).filter(
                        TenantUser.tenant_id == tenant_id,
                        TenantUser.username == username,
                    ).first()
                    if existing_user2:
                        username = f"sso_{sso_provider_id}_{idp_user_id}"

                # 创建用户
                user = TenantUser(
                    tenant_id=tenant_id,
                    username=username,
                    password_hash=None,
                    display_name=display_name,
                    email=email,
                    role=role,
                    status='active' if provider.jit_auto_activate else 'disabled',
                )
                db.add(user)
                db.flush()

                # 检查配额
                quota = db.query(TenantQuota).filter(
                    TenantQuota.tenant_id == tenant_id
                ).first()
                if quota:
                    quota.current_user_count = db.query(TenantUser).filter(
                        TenantUser.tenant_id == tenant_id,
                        TenantUser.status == 'active',
                    ).count()

                # 创建 SSO 关联
                sso_link = UserSSOLink(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    sso_provider_id=sso_provider_id,
                    idp_user_id=idp_user_id,
                    idp_username=username,
                    idp_email=email,
                    idp_groups=json.dumps(idp_groups, ensure_ascii=False) if idp_groups else None,
                    idp_attributes=json.dumps(idp_attributes, ensure_ascii=False) if idp_attributes else None,
                    is_primary=True,
                    status='active',
                )
                db.add(sso_link)
                db.flush()

                logger.info(f"JIT 创建用户成功: tenant={tenant_id}, user={username}, provider={sso_provider_id}")
                return user, True

        except Exception as e:
            logger.error(f"JIT 建号失败: {e}")
            return None, False

    def find_user_by_sso_id(
        self,
        sso_provider_id: int,
        idp_user_id: str,
    ) -> Optional[TenantUser]:
        """
        根据 SSO 标识查找用户

        Args:
            sso_provider_id: SSO 提供者ID
            idp_user_id: IdP 用户唯一标识

        Returns:
            用户对象
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                sso_link = db.query(UserSSOLink).filter(
                    UserSSOLink.sso_provider_id == sso_provider_id,
                    UserSSOLink.idp_user_id == idp_user_id,
                    UserSSOLink.status == 'active',
                ).first()

                if not sso_link:
                    return None

                user = db.query(TenantUser).filter(
                    TenantUser.id == sso_link.user_id,
                    TenantUser.status == 'active',
                ).first()

                return user

        except Exception as e:
            logger.error(f"查找 SSO 用户失败: {e}")
            return None

    def link_sso_to_user(
        self,
        tenant_id: int,
        user_id: int,
        sso_provider_id: int,
        idp_user_id: str,
        idp_username: Optional[str] = None,
        idp_email: Optional[str] = None,
        is_primary: bool = False,
    ) -> Optional[UserSSOLink]:
        """
        将 SSO 身份关联到现有用户

        Args:
            tenant_id: 租户ID
            user_id: 本地用户ID
            sso_provider_id: SSO 提供者ID
            idp_user_id: IdP 用户唯一标识
            idp_username: IdP 用户名
            idp_email: IdP 邮箱
            is_primary: 是否为主要登录方式

        Returns:
            SSO 关联对象
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                # 检查是否已关联
                existing = db.query(UserSSOLink).filter(
                    UserSSOLink.sso_provider_id == sso_provider_id,
                    UserSSOLink.idp_user_id == idp_user_id,
                ).first()

                if existing:
                    raise ValueError(f"该 IdP 身份已关联到其他用户")

                # 如果设为主要，取消其他的主要标记
                if is_primary:
                    db.query(UserSSOLink).filter(
                        UserSSOLink.user_id == user_id,
                        UserSSOLink.is_primary == True,
                    ).update({UserSSOLink.is_primary: False})

                link = UserSSOLink(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    sso_provider_id=sso_provider_id,
                    idp_user_id=idp_user_id,
                    idp_username=idp_username,
                    idp_email=idp_email,
                    is_primary=is_primary,
                    status='active',
                )
                db.add(link)
                db.flush()
                return link

        except Exception as e:
            logger.error(f"关联 SSO 身份失败: {e}")
            raise

    def unlink_sso_from_user(
        self,
        user_id: int,
        sso_provider_id: int,
    ) -> bool:
        """
        解除 SSO 身份关联

        Args:
            user_id: 用户ID
            sso_provider_id: SSO 提供者ID

        Returns:
            是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                link = db.query(UserSSOLink).filter(
                    UserSSOLink.user_id == user_id,
                    UserSSOLink.sso_provider_id == sso_provider_id,
                ).first()

                if not link:
                    return False

                link.status = 'disconnected'
                return True

        except Exception as e:
            logger.error(f"解除 SSO 关联失败: {e}")
            return False

    def list_user_sso_links(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        列出用户的所有 SSO 关联

        Args:
            user_id: 用户ID

        Returns:
            SSO 关联列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                links = db.query(UserSSOLink).filter(
                    UserSSOLink.user_id == user_id
                ).all()

                result = []
                for link in links:
                    provider = db.query(SSOProvider).filter(
                        SSOProvider.id == link.sso_provider_id
                    ).first()

                    result.append({
                        'id': link.id,
                        'sso_provider_id': link.sso_provider_id,
                        'provider_name': provider.provider_name if provider else None,
                        'provider_type': provider.provider_type if provider else None,
                        'idp_user_id': link.idp_user_id,
                        'idp_username': link.idp_username,
                        'idp_email': link.idp_email,
                        'is_primary': link.is_primary,
                        'status': link.status,
                        'linked_at': link.linked_at,
                        'last_login_at': link.last_login_at,
                        'login_count': link.login_count,
                    })

                return result

        except Exception as e:
            logger.error(f"列出用户 SSO 关联失败: {e}")
            return []

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _parse_json(value: Optional[str], default: Any) -> Any:
        """解析 JSON 字符串"""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _map_attribute(
        attributes: Dict[str, Any],
        key: str,
        default: str,
    ) -> str:
        """
        根据映射键从 IdP 属性中获取值

        支持嵌套属性，如 'name.givenName'
        """
        if not key or not attributes:
            return default

        keys = key.split('.')
        value = attributes

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return str(value) if value is not None else default

    @staticmethod
    def _map_role(
        groups: Optional[List[str]],
        role_mapping: Dict[str, str],
        default_role: str,
    ) -> str:
        """
        根据 IdP 用户组映射到本地角色

        优先级:
        1. tenant_admin - 最高权限
        2. admin
        3. operator
        4. viewer - 默认

        Args:
            groups: IdP 用户组列表
            role_mapping: 角色映射规则 {idp_group: local_role}
            default_role: 默认角色

        Returns:
            映射后的角色
        """
        if not groups or not role_mapping:
            return default_role

        role_hierarchy = {
            'tenant_admin': 0,
            'admin': 1,
            'operator': 2,
            'viewer': 3,
        }

        highest_role = default_role
        highest_level = role_hierarchy.get(default_role, 99)

        for group in groups:
            local_role = role_mapping.get(group)
            if local_role and local_role in role_hierarchy:
                level = role_hierarchy[local_role]
                if level < highest_level:
                    highest_role = local_role
                    highest_level = level

        return highest_role

    @staticmethod
    def _update_user_from_idp(
        user: TenantUser,
        provider: SSOProvider,
        idp_attributes: Dict[str, Any],
        idp_groups: Optional[List[str]],
    ) -> None:
        """根据 IdP 属性更新用户信息"""
        import json

        attribute_mapping = SSOService._parse_json(provider.attribute_mapping, {})
        role_mapping = SSOService._parse_json(provider.role_mapping, {})

        if attribute_mapping.get('email'):
            email = SSOService._map_attribute(idp_attributes, attribute_mapping['email'], user.email or '')
            if email:
                user.email = email

        if attribute_mapping.get('display_name'):
            display_name = SSOService._map_attribute(idp_attributes, attribute_mapping['display_name'], user.display_name or '')
            if display_name:
                user.display_name = display_name

        if idp_groups and role_mapping:
            new_role = SSOService._map_role(idp_groups, role_mapping, user.role)
            if new_role and new_role != user.role:
                user.role = new_role

        user.last_login_time = datetime.now()

    @staticmethod
    def _update_sso_link(
        link: UserSSOLink,
        idp_attributes: Dict[str, Any],
        idp_groups: Optional[List[str]],
    ) -> None:
        """更新 SSO 关联信息"""
        import json

        link.last_login_at = datetime.now()
        link.login_count = (link.login_count or 0) + 1

        if idp_groups:
            link.idp_groups = json.dumps(idp_groups, ensure_ascii=False)

        if idp_attributes:
            link.idp_attributes = json.dumps(idp_attributes, ensure_ascii=False)


sso_service = SSOService()
