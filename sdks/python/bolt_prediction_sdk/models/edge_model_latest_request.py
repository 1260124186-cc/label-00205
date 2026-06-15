"""
EdgeModelLatestRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeModelLatestRequest(SDKBaseModel):
    """EdgeModelLatestRequest"""

    model_type: str = Field(description="模型类型 bolt/flange")
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    edge_device_id: Optional[Any] = Field(description="边缘设备ID", default=None)
