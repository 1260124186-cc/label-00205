"""
CmmsSyncLogResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsSyncLogResponse(SDKBaseModel):
    """CMMS同步日志响应"""

    id: int = Field()
    config_id: Optional[Any] = Field(default=None)
    sync_type: Optional[Any] = Field(default=None)
    sync_direction: Optional[Any] = Field(default=None)
    work_order_id: Optional[Any] = Field(default=None)
    external_id: Optional[Any] = Field(default=None)
    status: Optional[Any] = Field(default=None)
    error_message: Optional[Any] = Field(default=None)
    retry_count: Optional[Any] = Field(default=None)
    sync_time: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
