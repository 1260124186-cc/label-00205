"""
FederatedLocalTrainRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedLocalTrainRequest(SDKBaseModel):
    """本地训练请求"""

    client_id: str = Field(description="客户端ID")
    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: str = Field(description="节点ID")
    local_epochs: Optional[Any] = Field(description="本地训练轮数", default=None)
    fine_tune: Optional[bool] = Field(description="是否执行本地微调（第二层）", default=False)
    train_data: Optional[Any] = Field(description="训练数据（可选，自动加载）", default=None)
    train_labels: Optional[Any] = Field(description="训练标签（可选，自动加载）", default=None)
