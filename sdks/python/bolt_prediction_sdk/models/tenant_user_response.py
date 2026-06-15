"""
TenantUserResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantUserResponse(SDKBaseModel):
    """TenantUserResponse"""

    id: int = Field()
    tenant_id: int = Field()
    username: str = Field()
    display_name: Optional[Any] = Field(default=None)
    email: Optional[Any] = Field(default=None)
    phone: Optional[Any] = Field(default=None)
    role: str = Field()
    org_node_id: Optional[Any] = Field(default=None)
    status: str = Field()
    last_login_time: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
    update_time: datetime = Field()
