"""
SchedulerJobUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class SchedulerJobUpdateRequest(SDKBaseModel):
    """调度任务更新请求"""

    enabled: Optional[Any] = Field(description="是否启用", default=None)
    cron: Optional[Any] = Field(description="Cron表达式", default=None)
