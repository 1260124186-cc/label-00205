"""
AnomalyListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyListResponse(SDKBaseModel):
    """异常列表响应"""

    total: int = Field(description="总记录数")
    items: List[AnomalyDataResponse] = Field(description="异常数据列表")
