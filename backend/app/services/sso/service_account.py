import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from app.utils.database import get_db, ServiceAccount, ServiceAccountKey, TenantQuota
from app.utils.config import config


class ServiceAccountService:
    """
    服务账号管理服务

    功能:
    1. 服务账号 CRUD
    2. API Key 管理（创建、吊销、轮换）
    3. 服务账号认证验证
    4. 权限和配额管理
    """

    VALID_ROLES = {'tenant_admin', 'admin', 'operator', 'viewer'}

    # ============================================================
    # 服务账号管理
    # ============================================================

    def create_service_account(
        self,
        tenant_id: int,
        account_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        role: str = 'viewer',
        rate_limit: int = 1000,
        allowed_ips: Optional[List[str]] = None,
        allowed_scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
        owner_id: Optional[int] = None,
        owner_name: Optional[str] = None,
        owner_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建服务账号

        Args:
            tenant_id: 租户ID
            account_name: 账号名称
            display_name: 显示名称
            description: 描述
            role: 角色
            rate_limit: 速率限制
            allowed_ips: IP 白名单
            allowed_scopes: 允许的 scope
            expires_at: 过期时间
            owner_id: 负责人用户ID
            owner_name: 负责人姓名
            owner_email: 负责人邮箱

        Returns:
            服务账号信息（包含第一个 API Key）
        """
        if role not in self.VALID_ROLES:
            raise ValueError(f"无效角色: {role}")

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                # 检查账号名是否已存在
                existing = db.query(ServiceAccount).filter(
                    ServiceAccount.tenant_id == tenant_id,
                    ServiceAccount.account_name == account_name,
                ).first()

                if existing:
                    raise ValueError(f"服务账号名称已存在: {account_name}")

                # 创建服务账号
                sa = ServiceAccount(
                    tenant_id=tenant_id,
                    account_name=account_name,
                    display_name=display_name or account_name,
                    description=description,
                    status='active',
                    role=role,
                    rate_limit=rate_limit,
                    allowed_ips=json.dumps(allowed_ips, ensure_ascii=False) if allowed_ips else None,
                    allowed_scopes=json.dumps(allowed_scopes, ensure_ascii=False) if allowed_scopes else None,
                    expires_at=expires_at,
                    owner_id=owner_id,
                    owner_name=owner_name,
                    owner_email=owner_email,
                )
                db.add(sa)
                db.flush()

                # 创建第一个 API Key
                key_result = self._create_api_key_internal(
                    db=db,
                    service_account_id=sa.id,
                    tenant_id=tenant_id,
                    key_name="default",
                )

                sa.current_api_key_id = key_result['key_id']
                db.flush()

                return {
                    'id': sa.id,
                    'tenant_id': sa.tenant_id,
                    'account_name': sa.account_name,
                    'display_name': sa.display_name,
                    'description': sa.description,
                    'status': sa.status,
                    'role': sa.role,
                    'rate_limit': sa.rate_limit,
                    'allowed_ips': allowed_ips,
                    'allowed_scopes': allowed_scopes,
                    'expires_at': sa.expires_at,
                    'owner_id': sa.owner_id,
                    'owner_name': sa.owner_name,
                    'owner_email': sa.owner_email,
                    'api_key': key_result,
                    'create_time': sa.create_time,
                }

        except Exception as e:
            logger.error(f"创建服务账号失败: {e}")
            raise

    def get_service_account(
        self,
        tenant_id: int,
        service_account_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取服务账号信息

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID

        Returns:
            服务账号信息
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                sa = db.query(ServiceAccount).filter(
                    ServiceAccount.id == service_account_id,
                    ServiceAccount.tenant_id == tenant_id,
                ).first()

                if not sa:
                    return None

                return self._sa_to_dict(sa)

        except Exception as e:
            logger.error(f"获取服务账号失败: {e}")
            return None

    def list_service_accounts(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出服务账号

        Args:
            tenant_id: 租户ID
            status: 状态过滤
            role: 角色过滤
            limit: 数量限制
            offset: 偏移量

        Returns:
            服务账号列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(ServiceAccount).filter(
                    ServiceAccount.tenant_id == tenant_id
                )

                if status:
                    query = query.filter(ServiceAccount.status == status)

                if role:
                    query = query.filter(ServiceAccount.role == role)

                accounts = query.order_by(
                    ServiceAccount.create_time.desc()
                ).offset(offset).limit(limit).all()

                return [self._sa_to_dict(sa) for sa in accounts]

        except Exception as e:
            logger.error(f"列出服务账号失败: {e}")
            return []

    def count_service_accounts(
        self,
        tenant_id: int,
        status: Optional[str] = None,
    ) -> int:
        """
        统计服务账号数量

        Args:
            tenant_id: 租户ID
            status: 状态过滤

        Returns:
            服务账号数量
        """
        try:
            with get_db() as db:
                if db is None:
                    return 0

                query = db.query(ServiceAccount).filter(
                    ServiceAccount.tenant_id == tenant_id
                )

                if status:
                    query = query.filter(ServiceAccount.status == status)

                return query.count()

        except Exception as e:
            logger.error(f"统计服务账号失败: {e}")
            return 0

    def update_service_account(
        self,
        tenant_id: int,
        service_account_id: int,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        更新服务账号

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID
            **kwargs: 要更新的字段

        Returns:
            更新后的服务账号信息
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                sa = db.query(ServiceAccount).filter(
                    ServiceAccount.id == service_account_id,
                    ServiceAccount.tenant_id == tenant_id,
                ).first()

                if not sa:
                    return None

                for key, value in kwargs.items():
                    if value is not None and hasattr(sa, key):
                        if key in ('allowed_ips', 'allowed_scopes'):
                            if isinstance(value, (list, dict)):
                                setattr(sa, key, json.dumps(value, ensure_ascii=False))
                        else:
                            setattr(sa, key, value)

                return self._sa_to_dict(sa)

        except Exception as e:
            logger.error(f"更新服务账号失败: {e}")
            return None

    def delete_service_account(
        self,
        tenant_id: int,
        service_account_id: int,
    ) -> bool:
        """
        删除（禁用）服务账号

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID

        Returns:
            是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                sa = db.query(ServiceAccount).filter(
                    ServiceAccount.id == service_account_id,
                    ServiceAccount.tenant_id == tenant_id,
                ).first()

                if not sa:
                    return False

                sa.status = 'disabled'

                # 吊销所有 API Key
                keys = db.query(ServiceAccountKey).filter(
                    ServiceAccountKey.service_account_id == service_account_id,
                    ServiceAccountKey.status == 'active',
                ).all()

                for key in keys:
                    key.status = 'revoked'

                return True

        except Exception as e:
            logger.error(f"删除服务账号失败: {e}")
            return False

    # ============================================================
    # API Key 管理
    # ============================================================

    def create_api_key(
        self,
        tenant_id: int,
        service_account_id: int,
        key_name: str = 'default',
        expires_in_days: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        创建新的 API Key

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID
            key_name: 密钥名称
            expires_in_days: 过期天数（可选）

        Returns:
            API Key 信息（包含明文密钥）
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                # 验证服务账号存在
                sa = db.query(ServiceAccount).filter(
                    ServiceAccount.id == service_account_id,
                    ServiceAccount.tenant_id == tenant_id,
                    ServiceAccount.status == 'active',
                ).first()

                if not sa:
                    raise ValueError("服务账号不存在或未激活")

                expires_at = None
                if expires_in_days:
                    expires_at = datetime.now() + timedelta(days=expires_in_days)

                result = self._create_api_key_internal(
                    db=db,
                    service_account_id=service_account_id,
                    tenant_id=tenant_id,
                    key_name=key_name,
                    expires_at=expires_at,
                )

                return result

        except Exception as e:
            logger.error(f"创建 API Key 失败: {e}")
            raise

    def _create_api_key_internal(
        self,
        db,
        service_account_id: int,
        tenant_id: int,
        key_name: str,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        内部方法：创建 API Key

        Args:
            db: 数据库会话
            service_account_id: 服务账号ID
            tenant_id: 租户ID
            key_name: 密钥名称
            expires_at: 过期时间

        Returns:
            API Key 信息
        """
        plain_key = f"svc_{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:8]

        key = ServiceAccountKey(
            service_account_id=service_account_id,
            tenant_id=tenant_id,
            key_name=key_name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            status='active',
            expires_at=expires_at,
        )
        db.add(key)
        db.flush()

        return {
            'key_id': key.id,
            'key_name': key.key_name,
            'key_prefix': key.key_prefix,
            'key_plain': plain_key,
            'status': key.status,
            'expires_at': key.expires_at,
            'create_time': key.create_time,
        }

    def list_api_keys(
        self,
        tenant_id: int,
        service_account_id: int,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出服务账号的 API Key

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID
            status: 状态过滤

        Returns:
            API Key 列表（不含明文）
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(ServiceAccountKey).filter(
                    ServiceAccountKey.service_account_id == service_account_id,
                    ServiceAccountKey.tenant_id == tenant_id,
                )

                if status:
                    query = query.filter(ServiceAccountKey.status == status)

                keys = query.order_by(
                    ServiceAccountKey.create_time.desc()
                ).all()

                result = []
                for key in keys:
                    result.append({
                        'key_id': key.id,
                        'key_name': key.key_name,
                        'key_prefix': key.key_prefix,
                        'status': key.status,
                        'expires_at': key.expires_at,
                        'last_used_at': key.last_used_at,
                        'last_used_ip': key.last_used_ip,
                        'create_time': key.create_time,
                    })

                return result

        except Exception as e:
            logger.error(f"列出 API Key 失败: {e}")
            return []

    def revoke_api_key(
        self,
        tenant_id: int,
        service_account_id: int,
        key_id: int,
    ) -> bool:
        """
        吊销 API Key

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID
            key_id: Key ID

        Returns:
            是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                key = db.query(ServiceAccountKey).filter(
                    ServiceAccountKey.id == key_id,
                    ServiceAccountKey.service_account_id == service_account_id,
                    ServiceAccountKey.tenant_id == tenant_id,
                ).first()

                if not key:
                    return False

                key.status = 'revoked'
                return True

        except Exception as e:
            logger.error(f"吊销 API Key 失败: {e}")
            return False

    def rotate_api_key(
        self,
        tenant_id: int,
        service_account_id: int,
        key_id: int,
        expiration_grace_days: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """
        轮换 API Key

        创建新密钥，旧密钥在宽限期后失效。

        Args:
            tenant_id: 租户ID
            service_account_id: 服务账号ID
            key_id: 旧 Key ID
            expiration_grace_days: 旧密钥宽限天数

        Returns:
            新 API Key 信息
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                old_key = db.query(ServiceAccountKey).filter(
                    ServiceAccountKey.id == key_id,
                    ServiceAccountKey.service_account_id == service_account_id,
                    ServiceAccountKey.tenant_id == tenant_id,
                    ServiceAccountKey.status == 'active',
                ).first()

                if not old_key:
                    return None

                # 设置旧密钥过期时间
                old_key.status = 'expiring'
                old_key.expires_at = datetime.now() + timedelta(days=expiration_grace_days)

                # 创建新密钥
                new_key = self._create_api_key_internal(
                    db=db,
                    service_account_id=service_account_id,
                    tenant_id=tenant_id,
                    key_name=f"{old_key.key_name}_rotated",
                )

                # 更新服务账号的当前密钥
                sa = db.query(ServiceAccount).filter(
                    ServiceAccount.id == service_account_id
                ).first()
                if sa and sa.current_api_key_id == key_id:
                    sa.current_api_key_id = new_key['key_id']

                return new_key

        except Exception as e:
            logger.error(f"轮换 API Key 失败: {e}")
            return None

    # ============================================================
    # 服务账号认证
    # ============================================================

    def validate_service_account_key(
        self,
        api_key_plain: str,
        client_ip: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        验证服务账号 API Key

        Args:
            api_key_plain: API Key 明文
            client_ip: 客户端IP（用于 IP 白名单检查）

        Returns:
            服务账号信息，如果无效返回 None
        """
        try:
            if not api_key_plain:
                return None

            key_hash = hashlib.sha256(api_key_plain.encode()).hexdigest()

            with get_db() as db:
                if db is None:
                    return None

                key = db.query(ServiceAccountKey).filter(
                    ServiceAccountKey.key_hash == key_hash,
                    ServiceAccountKey.status == 'active',
                ).first()

                if not key:
                    return None

                if key.expires_at and key.expires_at < datetime.now():
                    key.status = 'revoked'
                    return None

                sa = db.query(ServiceAccount).filter(
                    ServiceAccount.id == key.service_account_id,
                    ServiceAccount.status == 'active',
                ).first()

                if not sa:
                    return None

                if sa.expires_at and sa.expires_at < datetime.now():
                    return None

                # IP 白名单检查
                allowed_ips = self._parse_json(sa.allowed_ips, [])
                if allowed_ips and client_ip:
                    if client_ip not in allowed_ips:
                        logger.warning(f"服务账号 IP 不在白名单: sa={sa.account_name}, ip={client_ip}")
                        return None

                # 更新使用信息
                key.last_used_at = datetime.now()
                key.last_used_ip = client_ip
                sa.last_used_at = datetime.now()
                sa.last_used_ip = client_ip

                # 获取配额信息
                quota = db.query(TenantQuota).filter(
                    TenantQuota.tenant_id == sa.tenant_id
                ).first()

                return {
                    'tenant_id': sa.tenant_id,
                    'service_account_id': sa.id,
                    'account_name': sa.account_name,
                    'display_name': sa.display_name,
                    'role': sa.role,
                    'permissions': self._role_to_permissions(sa.role),
                    'rate_limit': sa.rate_limit,
                    'allowed_scopes': self._parse_json(sa.allowed_scopes, []),
                    'key_id': key.id,
                    'key_name': key.key_name,
                    'auth_method': 'service_account',
                }

        except Exception as e:
            logger.error(f"验证服务账号 API Key 失败: {e}")
            return None

    # ============================================================
    # 辅助方法
    # ============================================================

    @staticmethod
    def _role_to_permissions(role: str) -> List[str]:
        """角色到权限的映射"""
        mapping = {
            'tenant_admin': ['read', 'write', 'admin', 'tenant_admin'],
            'admin': ['read', 'write', 'admin'],
            'operator': ['read', 'write'],
            'viewer': ['read'],
        }
        return mapping.get(role, ['read'])

    @staticmethod
    def _parse_json(value: Optional[str], default: Any) -> Any:
        """解析 JSON 字符串"""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default

    def _sa_to_dict(self, sa: ServiceAccount) -> Dict[str, Any]:
        """将服务账号转换为字典"""
        return {
            'id': sa.id,
            'tenant_id': sa.tenant_id,
            'account_name': sa.account_name,
            'display_name': sa.display_name,
            'description': sa.description,
            'status': sa.status,
            'role': sa.role,
            'rate_limit': sa.rate_limit,
            'allowed_ips': self._parse_json(sa.allowed_ips, []),
            'allowed_scopes': self._parse_json(sa.allowed_scopes, []),
            'expires_at': sa.expires_at,
            'owner_id': sa.owner_id,
            'owner_name': sa.owner_name,
            'owner_email': sa.owner_email,
            'current_api_key_id': sa.current_api_key_id,
            'last_used_at': sa.last_used_at,
            'last_used_ip': sa.last_used_ip,
            'create_time': sa.create_time,
            'update_time': sa.update_time,
        }


service_account_service = ServiceAccountService()
