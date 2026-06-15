"""
MttrTrendPoint 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class MttrTrendPoint(SDKBaseModel):
    """MTTR趋势点"""

    date: str = Field()
    mttr_hours: Optional[Any] = Field(default=None)
    work_order_count: Optional[int] = Field(default=0)
