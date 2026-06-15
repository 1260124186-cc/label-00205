"""
RepairRecommendationSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RepairRecommendationSchema(SDKBaseModel):
    """修复建议"""

    sensor_id: str = Field()
    problem_type: str = Field()
    description: str = Field()
    recommendation: str = Field()
    priority: str = Field()
    estimated_effort: float = Field()
    affected_metrics: List[str] = Field()
    evidence: Dict[str, Any] = Field()
