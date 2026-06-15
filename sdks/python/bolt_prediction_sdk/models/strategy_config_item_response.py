"""
StrategyConfigItemResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StrategyConfigItemResponse(SDKBaseModel):
    """单条策略配置响应"""

    id: int = Field()
    scope: Optional[str] = Field(default='global')
    node_type: Optional[Any] = Field(default=None)
    node_id: Optional[Any] = Field(default=None)
    strategy_type: int = Field()
    confidence_threshold: float = Field()
    false_positive_threshold: Optional[Any] = Field(default=None)
    false_negative_threshold: Optional[Any] = Field(default=None)
    version: Optional[int] = Field(default=1)
    is_active: Optional[bool] = Field(default=True)
    description: Optional[Any] = Field(default=None)
    operator_id: Optional[Any] = Field(default=None)
    operator_name: Optional[Any] = Field(default=None)
    create_time: Optional[Any] = Field(default=None)
    update_time: Optional[Any] = Field(default=None)
