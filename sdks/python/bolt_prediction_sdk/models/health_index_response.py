"""
HealthIndexResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthIndexResponse(SDKBaseModel):
    """健康度计算响应"""

    node_id: str = Field()
    node_type: str = Field()
    health_data: HealthIndexDetailSchema = Field()
    saved: bool = Field()
    calculate_time: datetime = Field()
