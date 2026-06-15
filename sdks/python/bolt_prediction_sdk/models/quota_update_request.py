"""
QuotaUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class QuotaUpdateRequest(SDKBaseModel):
    """QuotaUpdateRequest"""

    max_models: Optional[Any] = Field(default=None)
    max_api_calls_per_day: Optional[Any] = Field(default=None)
    max_storage_mb: Optional[Any] = Field(default=None)
    max_users: Optional[Any] = Field(default=None)
    max_org_nodes: Optional[Any] = Field(default=None)
