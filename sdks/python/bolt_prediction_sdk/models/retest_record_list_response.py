"""
RetestRecordListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RetestRecordListResponse(SDKBaseModel):
    """复测记录列表响应"""

    total: int = Field()
    items: List[RetestRecordResponse] = Field()
