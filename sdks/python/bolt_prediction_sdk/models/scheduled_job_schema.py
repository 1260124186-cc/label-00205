"""
ScheduledJobSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ScheduledJobSchema(SDKBaseModel):
    """调度任务信息"""

    id: str = Field(description="任务ID")
    name: str = Field(description="任务名称")
    enabled: bool = Field(description="是否启用")
    cron: str = Field(description="Cron表达式")
    next_run: Optional[Any] = Field(description="下次执行时间", default=None)
    description: Optional[Any] = Field(description="任务描述", default=None)
