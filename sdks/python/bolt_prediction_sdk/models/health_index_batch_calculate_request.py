"""
HealthIndexBatchCalculateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthIndexBatchCalculateRequest(SDKBaseModel):
    """批量健康度计算请求"""

    nodes: List[Dict[str, Any]] = Field(description="节点列表 [{node_id, node_type, data}, ...]")
    working_condition: Optional[Any] = Field(default=None)
    save_to_db: Optional[bool] = Field(default=True)
