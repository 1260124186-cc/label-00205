"""
StrategyRollbackRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StrategyRollbackRequest(SDKBaseModel):
    """策略回滚请求"""

    target_version: int = Field(description="回滚目标版本号")
    scope: Optional[str] = Field(description="作用域", default='global')
    node_type: Optional[Any] = Field(description="节点类型", default=None)
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
