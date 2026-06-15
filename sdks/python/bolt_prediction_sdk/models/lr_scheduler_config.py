"""
LRSchedulerConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LrSchedulerConfig(SDKBaseModel):
    """学习率调度器配置"""

    type: Optional[str] = Field(description="调度器类型: none/reduce_on_plateau/step/cosine", default='none')
    factor: Optional[Any] = Field(description="reduce_on_plateau衰减因子", default=0.5)
    patience: Optional[Any] = Field(description="reduce_on_plateau耐心轮数", default=5)
    min_lr: Optional[Any] = Field(description="最小学习率", default=1e-06)
    step_size: Optional[Any] = Field(description="step衰减步长（epoch数）", default=20)
    gamma: Optional[Any] = Field(description="step衰减因子", default=0.5)
    t_max: Optional[Any] = Field(description="cosine最大迭代轮数", default=None)
    eta_min: Optional[Any] = Field(description="cosine最小学习率", default=1e-06)
