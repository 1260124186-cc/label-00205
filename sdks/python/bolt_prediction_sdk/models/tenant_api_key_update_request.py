"""
TenantAPIKeyUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantApiKeyUpdateRequest(SDKBaseModel):
    """TenantAPIKeyUpdateRequest"""

    key_name: Optional[Any] = Field(default=None)
    permissions: Optional[Any] = Field(default=None)
    rate_limit: Optional[Any] = Field(default=None)
    status: Optional[Any] = Field(description="状态 active/revoked", default=None)
    expires_at: Optional[Any] = Field(default=None)
