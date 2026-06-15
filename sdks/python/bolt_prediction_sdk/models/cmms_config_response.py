"""
CmmsConfigResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsConfigResponse(SDKBaseModel):
    """CMMS配置响应"""

    id: int = Field()
    system_name: str = Field()
    system_type: Optional[Any] = Field(default=None)
    base_url: Optional[Any] = Field(default=None)
    auth_type: Optional[Any] = Field(default=None)
    work_order_sync: Optional[Any] = Field(default=None)
    work_order_webhook_url: Optional[Any] = Field(default=None)
    work_order_push_url: Optional[Any] = Field(default=None)
    status_mapping: Optional[Any] = Field(default=None)
    priority_mapping: Optional[Any] = Field(default=None)
    field_mapping: Optional[Any] = Field(default=None)
    enabled: Optional[Any] = Field(default=None)
    sync_direction: Optional[Any] = Field(default=None)
    last_sync_time: Optional[Any] = Field(default=None)
    sync_interval: Optional[Any] = Field(default=None)
    tenant_id: Optional[Any] = Field(default=None)
    extra_info: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
    update_time: datetime = Field()
