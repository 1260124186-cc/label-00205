"""
TenantResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantResponse(SDKBaseModel):
    """TenantResponse"""

    id: int = Field()
    tenant_code: str = Field()
    tenant_name: str = Field()
    contact_email: Optional[Any] = Field(default=None)
    contact_phone: Optional[Any] = Field(default=None)
    status: str = Field()
    settings: Optional[Any] = Field(default=None)
    expire_time: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
    update_time: datetime = Field()
