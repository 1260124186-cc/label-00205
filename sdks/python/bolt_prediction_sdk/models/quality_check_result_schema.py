"""
QualityCheckResultSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class QualityCheckResultSchema(SDKBaseModel):
    """质量检查结果"""

    sensor_id: str = Field()
    total_points: int = Field()
    valid_points: int = Field()
    overall_score: float = Field()
    rule_scores: Dict[str, float] = Field()
    violations: List[RuleViolationSchema] = Field()
    violation_count: int = Field()
    check_time: datetime = Field()
