"""
EffectEvaluationSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EffectEvaluationSchema(SDKBaseModel):
    """效果评估"""

    overall_rating: Optional[Any] = Field(description="整体评价 excellent/good/fair/poor", default=None)
    effectiveness_score: Optional[Any] = Field(description="效果评分 0-100", default=None)
    fault_resolved: Optional[Any] = Field(description="故障是否解决", default=None)
    recurrence_within_days: Optional[Any] = Field(description="多少天内复发", default=None)
    actual_cost: Optional[Any] = Field(description="实际成本", default=None)
    actual_duration_minutes: Optional[Any] = Field(description="实际耗时（分钟）", default=None)
    side_effects: Optional[Any] = Field(description="副作用/不良影响", default=None)
    improvement_metrics: Optional[Any] = Field(description="改进指标", default=None)
    notes: Optional[Any] = Field(description="备注", default=None)
