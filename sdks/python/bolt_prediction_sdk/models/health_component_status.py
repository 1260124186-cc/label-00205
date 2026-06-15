"""
HealthComponentStatus 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthComponentStatus(SDKBaseModel):
    """组件健康状态"""

    status: str = Field()
    message: Optional[Any] = Field(default=None)
