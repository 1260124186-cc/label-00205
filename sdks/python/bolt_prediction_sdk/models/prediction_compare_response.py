"""
PredictionCompareResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class PredictionCompareResponse(SDKBaseModel):
    """预测对比响应"""

    id: int = Field()
    work_order_id: int = Field()
    retest_id: Optional[Any] = Field(default=None)
    original_prediction_id: Optional[Any] = Field(default=None)
    retest_prediction_id: Optional[Any] = Field(default=None)
    original_status: Optional[Any] = Field(default=None)
    retest_status: Optional[Any] = Field(default=None)
    original_risk_score: Optional[Any] = Field(default=None)
    retest_risk_score: Optional[Any] = Field(default=None)
    original_confidence: Optional[Any] = Field(default=None)
    retest_confidence: Optional[Any] = Field(default=None)
    risk_change: Optional[Any] = Field(default=None)
    risk_delta: Optional[Any] = Field(default=None)
    status_match: Optional[Any] = Field(default=None)
    is_false_positive: Optional[Any] = Field(default=None)
    is_recurring: Optional[Any] = Field(default=None)
    comparison_detail: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
