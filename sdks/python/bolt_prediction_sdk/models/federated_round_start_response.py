"""
FederatedRoundStartResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedRoundStartResponse(SDKBaseModel):
    """开始联邦学习轮次响应"""

    round_id: int = Field()
    model_type: str = Field()
    node_id: str = Field()
    status: str = Field()
    expected_clients: List[str] = Field()
    started_at: datetime = Field()
