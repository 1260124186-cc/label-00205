"""
StreamBatchIngestResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamBatchIngestResponse(SDKBaseModel):
    """批量流式数据注入响应"""

    success: bool = Field()
    total_count: int = Field()
    accepted_count: int = Field()
    rejected_count: int = Field()
    messages: Optional[List[Dict[str, Any]]] = Field(default=[])
