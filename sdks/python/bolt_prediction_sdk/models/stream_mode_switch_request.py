"""
StreamModeSwitchRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamModeSwitchRequest(SDKBaseModel):
    """流式预测模式切换请求"""

    mode: str = Field(description="预测模式: batch 或 stream")
