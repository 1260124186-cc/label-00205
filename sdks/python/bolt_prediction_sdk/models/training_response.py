"""
TrainingResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TrainingResponse(SDKBaseModel):
    """模型训练响应"""

    model_type: str = Field()
    node_id: Any = Field()
    status: str = Field()
    message: str = Field()
    training_time: float = Field()
    metrics: Optional[Any] = Field(default=None)
