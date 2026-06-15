"""
StreamConfigUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamConfigUpdateRequest(SDKBaseModel):
    """流式预测配置更新请求"""

    window_size: Optional[Any] = Field(description="窗口大小", default=None)
    max_concurrent_streams: Optional[Any] = Field(description="最大并发流数", default=None)
    rate_per_stream: Optional[Any] = Field(description="每个流的速率限制（每秒）", default=None)
