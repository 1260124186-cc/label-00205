"""
FederatedServerStatusResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedServerStatusResponse(SDKBaseModel):
    """联邦学习服务器状态响应"""

    registered_clients: int = Field()
    active_clients: int = Field()
    total_rounds: int = Field()
    completed_rounds: int = Field()
    failed_rounds: int = Field()
    aggregation_strategy: str = Field()
    managed_models: List[str] = Field()
    current_round: Optional[Any] = Field(default=None)
