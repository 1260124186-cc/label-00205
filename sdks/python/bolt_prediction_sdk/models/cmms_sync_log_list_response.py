"""
CmmsSyncLogListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsSyncLogListResponse(SDKBaseModel):
    """CMMS同步日志列表响应"""

    total: int = Field()
    items: List[CmmsSyncLogResponse] = Field()
