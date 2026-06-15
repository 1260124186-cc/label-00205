"""
EpochMetricsSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EpochMetricsSchema(SDKBaseModel):
    """Epoch指标"""

    epoch: int = Field()
    train_loss: float = Field()
    val_loss: Optional[Any] = Field(default=None)
    train_acc: Optional[Any] = Field(default=None)
    val_acc: Optional[Any] = Field(default=None)
    learning_rate: Optional[Any] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=0)
    timestamp: str = Field()
