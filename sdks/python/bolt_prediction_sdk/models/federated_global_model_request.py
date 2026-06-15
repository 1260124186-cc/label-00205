"""
FederatedGlobalModelRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedGlobalModelRequest(SDKBaseModel):
    """获取全局模型请求"""

    client_id: str = Field(description="客户端ID")
    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: str = Field(description="节点ID")
