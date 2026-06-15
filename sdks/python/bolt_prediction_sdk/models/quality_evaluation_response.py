"""
QualityEvaluationResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class QualityEvaluationResponse(SDKBaseModel):
    """质量评估完整响应"""

    sensor_id: str = Field()
    quality_check: QualityCheckResultSchema = Field()
    quality_score: SensorQualityScoreSchema = Field()
    filter_result: FilteredDataResultSchema = Field()
    anomaly_classification: Optional[Any] = Field(default=None)
    evaluate_time: datetime = Field()
