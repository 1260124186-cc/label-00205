"""
EdgeDeviceHeartbeatRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeDeviceHeartbeatRequest(SDKBaseModel):
    """EdgeDeviceHeartbeatRequest"""

    device_id: str = Field()
    model_version: Optional[Any] = Field(default=None)
    cache_size: Optional[int] = Field(default=0)
    unsynced_count: Optional[int] = Field(default=0)
