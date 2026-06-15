"""
DisposalRecordResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DisposalRecordResponse(SDKBaseModel):
    """处置记录响应"""

    id: int = Field()
    work_order_id: int = Field()
    disposal_type: Optional[Any] = Field(default=None)
    disposal_content: Optional[Any] = Field(default=None)
    disposal_time: Optional[Any] = Field(default=None)
    operator_id: Optional[Any] = Field(default=None)
    operator_name: Optional[Any] = Field(default=None)
    before_value: Optional[Any] = Field(default=None)
    after_value: Optional[Any] = Field(default=None)
    materials_used: Optional[Any] = Field(default=None)
    photos: Optional[Any] = Field(default=None)
    notes: Optional[Any] = Field(default=None)
    extra_info: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
