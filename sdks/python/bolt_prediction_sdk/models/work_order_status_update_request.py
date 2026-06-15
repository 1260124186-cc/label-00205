"""
WorkOrderStatusUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkOrderStatusUpdateRequest(SDKBaseModel):
    """更新工单状态请求"""

    status: str = Field(description="新状态")
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
    note: Optional[Any] = Field(description="备注", default=None)
