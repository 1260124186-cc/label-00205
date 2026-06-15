"""
AlertHandleRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertHandleRequest(SDKBaseModel):
    """处理告警请求"""

    action: str = Field(description="处理动作: acknowledge/resolve/ignore")
    handler_id: Optional[Any] = Field(description="处理人ID", default=None)
    handler_name: Optional[Any] = Field(description="处理人姓名", default=None)
    handle_note: Optional[Any] = Field(description="处理备注", default=None)
    silence_minutes: Optional[Any] = Field(description="忽略时的静默期（分钟）", default=None)
