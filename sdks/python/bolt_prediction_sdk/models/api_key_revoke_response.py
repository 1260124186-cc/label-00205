"""
APIKeyRevokeResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiKeyRevokeResponse(SDKBaseModel):
    """APIKeyRevokeResponse"""

    key_id: str = Field(description="被吊销的密钥ID")
    revoked: Optional[bool] = Field(description="是否成功吊销", default=True)
