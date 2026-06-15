"""
AnomalyStatisticsResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyStatisticsResponse(SDKBaseModel):
    """异常统计响应"""

    total_count: Optional[int] = Field(description="异常总数", default=0)
    confirmed_count: Optional[int] = Field(description="已确认数", default=0)
    unconfirmed_count: Optional[int] = Field(description="未确认数", default=0)
    false_positive_count: Optional[int] = Field(description="误报数", default=0)
    true_anomaly_count: Optional[int] = Field(description="真实异常数", default=0)
    false_positive_rate: Optional[float] = Field(description="误报率", default=0.0)
    type_distribution: Optional[Any] = Field(default=None)
    classification_distribution: Optional[Any] = Field(default=None)
    time_range: Optional[Any] = Field(default=None)
