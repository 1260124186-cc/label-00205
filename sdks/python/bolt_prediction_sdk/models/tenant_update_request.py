"""
TenantUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantUpdateRequest(SDKBaseModel):
    """TenantUpdateRequest"""

    tenant_name: Optional[Any] = Field(default=None)
    contact_email: Optional[Any] = Field(default=None)
    contact_phone: Optional[Any] = Field(default=None)
    status: Optional[Any] = Field(description="状态 active/suspended/deleted", default=None)
    expire_time: Optional[Any] = Field(default=None)
    settings: Optional[Any] = Field(default=None)
