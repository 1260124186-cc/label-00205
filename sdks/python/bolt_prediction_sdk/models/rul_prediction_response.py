"""
RULPredictionResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RulPredictionResponse(SDKBaseModel):
    """RUL预测响应"""

    node_id: str = Field()
    node_type: str = Field()
    rul_data: RulPredictionSchema = Field()
    calculate_time: datetime = Field()
