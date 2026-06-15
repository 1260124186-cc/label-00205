"""
AlertListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertListResponse(SDKBaseModel):
    """告警列表响应"""

    total: int = Field()
    items: List[AlertEventResponse] = Field()
