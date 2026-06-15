"""
RULPredictionSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RulPredictionSchema(SDKBaseModel):
    """剩余使用寿命预测"""

    node_id: str = Field()
    node_type: str = Field(description="节点类型 bolt/flange")
    current_hi: float = Field()
    rul_days: float = Field(description="预测剩余使用寿命（天）")
    rul_lower_bound: float = Field(description="RUL下限（天）")
    rul_upper_bound: float = Field(description="RUL上限（天）")
    rul_confidence: float = Field(description="RUL预测置信度")
    failure_threshold: Optional[float] = Field(description="故障阈值 HI", default=30)
    warning_threshold: Optional[float] = Field(description="预警阈值 HI", default=50)
    days_to_warning: Optional[Any] = Field(description="距离预警的天数", default=None)
    historical_hi: List[Dict[str, Any]] = Field(description="历史HI序列")
    forecast_series: List[RulPredictionPointSchema] = Field(description="预测序列")
    degradation_model: str = Field(description="劣化模型类型 linear/exponential/polynomial")
    model_params: Dict[str, Any] = Field(description="模型参数")
    prediction_date: datetime = Field()
