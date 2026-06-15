"""
StrategyConfigUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StrategyConfigUpdateRequest(SDKBaseModel):
    """预警策略动态配置更新请求"""

    scope: Optional[str] = Field(description="作用域: global/bolt/flange/production_line", default='global')
    node_type: Optional[Any] = Field(description="节点类型 bolt/flange/production_line，scope非global时必填", default=None)
    node_id: Optional[Any] = Field(description="节点ID，scope非global时必填", default=None)
    strategy_type: int = Field(description="策略类型: 1=应报尽报, 2=精准报警")
    confidence_threshold: Optional[Any] = Field(description="置信度阈值", default=None)
    false_positive_threshold: Optional[Any] = Field(description="误报容忍度", default=None)
    false_negative_threshold: Optional[Any] = Field(description="漏报容忍度", default=None)
    description: Optional[Any] = Field(description="变更说明", default=None)
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
