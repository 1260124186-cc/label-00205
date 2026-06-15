"""
CmmsSyncResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsSyncResponse(SDKBaseModel):
    """CMMS同步响应"""

    success: bool = Field()
    sync_log_id: Optional[Any] = Field(default=None)
    external_id: Optional[Any] = Field(default=None)
    message: Optional[Any] = Field(default=None)
