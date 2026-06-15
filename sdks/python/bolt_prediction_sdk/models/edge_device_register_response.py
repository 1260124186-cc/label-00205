"""
EdgeDeviceRegisterResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeDeviceRegisterResponse(SDKBaseModel):
    """EdgeDeviceRegisterResponse"""

    device_id: str = Field()
    status: str = Field()
    message: str = Field()
    registered_at: str = Field()
