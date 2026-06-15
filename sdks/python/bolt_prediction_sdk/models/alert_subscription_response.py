"""
AlertSubscriptionResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertSubscriptionResponse(SDKBaseModel):
    """订阅响应"""

    subscriber_type: str = Field(description="订阅者类型 role/user/device")
    subscriber_id: str = Field(description="订阅者ID")
    subscriber_name: Optional[Any] = Field(description="订阅者名称", default=None)
    min_alert_level: Optional[int] = Field(description="最低订阅级别", default=1)
    alert_levels: Optional[Any] = Field(description="订阅的告警级别列表", default=None)
    node_type: Optional[str] = Field(description="节点类型过滤 bolt/flange/all", default='all')
    node_ids: Optional[Any] = Field(description="节点ID列表", default=None)
    notify_channels: Optional[Any] = Field(description="通知渠道列表", default=None)
    notify_targets: Optional[Any] = Field(description="通知目标 {渠道: [目标]}", default=None)
    enabled: Optional[bool] = Field(description="是否启用", default=True)
    id: int = Field()
    create_time: datetime = Field()
    update_time: datetime = Field()
