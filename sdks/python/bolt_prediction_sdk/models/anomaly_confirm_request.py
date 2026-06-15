"""
AnomalyConfirmRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyConfirmRequest(SDKBaseModel):
    """确认异常请求

将异常标记为真实异常。"""

    anomaly_id: int = Field(description="异常记录ID")
    confirmed_by: Optional[Any] = Field(description="确认人ID", default=None)
    confirm_note: Optional[Any] = Field(description="确认备注", default=None)
