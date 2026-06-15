"""
FederatedClientStatusResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedClientStatusResponse(SDKBaseModel):
    """客户端状态响应"""

    client_id: str = Field()
    factory_id: str = Field()
    model_type: Any = Field()
    node_id: Any = Field()
    current_round: int = Field()
    has_global_model: bool = Field()
    has_local_model: bool = Field()
    training_count: int = Field()
    privacy_mechanism: str = Field()
    update_type: str = Field()
    two_level_arch_enabled: bool = Field()
    last_update_time: Any = Field()
