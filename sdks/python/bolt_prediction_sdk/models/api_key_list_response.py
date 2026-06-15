"""
APIKeyListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiKeyListResponse(SDKBaseModel):
    """APIKeyListResponse"""

    total: int = Field(description="总数")
    items: Optional[List[ApiKeyInfoResponse]] = Field(description="密钥列表", default=[])
