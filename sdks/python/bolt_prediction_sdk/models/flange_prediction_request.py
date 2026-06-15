"""
FlangePredictionRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FlangePredictionRequest(SDKBaseModel):
    """法兰面预测请求

Attributes:
    法兰面id: 法兰面唯一标识
    data: 多螺栓预紧力时序数据"""

    flange_id: str = Field(description="法兰面唯一标识")
    data: List[List[List[Any]]] = Field(description="多螺栓预紧力数据，三维数组[螺栓][时间点][时间,预紧力]")
