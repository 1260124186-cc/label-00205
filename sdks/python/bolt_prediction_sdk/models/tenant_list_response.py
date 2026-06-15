"""
TenantListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantListResponse(SDKBaseModel):
    """TenantListResponse"""

    total: int = Field()
    items: List[TenantResponse] = Field()
