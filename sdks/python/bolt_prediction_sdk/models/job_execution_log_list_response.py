"""
JobExecutionLogListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class JobExecutionLogListResponse(SDKBaseModel):
    """任务执行日志列表响应"""

    total: int = Field(description="总记录数")
    items: List[JobExecutionLogSchema] = Field(description="日志列表")
