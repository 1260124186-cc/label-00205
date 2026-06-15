"""
StreamConfigResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamConfigResponse(SDKBaseModel):
    """流式预测配置响应"""

    success: bool = Field()
    config: Dict[str, Any] = Field()
    message: str = Field()
