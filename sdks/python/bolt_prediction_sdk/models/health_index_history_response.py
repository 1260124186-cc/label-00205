"""
HealthIndexHistoryResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthIndexHistoryResponse(SDKBaseModel):
    """健康度历史查询响应"""

    node_id: str = Field()
    node_type: str = Field()
    total: int = Field()
    history: List[Dict[str, Any]] = Field()
    trend_analysis: Optional[Any] = Field(default=None)
