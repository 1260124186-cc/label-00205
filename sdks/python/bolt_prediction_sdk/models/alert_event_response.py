"""
AlertEventResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertEventResponse(SDKBaseModel):
    """告警事件响应"""

    id: int = Field()
    alert_no: str = Field()
    rule_id: Optional[Any] = Field(default=None)
    alert_level: int = Field()
    original_level: Optional[Any] = Field(default=None)
    node_type: Optional[Any] = Field(default=None)
    node_id: Optional[Any] = Field(default=None)
    title: Optional[Any] = Field(default=None)
    content: Optional[Any] = Field(default=None)
    confidence: Optional[Any] = Field(default=None)
    risk_score: Optional[Any] = Field(default=None)
    recommendations: Optional[Any] = Field(default=None)
    status: str = Field()
    handler_id: Optional[Any] = Field(default=None)
    handler_name: Optional[Any] = Field(default=None)
    handle_time: Optional[Any] = Field(default=None)
    handle_note: Optional[Any] = Field(default=None)
    is_upgraded: Optional[bool] = Field(default=False)
    upgrade_count: Optional[int] = Field(default=0)
    last_upgrade_time: Optional[Any] = Field(default=None)
    work_order_id: Optional[Any] = Field(default=None)
    source_prediction_id: Optional[Any] = Field(default=None)
    silence_until: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
    update_time: datetime = Field()
