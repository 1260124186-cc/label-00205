"""
AnomalyBatchConfirmRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyBatchConfirmRequest(SDKBaseModel):
    """批量确认异常请求"""

    anomaly_ids: List[int] = Field(description="异常记录ID列表")
    confirmed_by: Optional[Any] = Field(description="确认人ID", default=None)
    confirm_note: Optional[Any] = Field(description="确认备注", default=None)
