"""
BoltPredictionRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltPredictionRequest(SDKBaseModel):
    """螺栓预测请求

Attributes:
    螺栓id: 螺栓唯一标识
    data: 预紧力时序数据 [[时间, 预紧力], ...]"""

    bolt_id: str = Field(description="螺栓唯一标识")
    data: List[List[Any]] = Field(description="预紧力时序数据，每个元素为[时间字符串, 预紧力值]")
