"""
CmmsConfigUpdate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsConfigUpdate(SDKBaseModel):
    """更新CMMS配置请求"""

    system_name: Optional[Any] = Field(default=None)
    system_type: Optional[Any] = Field(default=None)
    base_url: Optional[Any] = Field(default=None)
    auth_type: Optional[Any] = Field(default=None)
    auth_config: Optional[Any] = Field(default=None)
    work_order_sync: Optional[Any] = Field(default=None)
    work_order_webhook_url: Optional[Any] = Field(default=None)
    work_order_push_url: Optional[Any] = Field(default=None)
    status_mapping: Optional[Any] = Field(default=None)
    priority_mapping: Optional[Any] = Field(default=None)
    field_mapping: Optional[Any] = Field(default=None)
    enabled: Optional[Any] = Field(default=None)
    sync_direction: Optional[Any] = Field(default=None)
    sync_interval: Optional[Any] = Field(default=None)
    extra_info: Optional[Any] = Field(default=None)
