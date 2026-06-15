"""
DailyQualityReportSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DailyQualityReportSchema(SDKBaseModel):
    """每日质量报告"""

    report_date: datetime = Field()
    total_sensors: int = Field()
    average_quality_score: float = Field()
    quality_distribution: Dict[str, int] = Field()
    problem_sensors: List[ProblemSensorRankingSchema] = Field()
    recommendations: List[RepairRecommendationSchema] = Field()
    anomaly_statistics: Dict[str, Any] = Field()
    quality_trend: List[Dict[str, Any]] = Field()
    summary: str = Field()
    generated_at: datetime = Field()
