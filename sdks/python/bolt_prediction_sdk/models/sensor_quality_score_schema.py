"""
SensorQualityScoreSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class SensorQualityScoreSchema(SDKBaseModel):
    """传感器质量评分"""

    sensor_id: str = Field()
    overall_score: float = Field()
    overall_level: str = Field()
    dimensions: Dict[str, QualityDimensionScoreSchema] = Field()
    valid_for_training: bool = Field()
    confidence_adjustment: float = Field()
    rule_violations_count: Dict[str, int] = Field()
    calculate_time: datetime = Field()
