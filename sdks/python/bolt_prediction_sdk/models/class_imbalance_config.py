"""
ClassImbalanceConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ClassImbalanceConfig(SDKBaseModel):
    """类别不平衡处理配置"""

    strategy: Optional[str] = Field(description="不平衡处理策略: weighted_loss/oversampling/none", default='weighted_loss')
    oversampling_ratio: Optional[Any] = Field(description="过采样倍率", default=1.0)
