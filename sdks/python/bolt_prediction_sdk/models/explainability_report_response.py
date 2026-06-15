"""
ExplainabilityReportResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ExplainabilityReportResponse(SDKBaseModel):
    """可解释性报告响应"""

    prediction_id: str = Field()
    attention_weights: Optional[Any] = Field(default=None)
    key_timesteps: Optional[Any] = Field(default=None)
    risk_factor_decomposition: Optional[Any] = Field(default=None)
    rule_hits: Optional[Any] = Field(default=None)
    strategy_adjustment: Optional[Any] = Field(default=None)
