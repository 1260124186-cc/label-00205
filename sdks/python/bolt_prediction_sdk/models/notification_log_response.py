"""
NotificationLogResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class NotificationLogResponse(SDKBaseModel):
    """通知日志响应"""

    id: int = Field()
    alert_id: Optional[Any] = Field(default=None)
    channel_type: Optional[Any] = Field(default=None)
    subscriber_id: Optional[Any] = Field(default=None)
    subscriber_name: Optional[Any] = Field(default=None)
    target: Optional[Any] = Field(default=None)
    title: Optional[Any] = Field(default=None)
    content: Optional[Any] = Field(default=None)
    status: str = Field()
    error_message: Optional[Any] = Field(default=None)
    retry_count: Optional[int] = Field(default=0)
    send_time: datetime = Field()
