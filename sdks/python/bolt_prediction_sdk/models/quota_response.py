"""
QuotaResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class QuotaResponse(SDKBaseModel):
    """QuotaResponse"""

    tenant_id: int = Field()
    max_models: int = Field()
    max_api_calls_per_day: int = Field()
    max_storage_mb: int = Field()
    max_users: int = Field()
    max_org_nodes: int = Field()
    current_model_count: int = Field()
    current_api_calls_today: int = Field()
    current_storage_mb: float = Field()
    current_user_count: int = Field()
    current_org_node_count: int = Field()
    create_time: datetime = Field()
    update_time: datetime = Field()
