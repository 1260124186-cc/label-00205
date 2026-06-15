"""
EdgeDeviceRegisterRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeDeviceRegisterRequest(SDKBaseModel):
    """EdgeDeviceRegisterRequest"""

    device_id: str = Field(description="边缘设备ID")
    device_name: Optional[Any] = Field(description="设备名称", default=None)
    device_type: Optional[Any] = Field(description="设备类型", default=None)
    location: Optional[Any] = Field(description="设备位置", default=None)
    capabilities: Optional[Any] = Field(description="设备能力", default=None)
