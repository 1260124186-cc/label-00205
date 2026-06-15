"""
FederatedUpdateUploadRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedUpdateUploadRequest(SDKBaseModel):
    """上传模型更新请求"""

    client_id: str = Field(description="客户端ID")
    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: str = Field(description="节点ID")
    round_id: int = Field(description="联邦学习轮次ID")
    weights: Dict[str, Any] = Field(description="模型更新（权重或差异）")
    num_samples: int = Field(description="训练样本数量")
    metrics: Optional[Any] = Field(description="训练指标", default=None)
    encrypted: Optional[bool] = Field(description="是否加密", default=False)
    encrypted_update: Optional[Any] = Field(description="加密后的更新（Base64编码）", default=None)
    update_type: Optional[str] = Field(description="更新类型: weights/gradients/difference", default='difference')
