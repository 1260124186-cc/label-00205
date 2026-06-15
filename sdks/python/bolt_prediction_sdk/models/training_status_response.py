"""
TrainingStatusResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TrainingStatusResponse(SDKBaseModel):
    """训练状态响应"""

    is_training: bool = Field()
    current_session: Optional[Any] = Field(default=None)
    recent_sessions: Optional[List[TrainingSessionSchema]] = Field(default=None)
