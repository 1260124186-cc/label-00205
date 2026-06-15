"""
PredictionCompareListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class PredictionCompareListResponse(SDKBaseModel):
    """预测对比列表响应"""

    total: int = Field()
    items: List[PredictionCompareResponse] = Field()
