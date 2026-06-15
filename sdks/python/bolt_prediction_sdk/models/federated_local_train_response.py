"""
FederatedLocalTrainResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedLocalTrainResponse(SDKBaseModel):
    """本地训练响应"""

    client_id: str = Field()
    model_type: str = Field()
    node_id: str = Field()
    status: str = Field()
    message: str = Field()
    num_samples: int = Field()
    training_time: float = Field()
    metrics: Dict[str, float] = Field()
