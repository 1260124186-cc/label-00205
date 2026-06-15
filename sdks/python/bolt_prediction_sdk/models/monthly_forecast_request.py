"""
MonthlyForecastRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class MonthlyForecastRequest(SDKBaseModel):
    """月度预测请求"""

    node_id: str = Field()
    node_type: str = Field()
    forecast_days: Optional[int] = Field(default=30)
