"""
WorkOrderUpdate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkOrderUpdate(SDKBaseModel):
    """更新工单请求"""

    title: Optional[Any] = Field(default=None)
    description: Optional[Any] = Field(default=None)
    priority: Optional[Any] = Field(default=None)
    status: Optional[Any] = Field(default=None)
    assignee_id: Optional[Any] = Field(default=None)
    assignee_name: Optional[Any] = Field(default=None)
    due_time: Optional[Any] = Field(default=None)
    recommendations: Optional[Any] = Field(default=None)
    extra_info: Optional[Any] = Field(default=None)
