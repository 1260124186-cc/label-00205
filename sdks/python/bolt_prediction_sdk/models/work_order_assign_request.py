"""
WorkOrderAssignRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkOrderAssignRequest(SDKBaseModel):
    """指派工单请求"""

    assignee_id: str = Field(description="处理人ID")
    assignee_name: str = Field(description="处理人姓名")
    assigner_id: Optional[Any] = Field(description="指派人ID", default=None)
    assigner_name: Optional[Any] = Field(description="指派人姓名", default=None)
