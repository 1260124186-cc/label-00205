"""
ConfidenceAdjustmentResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ConfidenceAdjustmentResponse(SDKBaseModel):
    """置信度调整响应"""

    sensor_id: str = Field()
    original_confidence: float = Field()
    adjusted_confidence: float = Field()
    quality_score: float = Field()
    quality_level: str = Field()
    adjustment_factor: float = Field()
    reasons: List[str] = Field()
