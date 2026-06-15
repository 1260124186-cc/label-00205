"""
TrainingConfigSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TrainingConfigSchema(SDKBaseModel):
    """完整训练配置"""

    epochs: Optional[Any] = Field(description="总训练轮数", default=None)
    batch_size: Optional[Any] = Field(description="批次大小", default=None)
    learning_rate: Optional[Any] = Field(description="初始学习率", default=None)
    validation_split: Optional[Any] = Field(description="验证集比例", default=None)
    early_stopping: Optional[Any] = Field(description="早停配置", default=None)
    lr_scheduler: Optional[Any] = Field(description="学习率调度配置", default=None)
    class_imbalance: Optional[Any] = Field(description="类别不平衡处理配置", default=None)
    incremental: Optional[Any] = Field(description="增量训练配置", default=None)
    focal_loss: Optional[Any] = Field(description="Focal Loss配置", default=None)
