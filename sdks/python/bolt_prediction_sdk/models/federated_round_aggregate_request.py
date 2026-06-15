"""
FederatedRoundAggregateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedRoundAggregateRequest(SDKBaseModel):
    """聚合模型更新请求"""

    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: str = Field(description="节点ID")
