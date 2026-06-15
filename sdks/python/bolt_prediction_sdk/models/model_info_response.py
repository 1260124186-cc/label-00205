"""
ModelInfoResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelInfoResponse(SDKBaseModel):
    """模型信息响应"""

    model_type: str = Field()
    node_id: str = Field()
    is_trained: bool = Field()
    last_training_time: Any = Field()
    training_samples: Any = Field()
    validation_accuracy: Any = Field()
    version: Optional[Any] = Field(default=None)
    file_hash: Optional[Any] = Field(default=None)
    create_time: Optional[Any] = Field(default=None)
    training_session_id: Optional[Any] = Field(default=None)
    description: Optional[Any] = Field(default=None)
    validation_samples: Optional[Any] = Field(default=None)
    is_incremental: Optional[Any] = Field(default=None)
    parent_version: Optional[Any] = Field(default=None)
    metrics: Optional[Any] = Field(default=None)
    version_history: Optional[Any] = Field(default=None)
