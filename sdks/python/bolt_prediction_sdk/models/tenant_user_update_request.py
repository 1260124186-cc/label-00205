"""
TenantUserUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantUserUpdateRequest(SDKBaseModel):
    """TenantUserUpdateRequest"""

    display_name: Optional[Any] = Field(default=None)
    email: Optional[Any] = Field(default=None)
    phone: Optional[Any] = Field(default=None)
    role: Optional[Any] = Field(description="角色 tenant_admin/admin/operator/viewer", default=None)
    org_node_id: Optional[Any] = Field(default=None)
    status: Optional[Any] = Field(description="状态 active/disabled", default=None)
