"""
FederatedRoundAggregateResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedRoundAggregateResponse(SDKBaseModel):
    """聚合模型更新响应"""

    round_id: int = Field()
    model_type: str = Field()
    node_id: str = Field()
    status: str = Field()
    message: str = Field()
    num_clients_aggregated: int = Field()
    version: Optional[Any] = Field(default=None)
    metrics: Optional[Any] = Field(default=None)
    aggregated_at: datetime = Field()
