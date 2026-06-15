"""
AlertRuleUpdate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertRuleUpdate(SDKBaseModel):
    """更新告警规则请求"""

    rule_name: Optional[Any] = Field(default=None)
    alert_level: Optional[Any] = Field(default=None)
    node_type: Optional[Any] = Field(default=None)
    node_ids: Optional[Any] = Field(default=None)
    min_confidence: Optional[Any] = Field(default=None)
    silence_period: Optional[Any] = Field(default=None)
    enable_upgrade: Optional[Any] = Field(default=None)
    upgrade_minutes: Optional[Any] = Field(default=None)
    upgrade_to_level: Optional[Any] = Field(default=None)
    enabled: Optional[Any] = Field(default=None)
    description: Optional[Any] = Field(default=None)
