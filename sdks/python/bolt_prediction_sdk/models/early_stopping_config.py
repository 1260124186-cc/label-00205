"""
EarlyStoppingConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EarlyStoppingConfig(SDKBaseModel):
    """早停配置"""

    enabled: Optional[bool] = Field(description="是否启用早停", default=True)
    patience: Optional[int] = Field(description="耐心轮数，连续多少轮无提升则停止", default=10)
    min_delta: Optional[float] = Field(description="最小改进阈值", default=0.001)
    mode: Optional[str] = Field(description="监控模式 min=损失最小化/max=准确率最大化", default='min')
