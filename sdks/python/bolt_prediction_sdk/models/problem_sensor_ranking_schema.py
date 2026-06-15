"""
ProblemSensorRankingSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ProblemSensorRankingSchema(SDKBaseModel):
    """问题传感器排行"""

    rank: int = Field()
    sensor_id: str = Field()
    quality_score: float = Field()
    quality_level: str = Field()
    problem_types: List[str] = Field()
    violation_count: int = Field()
    anomaly_count: int = Field()
    collection_anomaly_ratio: float = Field()
    trend: str = Field()
