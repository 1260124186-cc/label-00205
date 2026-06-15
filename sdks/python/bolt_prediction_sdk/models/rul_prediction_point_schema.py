"""
RULPredictionPointSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RulPredictionPointSchema(SDKBaseModel):
    """RUL预测点"""

    date: datetime = Field()
    predicted_hi: float = Field()
    lower_bound: float = Field()
    upper_bound: float = Field()
