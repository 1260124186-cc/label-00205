import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from app.utils.database import (
    get_db,
    Tenant,
    TenantAPIKey,
    TenantQuota,
    TenantUser,
    OrganizationNode,
)


ORG_NODE_TYPES = {"group", "factory", "unit", "flange", "bolt"}
ORG_LEVEL_MAP = {"group": 0, "factory": 1, "unit": 2, "flange": 3, "bolt": 4}
VALID_ROLES = {"tenant_admin", "admin", "operator", "viewer"}
ROLE_HIERARCHY = {"tenant_admin": 0, "admin": 1, "operator": 2, "viewer": 3}


class TenantService:
    def create_tenant(
        self,
        tenant_code: str,
        tenant_name: str,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        expire_time: Optional[datetime] = None,
    ) -> Optional[Tenant]:
        with get_db() as db:
            if db is None:
                return None
            existing = (
                db.query(Tenant)
                .filter(Tenant.tenant_code == tenant_code)
                .first()
            )
            if existing:
                raise ValueError(f"租户编码已存在: {tenant_code}")
            tenant = Tenant(
                tenant_code=tenant_code,
                tenant_name=tenant_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                status="active",
                expire_time=expire_time,
            )
            db.add(tenant)
            db.flush()
            quota = TenantQuota(tenant_id=tenant.id)
            db.add(quota)
            db.flush()
            admin = TenantUser(
                tenant_id=tenant.id,
                username="admin",
                password_hash=self._hash_password("admin123"),
                display_name="租户管理员",
                role="tenant_admin",
                status="active",
            )
            db.add(admin)
            db.flush()
            return tenant

    def get_tenant(self, tenant_id: int) -> Optional[Tenant]:
        with get_db() as db:
            if db is None:
                return None
            return db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_code(self, tenant_code: str) -> Optional[Tenant]:
        with get_db() as db:
            if db is None:
                return None
            return (
                db.query(Tenant)
                .filter(Tenant.tenant_code == tenant_code)
                .first()
            )

    def list_tenants(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Tenant]:
        with get_db() as db:
            if db is None:
                return []
            q = db.query(Tenant)
            if status:
                q = q.filter(Tenant.status == status)
            return q.order_by(Tenant.id.desc()).offset(offset).limit(limit).all()

    def update_tenant(self, tenant_id: int, **kwargs) -> Optional[Tenant]:
        with get_db() as db:
            if db is None:
                return None
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                return None
            for k, v in kwargs.items():
                if v is not None and hasattr(tenant, k):
                    if k == "settings" and isinstance(v, dict):
                        v = json.dumps(v, ensure_ascii=False)
                    setattr(tenant, k, v)
            db.flush()
            return tenant

    def delete_tenant(self, tenant_id: int) -> bool:
        with get_db() as db:
            if db is None:
                return False
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                return False
            tenant.status = "deleted"
            db.flush()
            return True

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(8)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${h}"

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        try:
            salt, h = password_hash.split("$", 1)
            return hashlib.sha256((salt + password).encode()).hexdigest() == h
        except Exception:
            return False


class OrganizationService:
    def create_node(
        self,
        tenant_id: int,
        node_name: str,
        node_type: str,
        parent_id: Optional[int] = None,
        node_code: Optional[str] = None,
        sort_order: int = 0,
        extra_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[OrganizationNode]:
        if node_type not in ORG_NODE_TYPES:
            raise ValueError(f"无效节点类型: {node_type}, 有效值: {ORG_NODE_TYPES}")
        with get_db() as db:
            if db is None:
                return None
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if not tenant:
                raise ValueError("租户不存在")
            if parent_id:
                parent = (
                    db.query(OrganizationNode)
                    .filter(
                        OrganizationNode.id == parent_id,
                        OrganizationNode.tenant_id == tenant_id,
                    )
                    .first()
                )
                if not parent:
                    raise ValueError("父节点不存在或不属于该租户")
                if ORG_LEVEL_MAP.get(node_type, -1) <= parent.level:
                    raise ValueError(
                        f"子节点类型 {node_type} 的层级必须大于父节点层级 {parent.node_type}"
                    )
            level = ORG_LEVEL_MAP.get(node_type, 0)
            node = OrganizationNode(
                tenant_id=tenant_id,
                parent_id=parent_id,
                node_code=node_code,
                node_name=node_name,
                node_type=node_type,
                level=level,
                sort_order=sort_order,
                extra_info=(
                    json.dumps(extra_info, ensure_ascii=False) if extra_info else None
                ),
                status="active",
            )
            db.add(node)
            db.flush()
            if parent_id:
                parent_node = (
                    db.query(OrganizationNode)
                    .filter(OrganizationNode.id == parent_id)
                    .first()
                )
                node.path = f"{parent_node.path}/{node.id}"
            else:
                node.path = f"/{node.id}"
            db.flush()
            quota = (
                db.query(TenantQuota)
                .filter(TenantQuota.tenant_id == tenant_id)
                .first()
            )
            if quota:
                quota.current_org_node_count = (
                    db.query(OrganizationNode)
                    .filter(OrganizationNode.tenant_id == tenant_id)
                    .count()
                )
            db.flush()
            return node

    def get_node(self, tenant_id: int, node_id: int) -> Optional[OrganizationNode]:
        with get_db() as db:
            if db is None:
                return None
            return (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.id == node_id,
                    OrganizationNode.tenant_id == tenant_id,
                )
                .first()
            )

    def list_nodes(
        self,
        tenant_id: int,
        parent_id: Optional[int] = None,
        node_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[OrganizationNode]:
        with get_db() as db:
            if db is None:
                return []
            q = db.query(OrganizationNode).filter(
                OrganizationNode.tenant_id == tenant_id
            )
            if parent_id is not None:
                q = q.filter(OrganizationNode.parent_id == parent_id)
            if node_type:
                q = q.filter(OrganizationNode.node_type == node_type)
            if status:
                q = q.filter(OrganizationNode.status == status)
            return q.order_by(OrganizationNode.sort_order, OrganizationNode.id).all()

    def get_tree(self, tenant_id: int) -> List[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return []
            nodes = (
                db.query(OrganizationNode)
                .filter(OrganizationNode.tenant_id == tenant_id)
                .order_by(OrganizationNode.sort_order, OrganizationNode.id)
                .all()
            )
            node_map: Dict[int, Dict[str, Any]] = {}
            roots = []
            for n in nodes:
                extra = None
                if n.extra_info:
                    try:
                        extra = json.loads(n.extra_info)
                    except Exception:
                        extra = None
                node_dict = {
                    "id": n.id,
                    "tenant_id": n.tenant_id,
                    "parent_id": n.parent_id,
                    "node_code": n.node_code,
                    "node_name": n.node_name,
                    "node_type": n.node_type,
                    "path": n.path,
                    "level": n.level,
                    "sort_order": n.sort_order,
                    "extra_info": extra,
                    "status": n.status,
                    "create_time": n.create_time,
                    "update_time": n.update_time,
                    "children": [],
                }
                node_map[n.id] = node_dict
                if n.parent_id is None:
                    roots.append(node_dict)
                elif n.parent_id in node_map:
                    node_map[n.parent_id]["children"].append(node_dict)
            return roots

    def update_node(
        self, tenant_id: int, node_id: int, **kwargs
    ) -> Optional[OrganizationNode]:
        with get_db() as db:
            if db is None:
                return None
            node = (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.id == node_id,
                    OrganizationNode.tenant_id == tenant_id,
                )
                .first()
            )
            if not node:
                return None
            for k, v in kwargs.items():
                if v is not None and hasattr(node, k):
                    if k == "extra_info" and isinstance(v, dict):
                        v = json.dumps(v, ensure_ascii=False)
                    setattr(node, k, v)
            db.flush()
            return node

    def delete_node(self, tenant_id: int, node_id: int) -> bool:
        with get_db() as db:
            if db is None:
                return False
            children = (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.parent_id == node_id,
                    OrganizationNode.tenant_id == tenant_id,
                )
                .count()
            )
            if children > 0:
                raise ValueError("存在子节点, 无法删除")
            node = (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.id == node_id,
                    OrganizationNode.tenant_id == tenant_id,
                )
                .first()
            )
            if not node:
                return False
            node.status = "inactive"
            db.flush()
            return True

    def get_ancestors(self, tenant_id: int, node_id: int) -> List[OrganizationNode]:
        with get_db() as db:
            if db is None:
                return []
            node = (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.id == node_id,
                    OrganizationNode.tenant_id == tenant_id,
                )
                .first()
            )
            if not node or not node.path:
                return []
            ancestor_ids = [
                int(x) for x in node.path.strip("/").split("/") if x.strip()
            ]
            ancestor_ids = [aid for aid in ancestor_ids if aid != node_id]
            if not ancestor_ids:
                return []
            return (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.id.in_(ancestor_ids),
                    OrganizationNode.tenant_id == tenant_id,
                )
                .order_by(OrganizationNode.level)
                .all()
            )

    def get_descendants(self, tenant_id: int, node_id: int) -> List[OrganizationNode]:
        with get_db() as db:
            if db is None:
                return []
            return (
                db.query(OrganizationNode)
                .filter(
                    OrganizationNode.tenant_id == tenant_id,
                    OrganizationNode.path.like(f"%/{node_id}/%"),
                )
                .all()
            )


class QuotaService:
    def get_quota(self, tenant_id: int) -> Optional[TenantQuota]:
        with get_db() as db:
            if db is None:
                return None
            return (
                db.query(TenantQuota)
                .filter(TenantQuota.tenant_id == tenant_id)
                .first()
            )

    def update_quota(self, tenant_id: int, **kwargs) -> Optional[TenantQuota]:
        with get_db() as db:
            if db is None:
                return None
            quota = (
                db.query(TenantQuota)
                .filter(TenantQuota.tenant_id == tenant_id)
                .first()
            )
            if not quota:
                return None
            for k, v in kwargs.items():
                if v is not None and hasattr(quota, k):
                    setattr(quota, k, v)
            db.flush()
            return quota

    def check_quota(self, tenant_id: int, resource: str) -> bool:
        quota = self.get_quota(tenant_id)
        if not quota:
            return False
        checks = {
            "model": quota.current_model_count < quota.max_models,
            "api_call": quota.current_api_calls_today < quota.max_api_calls_per_day,
            "storage": quota.current_storage_mb < quota.max_storage_mb,
            "user": quota.current_user_count < quota.max_users,
            "org_node": quota.current_org_node_count < quota.max_org_nodes,
            "training": True,
        }
        if resource == "training":
            try:
                from app.utils.database import get_db, TrainingLog
                with get_db() as db:
                    if db is None:
                        return True
                    running_count = db.query(TrainingLog).filter(
                        TrainingLog.tenant_id == tenant_id,
                        TrainingLog.status.in_(['pending', 'running']),
                    ).count()
                    max_concurrent = getattr(quota, 'max_training_concurrent', 2)
                    return running_count < max_concurrent
            except Exception:
                return True
        return checks.get(resource, False)

    def increment_api_calls(self, tenant_id: int) -> Optional[TenantQuota]:
        with get_db() as db:
            if db is None:
                return None
            quota = (
                db.query(TenantQuota)
                .filter(TenantQuota.tenant_id == tenant_id)
                .first()
            )
            if not quota:
                return None
            today = datetime.now().strftime("%Y-%m-%d")
            if quota.api_call_reset_date != today:
                quota.current_api_calls_today = 1
                quota.api_call_reset_date = today
            else:
                quota.current_api_calls_today += 1
            db.flush()
            return quota


class TenantUserService:
    def create_user(
        self,
        tenant_id: int,
        username: str,
        password: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        role: str = "viewer",
        org_node_id: Optional[int] = None,
    ) -> Optional[TenantUser]:
        if role not in VALID_ROLES:
            raise ValueError(f"无效角色: {role}, 有效值: {VALID_ROLES}")
        with get_db() as db:
            if db is None:
                return None
            existing = (
                db.query(TenantUser)
                .filter(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.username == username,
                )
                .first()
            )
            if existing:
                raise ValueError(f"用户名已存在: {username}")
            user = TenantUser(
                tenant_id=tenant_id,
                username=username,
                password_hash=TenantService._hash_password(password),
                display_name=display_name,
                email=email,
                phone=phone,
                role=role,
                org_node_id=org_node_id,
                status="active",
            )
            db.add(user)
            db.flush()
            quota = (
                db.query(TenantQuota)
                .filter(TenantQuota.tenant_id == tenant_id)
                .first()
            )
            if quota:
                quota.current_user_count = (
                    db.query(TenantUser)
                    .filter(TenantUser.tenant_id == tenant_id)
                    .count()
                )
            db.flush()
            return user

    def get_user(self, tenant_id: int, user_id: int) -> Optional[TenantUser]:
        with get_db() as db:
            if db is None:
                return None
            return (
                db.query(TenantUser)
                .filter(
                    TenantUser.id == user_id, TenantUser.tenant_id == tenant_id
                )
                .first()
            )

    def list_users(
        self,
        tenant_id: int,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TenantUser]:
        with get_db() as db:
            if db is None:
                return []
            q = db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id)
            if role:
                q = q.filter(TenantUser.role == role)
            if status:
                q = q.filter(TenantUser.status == status)
            return q.order_by(TenantUser.id).offset(offset).limit(limit).all()

    def count_users(self, tenant_id: int) -> int:
        with get_db() as db:
            if db is None:
                return 0
            return (
                db.query(TenantUser)
                .filter(TenantUser.tenant_id == tenant_id)
                .count()
            )

    def update_user(
        self, tenant_id: int, user_id: int, **kwargs
    ) -> Optional[TenantUser]:
        with get_db() as db:
            if db is None:
                return None
            user = (
                db.query(TenantUser)
                .filter(
                    TenantUser.id == user_id, TenantUser.tenant_id == tenant_id
                )
                .first()
            )
            if not user:
                return None
            for k, v in kwargs.items():
                if v is not None and hasattr(user, k):
                    setattr(user, k, v)
            db.flush()
            return user

    def change_password(
        self, tenant_id: int, user_id: int, new_password: str
    ) -> bool:
        with get_db() as db:
            if db is None:
                return False
            user = (
                db.query(TenantUser)
                .filter(
                    TenantUser.id == user_id, TenantUser.tenant_id == tenant_id
                )
                .first()
            )
            if not user:
                return False
            user.password_hash = TenantService._hash_password(new_password)
            db.flush()
            return True

    def delete_user(self, tenant_id: int, user_id: int) -> bool:
        with get_db() as db:
            if db is None:
                return False
            user = (
                db.query(TenantUser)
                .filter(
                    TenantUser.id == user_id, TenantUser.tenant_id == tenant_id
                )
                .first()
            )
            if not user:
                return False
            user.status = "disabled"
            db.flush()
            quota = (
                db.query(TenantQuota)
                .filter(TenantQuota.tenant_id == tenant_id)
                .first()
            )
            if quota:
                quota.current_user_count = (
                    db.query(TenantUser)
                    .filter(
                        TenantUser.tenant_id == tenant_id,
                        TenantUser.status == "active",
                    )
                    .count()
                )
            db.flush()
            return True

    def authenticate(
        self, tenant_code: str, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return None
            tenant = (
                db.query(Tenant)
                .filter(Tenant.tenant_code == tenant_code, Tenant.status == "active")
                .first()
            )
            if not tenant:
                return None
            user = (
                db.query(TenantUser)
                .filter(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.username == username,
                    TenantUser.status == "active",
                )
                .first()
            )
            if not user:
                return None
            if not TenantService._verify_password(password, user.password_hash):
                return None
            user.last_login_time = datetime.now()
            db.flush()
            return {
                "tenant_id": tenant.id,
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
            }


class TenantAPIKeyService:
    def create_api_key(
        self,
        tenant_id: int,
        key_name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        rate_limit: int = 1000,
        user_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        plain_key = f"tp_{secrets.token_hex(24)}"
        hashed_key = hashlib.sha256(plain_key.encode()).hexdigest()
        with get_db() as db:
            if db is None:
                return None
            api_key = TenantAPIKey(
                tenant_id=tenant_id,
                api_key=hashed_key,
                key_name=key_name,
                permissions=(
                    json.dumps(permissions, ensure_ascii=False) if permissions else None
                ),
                rate_limit=rate_limit,
                user_id=user_id,
                expires_at=expires_at,
                status="active",
            )
            db.add(api_key)
            db.flush()
            return {
                "id": api_key.id,
                "tenant_id": tenant_id,
                "api_key": hashed_key,
                "api_key_plain": plain_key,
                "key_name": key_name,
                "permissions": permissions,
                "rate_limit": rate_limit,
                "user_id": user_id,
                "expires_at": expires_at,
                "status": "active",
                "create_time": api_key.create_time,
                "update_time": api_key.update_time,
            }

    def get_api_key(self, tenant_id: int, key_id: int) -> Optional[TenantAPIKey]:
        with get_db() as db:
            if db is None:
                return None
            return (
                db.query(TenantAPIKey)
                .filter(
                    TenantAPIKey.id == key_id, TenantAPIKey.tenant_id == tenant_id
                )
                .first()
            )

    def list_api_keys(
        self,
        tenant_id: int,
        status: Optional[str] = None,
    ) -> List[TenantAPIKey]:
        with get_db() as db:
            if db is None:
                return []
            q = db.query(TenantAPIKey).filter(TenantAPIKey.tenant_id == tenant_id)
            if status:
                q = q.filter(TenantAPIKey.status == status)
            return q.order_by(TenantAPIKey.id.desc()).all()

    def update_api_key(
        self, tenant_id: int, key_id: int, **kwargs
    ) -> Optional[TenantAPIKey]:
        with get_db() as db:
            if db is None:
                return None
            api_key = (
                db.query(TenantAPIKey)
                .filter(
                    TenantAPIKey.id == key_id, TenantAPIKey.tenant_id == tenant_id
                )
                .first()
            )
            if not api_key:
                return None
            for k, v in kwargs.items():
                if v is not None and hasattr(api_key, k):
                    if k == "permissions" and isinstance(v, list):
                        v = json.dumps(v, ensure_ascii=False)
                    setattr(api_key, k, v)
            db.flush()
            return api_key

    def revoke_api_key(self, tenant_id: int, key_id: int) -> bool:
        with get_db() as db:
            if db is None:
                return False
            api_key = (
                db.query(TenantAPIKey)
                .filter(
                    TenantAPIKey.id == key_id, TenantAPIKey.tenant_id == tenant_id
                )
                .first()
            )
            if not api_key:
                return False
            api_key.status = "revoked"
            db.flush()
            return True

    def validate_api_key(self, api_key_plain: str) -> Optional[Dict[str, Any]]:
        hashed_key = hashlib.sha256(api_key_plain.encode()).hexdigest()
        with get_db() as db:
            if db is None:
                return None
            api_key = (
                db.query(TenantAPIKey)
                .filter(
                    TenantAPIKey.api_key == hashed_key,
                    TenantAPIKey.status == "active",
                )
                .first()
            )
            if not api_key:
                return None
            if api_key.expires_at and api_key.expires_at < datetime.now():
                return None
            tenant = (
                db.query(Tenant)
                .filter(Tenant.id == api_key.tenant_id, Tenant.status == "active")
                .first()
            )
            if not tenant:
                return None
            api_key.last_used_at = datetime.now()
            db.flush()
            permissions = []
            if api_key.permissions:
                try:
                    permissions = json.loads(api_key.permissions)
                except Exception:
                    permissions = []
            return {
                "tenant_id": api_key.tenant_id,
                "key_id": api_key.id,
                "key_name": api_key.key_name,
                "permissions": permissions,
                "rate_limit": api_key.rate_limit,
                "user_id": api_key.user_id,
            }
