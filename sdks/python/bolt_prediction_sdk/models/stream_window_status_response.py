"""
StreamWindowStatusResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamWindowStatusResponse(SDKBaseModel):
    """流式窗口状态响应"""

    bolt_id: str = Field()
    window_size: int = Field()
    current_size: int = Field()
    is_full: bool = Field()
    last_updated: Optional[Any] = Field(default=None)
    last_prediction_status: Optional[Any] = Field(default=None)
    prediction_count: Optional[Any] = Field(default=None)
    first_timestamp: Optional[Any] = Field(default=None)
    last_timestamp: Optional[Any] = Field(default=None)
