"""
TenantAPIKeyResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantApiKeyResponse(SDKBaseModel):
    """TenantAPIKeyResponse"""

    id: int = Field()
    tenant_id: int = Field()
    api_key: str = Field()
    key_name: Optional[Any] = Field(default=None)
    permissions: Optional[Any] = Field(default=None)
    rate_limit: int = Field()
    user_id: Optional[Any] = Field(default=None)
    expires_at: Optional[Any] = Field(default=None)
    last_used_at: Optional[Any] = Field(default=None)
    status: str = Field()
    create_time: datetime = Field()
    update_time: datetime = Field()
