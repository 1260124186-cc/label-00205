"""
StrategyAuditLogResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StrategyAuditLogResponse(SDKBaseModel):
    """策略审计日志响应"""

    id: int = Field()
    config_id: int = Field()
    scope: str = Field()
    node_type: Optional[Any] = Field(default=None)
    node_id: Optional[Any] = Field(default=None)
    action: str = Field()
    old_value: Optional[Any] = Field(default=None)
    new_value: Optional[Any] = Field(default=None)
    version_before: Optional[Any] = Field(default=None)
    version_after: Optional[Any] = Field(default=None)
    change_summary: Optional[Any] = Field(default=None)
    operator_id: Optional[Any] = Field(default=None)
    operator_name: Optional[Any] = Field(default=None)
    create_time: Optional[Any] = Field(default=None)
