"""
ConfidenceAdjustmentRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ConfidenceAdjustmentRequest(SDKBaseModel):
    """置信度调整请求"""

    sensor_id: str = Field(description="传感器ID")
    original_confidence: float = Field(description="原始置信度")
    data: List[List[Any]] = Field(description="时序数据")
