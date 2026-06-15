"""
TrainingSessionListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TrainingSessionListResponse(SDKBaseModel):
    """训练会话列表响应"""

    total: int = Field()
    items: List[TrainingSessionSchema] = Field()
