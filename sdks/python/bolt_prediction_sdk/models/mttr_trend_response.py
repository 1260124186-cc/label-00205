"""
MttrTrendResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class MttrTrendResponse(SDKBaseModel):
    """MTTR趋势响应"""

    trend: List[MttrTrendPoint] = Field()
    overall_mttr_hours: Optional[Any] = Field(default=None)
