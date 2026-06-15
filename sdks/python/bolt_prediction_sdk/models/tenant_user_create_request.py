"""
TenantUserCreateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantUserCreateRequest(SDKBaseModel):
    """TenantUserCreateRequest"""

    username: str = Field(description="用户名")
    password: str = Field(description="密码")
    display_name: Optional[Any] = Field(description="显示名称", default=None)
    email: Optional[Any] = Field(description="邮箱", default=None)
    phone: Optional[Any] = Field(description="手机号", default=None)
    role: Optional[str] = Field(description="角色 tenant_admin/admin/operator/viewer", default='viewer')
    org_node_id: Optional[Any] = Field(description="关联组织节点ID", default=None)
