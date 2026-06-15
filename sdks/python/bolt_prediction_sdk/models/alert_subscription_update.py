"""
AlertSubscriptionUpdate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertSubscriptionUpdate(SDKBaseModel):
    """更新订阅请求"""

    subscriber_type: Optional[Any] = Field(default=None)
    subscriber_id: Optional[Any] = Field(default=None)
    subscriber_name: Optional[Any] = Field(default=None)
    min_alert_level: Optional[Any] = Field(default=None)
    alert_levels: Optional[Any] = Field(default=None)
    node_type: Optional[Any] = Field(default=None)
    node_ids: Optional[Any] = Field(default=None)
    notify_channels: Optional[Any] = Field(default=None)
    notify_targets: Optional[Any] = Field(default=None)
    enabled: Optional[Any] = Field(default=None)
