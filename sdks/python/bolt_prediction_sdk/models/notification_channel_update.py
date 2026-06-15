"""
NotificationChannelUpdate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class NotificationChannelUpdate(SDKBaseModel):
    """更新通知渠道请求"""

    channel_type: Optional[Any] = Field(default=None)
    channel_name: Optional[Any] = Field(default=None)
    config: Optional[Any] = Field(default=None)
    enabled: Optional[Any] = Field(default=None)
    is_default: Optional[Any] = Field(default=None)
