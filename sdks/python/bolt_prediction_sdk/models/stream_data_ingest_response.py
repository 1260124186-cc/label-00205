"""
StreamDataIngestResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamDataIngestResponse(SDKBaseModel):
    """流式数据注入响应"""

    success: bool = Field()
    message: str = Field()
    node_id: Optional[Any] = Field(default=None)
    node_type: Optional[Any] = Field(default=None)
    window_current_size: Optional[Any] = Field(default=None)
    window_is_full: Optional[Any] = Field(default=None)
    accepted: Optional[bool] = Field(default=True)
