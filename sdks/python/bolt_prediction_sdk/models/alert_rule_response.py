"""
AlertRuleResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertRuleResponse(SDKBaseModel):
    """告警规则响应"""

    rule_name: str = Field(description="规则名称")
    alert_level: int = Field(description="告警级别 1-4")
    node_type: Optional[str] = Field(description="节点类型 bolt/flange/all", default='all')
    node_ids: Optional[Any] = Field(description="节点ID列表，空表示全部", default=None)
    min_confidence: Optional[float] = Field(description="最低置信度", default=0.0)
    silence_period: Optional[int] = Field(description="静默期（分钟）", default=30)
    enable_upgrade: Optional[bool] = Field(description="是否启用自动升级", default=True)
    upgrade_minutes: Optional[int] = Field(description="未处理升级时间（分钟）", default=30)
    upgrade_to_level: Optional[Any] = Field(description="升级到的级别", default=None)
    enabled: Optional[bool] = Field(description="是否启用", default=True)
    description: Optional[Any] = Field(description="规则描述", default=None)
    id: int = Field()
    create_time: datetime = Field()
    update_time: datetime = Field()
