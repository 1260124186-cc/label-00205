"""
DisposalRecordListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DisposalRecordListResponse(SDKBaseModel):
    """处置记录列表响应"""

    total: int = Field()
    items: List[DisposalRecordResponse] = Field()
