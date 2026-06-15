"""
RULPredictionRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RulPredictionRequest(SDKBaseModel):
    """RUL预测请求"""

    node_id: str = Field(description="节点ID")
    node_type: str = Field(description="节点类型 bolt/flange")
    forecast_days: Optional[int] = Field(description="预测天数", default=180)
    failure_threshold: Optional[float] = Field(description="故障阈值 HI", default=30)
    warning_threshold: Optional[float] = Field(description="预警阈值 HI", default=50)
    model_type: Optional[Any] = Field(description="劣化模型类型，None则自动选择", default=None)
    use_history_days: Optional[int] = Field(description="使用多少天历史数据", default=90)
