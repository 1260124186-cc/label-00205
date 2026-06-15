"""
FocalLossConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FocalLossConfig(SDKBaseModel):
    """Focal Loss配置"""

    enabled: Optional[bool] = Field(description="是否启用Focal Loss", default=False)
    gamma: Optional[float] = Field(description="聚焦参数gamma，难例加权系数", default=2.0)
    alpha: Optional[Any] = Field(description="类别权重alpha列表", default=None)
