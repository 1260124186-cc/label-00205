"""
SchedulerTriggerResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class SchedulerTriggerResponse(SDKBaseModel):
    """调度任务触发响应"""

    job_name: str = Field(description="任务名称")
    status: str = Field(description="状态: triggered/skipped")
    message: str = Field(description="消息")
    log_id: Optional[Any] = Field(description="任务执行日志ID", default=None)
    is_leader: Optional[Any] = Field(description="是否为Leader节点", default=None)
