"""
FederatedGlobalModelResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedGlobalModelResponse(SDKBaseModel):
    """获取全局模型响应"""

    model_type: str = Field()
    node_id: str = Field()
    round_id: int = Field()
    version: Optional[Any] = Field(default=None)
    weights: Dict[str, Any] = Field()
    server_time: datetime = Field()
    enable_two_level_arch: Optional[bool] = Field(default=True)
    metrics: Optional[Any] = Field(default=None)
