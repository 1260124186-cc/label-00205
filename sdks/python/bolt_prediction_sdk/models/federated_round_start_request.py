"""
FederatedRoundStartRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedRoundStartRequest(SDKBaseModel):
    """开始联邦学习轮次请求"""

    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: str = Field(description="节点ID")
    expected_clients: Optional[Any] = Field(description="期望参与的客户端列表", default=None)
