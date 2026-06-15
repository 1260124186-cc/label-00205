"""
TrainingSessionSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TrainingSessionSchema(SDKBaseModel):
    """训练会话信息"""

    session_id: str = Field()
    model_id: str = Field()
    model_type: str = Field()
    status: str = Field()
    start_time: Optional[Any] = Field(default=None)
    end_time: Optional[Any] = Field(default=None)
    total_epochs: Optional[int] = Field(default=0)
    current_epoch: Optional[int] = Field(default=0)
    best_metrics: Optional[Dict[str, float]] = Field(default=None)
    metrics_history: Optional[List[EpochMetricsSchema]] = Field(default=None)
    config: Optional[Dict[str, Any]] = Field(default=None)
    error_message: Optional[Any] = Field(default=None)
