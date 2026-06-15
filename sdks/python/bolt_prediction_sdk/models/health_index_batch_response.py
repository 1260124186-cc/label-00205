"""
HealthIndexBatchResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthIndexBatchResponse(SDKBaseModel):
    """批量健康度计算响应"""

    total_count: int = Field()
    success_count: int = Field()
    failed_count: int = Field()
    results: List[Dict[str, Any]] = Field()
    calculate_time: datetime = Field()
