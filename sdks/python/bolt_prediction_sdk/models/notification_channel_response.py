"""
NotificationChannelResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class NotificationChannelResponse(SDKBaseModel):
    """通知渠道响应"""

    channel_type: str = Field(description="渠道类型 email/sms/webhook/dingtalk/wechat")
    channel_name: Optional[Any] = Field(description="渠道名称", default=None)
    config: Optional[Any] = Field(description="渠道配置", default=None)
    enabled: Optional[bool] = Field(description="是否启用", default=True)
    is_default: Optional[bool] = Field(description="是否默认渠道", default=False)
    id: int = Field()
    create_time: datetime = Field()
    update_time: datetime = Field()
