"""
StreamModeSwitchResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamModeSwitchResponse(SDKBaseModel):
    """流式预测模式切换响应"""

    success: bool = Field()
    current_mode: str = Field()
    message: str = Field()
