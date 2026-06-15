"""
StrategyNodeOverrideDeleteRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StrategyNodeOverrideDeleteRequest(SDKBaseModel):
    """删除节点级策略覆盖请求"""

    node_type: str = Field(description="节点类型 bolt/flange/production_line")
    node_id: str = Field(description="节点ID")
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
