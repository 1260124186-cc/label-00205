"""
BoltEnsemblePredictionRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltEnsemblePredictionRequest(SDKBaseModel):
    """螺栓集成学习预测调试请求"""

    bolt_id: str = Field(description="螺栓唯一标识")
    data: List[float] = Field(description="预紧力时序数据")
    version: Optional[Any] = Field(description="模型版本号", default=None)
    method: Optional[Any] = Field(description="投票策略: hard / soft / weighted", default=None)
    weights: Optional[Any] = Field(description="自定义权重", default=None)
