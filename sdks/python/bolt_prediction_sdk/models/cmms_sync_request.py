"""
CmmsSyncRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsSyncRequest(SDKBaseModel):
    """CMMS同步请求"""

    config_id: int = Field(description="CMMS配置ID")
    sync_type: Optional[str] = Field(description="同步类型", default='work_order_create')
    work_order_id: Optional[Any] = Field(description="工单ID", default=None)
