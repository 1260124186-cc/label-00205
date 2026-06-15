"""
HealthResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthResponse(SDKBaseModel):
    """健康检查响应"""

    status: Optional[str] = Field(default='healthy')
    version: str = Field()
    timestamp: datetime = Field()
    components: Optional[Any] = Field(default=None)
