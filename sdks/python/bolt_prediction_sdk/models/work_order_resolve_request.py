"""
WorkOrderResolveRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkOrderResolveRequest(SDKBaseModel):
    """解决工单请求"""

    resolve_note: str = Field(description="解决备注")
    resolver_id: Optional[Any] = Field(description="解决人ID", default=None)
    resolver_name: Optional[Any] = Field(description="解决人姓名", default=None)
