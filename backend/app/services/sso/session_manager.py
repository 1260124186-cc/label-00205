import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from app.utils.database import get_db, UserSession, TenantUser
from app.utils.config import config


class SessionManager:
    """
    会话管理器

    功能:
    1. 创建用户会话
    2. 验证会话有效性
    3. 会话续期
    4. 强制登出（撤销会话）
    5. 批量登出（用户/租户级别）
    6. 会话列表查询
    """

    def create_session(
        self,
        tenant_id: int,
        user_id: int,
        username: str,
        display_name: Optional[str] = None,
        auth_method: str = 'password',
        sso_provider_id: Optional[int] = None,
        idp_session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        max_age_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        创建用户会话

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            username: 用户名
            display_name: 显示名称
            auth_method: 认证方式
            sso_provider_id: SSO 提供者ID
            idp_session_id: IdP 会话ID
            ip_address: 客户端IP
            user_agent: 用户代理
            device_info: 设备信息
            max_age_seconds: 会话最大时长（秒）

        Returns:
            会话信息字典
        """
        from .jwt_manager import jwt_manager
        import json

        session_id = secrets.token_hex(32)

        if max_age_seconds is None:
            sso_config = config.get('sso', {})
            max_age_seconds = sso_config.get('session_max_age', 86400)

        expires_at = datetime.now() + timedelta(seconds=max_age_seconds)

        subject = {
            'tenant_id': tenant_id,
            'user_id': user_id,
            'username': username,
            'session_id': session_id,
        }

        access_token, access_jti = jwt_manager.create_access_token(
            subject=subject,
            extra_claims={
                'tenant_id': tenant_id,
                'user_id': user_id,
                'username': username,
                'session_id': session_id,
            }
        )

        refresh_token, refresh_jti = jwt_manager.create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
        )

        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        sso_config = config.get('sso', {})
        refresh_ttl = sso_config.get('refresh_token_ttl', 604800)
        refresh_expires_at = datetime.now() + timedelta(seconds=refresh_ttl)

        try:
            with get_db() as db:
                if db is None:
                    return {
                        'session_id': session_id,
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'expires_at': expires_at,
                    }

                session = UserSession(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    username=username,
                    display_name=display_name,
                    auth_method=auth_method,
                    sso_provider_id=sso_provider_id,
                    idp_session_id=idp_session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_info=json.dumps(device_info, ensure_ascii=False) if device_info else None,
                    login_time=datetime.now(),
                    last_activity_time=datetime.now(),
                    expires_at=expires_at,
                    status='active',
                    refresh_token_hash=refresh_token_hash,
                    refresh_expires_at=refresh_expires_at,
                )
                db.add(session)
                db.flush()

        except Exception as e:
            logger.error(f"创建会话失败: {e}")

        return {
            'session_id': session_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at,
            'token_type': 'bearer',
        }

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        验证会话是否有效

        Args:
            session_id: 会话ID

        Returns:
            会话信息，如果无效返回 None
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                session = db.query(UserSession).filter(
                    UserSession.session_id == session_id
                ).first()

                if not session:
                    return None

                if session.status != 'active':
                    return None

                if session.expires_at and session.expires_at < datetime.now():
                    session.status = 'expired'
                    return None

                session.last_activity_time = datetime.now()

                return {
                    'session_id': session.session_id,
                    'tenant_id': session.tenant_id,
                    'user_id': session.user_id,
                    'username': session.username,
                    'display_name': session.display_name,
                    'auth_method': session.auth_method,
                    'sso_provider_id': session.sso_provider_id,
                    'login_time': session.login_time,
                    'last_activity_time': session.last_activity_time,
                    'expires_at': session.expires_at,
                    'ip_address': session.ip_address,
                }

        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None

    def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        刷新会话（使用刷新令牌）

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的访问令牌和刷新令牌
        """
        from .jwt_manager import jwt_manager
        import json

        try:
            payload = jwt_manager.verify_token(refresh_token, token_type='refresh')
            if not payload:
                return None

            subject = jwt_manager.get_subject(payload)
            if not subject:
                return None

            user_id = subject.get('user_id')
            tenant_id = subject.get('tenant_id')
            session_id = payload.get('session_id')

            refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

            with get_db() as db:
                if db is None:
                    return None

                session = db.query(UserSession).filter(
                    UserSession.session_id == session_id,
                    UserSession.status == 'active',
                ).first()

                if not session:
                    return None

                if session.refresh_token_hash != refresh_token_hash:
                    return None

                if session.refresh_expires_at and session.refresh_expires_at < datetime.now():
                    return None

                user = db.query(TenantUser).filter(
                    TenantUser.id == user_id,
                    TenantUser.tenant_id == tenant_id,
                ).first()

                if not user or user.status != 'active':
                    return None

                new_subject = {
                    'tenant_id': tenant_id,
                    'user_id': user_id,
                    'username': user.username,
                    'session_id': session_id,
                }

                new_access_token, _ = jwt_manager.create_access_token(
                    subject=new_subject,
                    extra_claims={
                        'tenant_id': tenant_id,
                        'user_id': user_id,
                        'username': user.username,
                        'session_id': session_id,
                    }
                )

                sso_config = config.get('sso', {})
                session_ttl = sso_config.get('session_max_age', 86400)
                session.expires_at = datetime.now() + timedelta(seconds=session_ttl)
                session.last_activity_time = datetime.now()

                new_refresh_token, new_refresh_jti = jwt_manager.create_refresh_token(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    session_id=session_id,
                )
                new_refresh_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
                session.refresh_token_hash = new_refresh_hash

                refresh_ttl = sso_config.get('refresh_token_ttl', 604800)
                session.refresh_expires_at = datetime.now() + timedelta(seconds=refresh_ttl)

                return {
                    'access_token': new_access_token,
                    'refresh_token': new_refresh_token,
                    'token_type': 'bearer',
                    'session_id': session_id,
                }

        except Exception as e:
            logger.error(f"刷新会话失败: {e}")
            return None

    def revoke_session(
        self,
        session_id: str,
        reason: str = 'user_logout',
        revoked_by: Optional[str] = None,
    ) -> bool:
        """
        撤销单个会话（强制登出）

        Args:
            session_id: 会话ID
            reason: 撤销原因
            revoked_by: 撤销人

        Returns:
            是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                session = db.query(UserSession).filter(
                    UserSession.session_id == session_id
                ).first()

                if not session:
                    return False

                session.status = 'revoked'
                session.revoke_reason = reason
                session.revoke_time = datetime.now()
                session.revoked_by = revoked_by

                return True

        except Exception as e:
            logger.error(f"撤销会话失败: {e}")
            return False

    def revoke_user_sessions(
        self,
        tenant_id: int,
        user_id: int,
        reason: str = 'user_forced_logout',
        revoked_by: Optional[str] = None,
        exclude_session_id: Optional[str] = None,
    ) -> int:
        """
        撤销用户的所有会话

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            reason: 撤销原因
            revoked_by: 撤销人
            exclude_session_id: 排除的会话ID（保留当前会话）

        Returns:
            撤销的会话数量
        """
        try:
            with get_db() as db:
                if db is None:
                    return 0

                query = db.query(UserSession).filter(
                    UserSession.tenant_id == tenant_id,
                    UserSession.user_id == user_id,
                    UserSession.status == 'active',
                )

                if exclude_session_id:
                    query = query.filter(UserSession.session_id != exclude_session_id)

                sessions = query.all()
                count = 0
                for session in sessions:
                    session.status = 'revoked'
                    session.revoke_reason = reason
                    session.revoke_time = datetime.now()
                    session.revoked_by = revoked_by
                    count += 1

                return count

        except Exception as e:
            logger.error(f"批量撤销用户会话失败: {e}")
            return 0

    def revoke_tenant_sessions(
        self,
        tenant_id: int,
        reason: str = 'tenant_forced_logout',
        revoked_by: Optional[str] = None,
    ) -> int:
        """
        撤销租户的所有会话

        Args:
            tenant_id: 租户ID
            reason: 撤销原因
            revoked_by: 撤销人

        Returns:
            撤销的会话数量
        """
        try:
            with get_db() as db:
                if db is None:
                    return 0

                sessions = db.query(UserSession).filter(
                    UserSession.tenant_id == tenant_id,
                    UserSession.status == 'active',
                ).all()

                count = 0
                for session in sessions:
                    session.status = 'revoked'
                    session.revoke_reason = reason
                    session.revoke_time = datetime.now()
                    session.revoked_by = revoked_by
                    count += 1

                return count

        except Exception as e:
            logger.error(f"批量撤销租户会话失败: {e}")
            return 0

    def list_user_sessions(
        self,
        tenant_id: int,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出用户的所有会话

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            status: 状态过滤
            limit: 数量限制
            offset: 偏移量

        Returns:
            会话列表
        """
        try:
            with get_db() as db:
                if db is None:
                    return []

                query = db.query(UserSession).filter(
                    UserSession.tenant_id == tenant_id,
                    UserSession.user_id == user_id,
                )

                if status:
                    query = query.filter(UserSession.status == status)

                sessions = query.order_by(
                    UserSession.login_time.desc()
                ).offset(offset).limit(limit).all()

                result = []
                for s in sessions:
                    result.append({
                        'session_id': s.session_id,
                        'auth_method': s.auth_method,
                        'sso_provider_id': s.sso_provider_id,
                        'ip_address': s.ip_address,
                        'user_agent': s.user_agent,
                        'login_time': s.login_time,
                        'last_activity_time': s.last_activity_time,
                        'expires_at': s.expires_at,
                        'status': s.status,
                        'is_current': False,
                    })

                return result

        except Exception as e:
            logger.error(f"查询用户会话列表失败: {e}")
            return []

    def get_session_count(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        """
        获取会话数量

        Args:
            tenant_id: 租户ID
            user_id: 用户ID（可选）
            status: 状态过滤

        Returns:
            会话数量
        """
        try:
            with get_db() as db:
                if db is None:
                    return 0

                query = db.query(UserSession).filter(
                    UserSession.tenant_id == tenant_id
                )

                if user_id:
                    query = query.filter(UserSession.user_id == user_id)

                if status:
                    query = query.filter(UserSession.status == status)

                return query.count()

        except Exception as e:
            logger.error(f"获取会话数量失败: {e}")
            return 0

    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        try:
            with get_db() as db:
                if db is None:
                    return 0

                from sqlalchemy import and_

                expired = db.query(UserSession).filter(
                    and_(
                        UserSession.status == 'active',
                        UserSession.expires_at < datetime.now(),
                    )
                ).all()

                count = 0
                for session in expired:
                    session.status = 'expired'
                    count += 1

                if count > 0:
                    logger.info(f"清理了 {count} 个过期会话")

                return count

        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0


session_manager = SessionManager()
