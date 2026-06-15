"""
EdgeDeviceHeartbeatResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeDeviceHeartbeatResponse(SDKBaseModel):
    """EdgeDeviceHeartbeatResponse"""

    device_id: str = Field()
    latest_model_version: Optional[Any] = Field(default=None)
    force_sync: Optional[bool] = Field(default=False)
    server_time: str = Field()
