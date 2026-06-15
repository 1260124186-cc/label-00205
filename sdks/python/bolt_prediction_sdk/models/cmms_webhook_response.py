"""
CmmsWebhookResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsWebhookResponse(SDKBaseModel):
    """CMMS Webhook响应"""

    success: bool = Field()
    message: str = Field()
    processed_count: Optional[Any] = Field(default=0)
