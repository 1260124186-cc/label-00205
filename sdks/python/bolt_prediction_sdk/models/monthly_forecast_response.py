"""
MonthlyForecastResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class MonthlyForecastResponse(SDKBaseModel):
    """月度预测响应"""

    node_id: str = Field()
    node_type: str = Field()
    pw_type: str = Field()
    fault_type: Any = Field()
    begin_time: Any = Field()
    end_time: Any = Field()
    confidence: float = Field()
    rec_measures: str = Field()
    forecast_dates: List[datetime] = Field()
    forecast_values: List[float] = Field()
