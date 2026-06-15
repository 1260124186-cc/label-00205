"""
TenantCreateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantCreateRequest(SDKBaseModel):
    """TenantCreateRequest"""

    tenant_code: str = Field(description="租户编码")
    tenant_name: str = Field(description="租户名称")
    contact_email: Optional[Any] = Field(description="联系邮箱", default=None)
    contact_phone: Optional[Any] = Field(description="联系电话", default=None)
    expire_time: Optional[Any] = Field(description="到期时间", default=None)
