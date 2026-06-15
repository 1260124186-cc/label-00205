"""
StreamBatchIngestRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamBatchIngestRequest(SDKBaseModel):
    """批量流式数据注入请求"""

    messages: List[Dict[str, Any]] = Field(description="消息列表，每个消息包含 node_type, node_id, value/timestamp 或 values/timestamps")
