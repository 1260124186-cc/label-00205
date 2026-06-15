"""
StreamDataIngestRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamDataIngestRequest(SDKBaseModel):
    """流式数据注入请求

支持单条或微批次数据注入"""

    node_type: str = Field(description="节点类型 bolt/flange")
    node_id: str = Field(description="节点ID")
    value: Optional[Any] = Field(description="单条预紧力值", default=None)
    timestamp: Optional[Any] = Field(description="单条时间戳", default=None)
    values: Optional[Any] = Field(description="批量预紧力值列表", default=None)
    timestamps: Optional[Any] = Field(description="批量时间戳列表", default=None)
    data: Optional[Any] = Field(description="时序数据 [[时间, 预紧力], ...]", default=None)
    metadata: Optional[Any] = Field(description="元数据", default=None)
