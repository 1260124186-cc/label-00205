"""
CmmsConfigCreate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CmmsConfigCreate(SDKBaseModel):
    """创建CMMS配置请求"""

    system_name: str = Field(description="系统名称")
    system_type: Optional[Any] = Field(description="系统类型 maximo/sap_eam/infor/eam/other", default=None)
    base_url: Optional[Any] = Field(description="系统基础URL", default=None)
    auth_type: Optional[Any] = Field(description="认证类型 basic/api_key/oauth2/token", default=None)
    auth_config: Optional[Any] = Field(description="认证配置", default=None)
    work_order_sync: Optional[Any] = Field(description="是否同步工单", default=False)
    work_order_webhook_url: Optional[Any] = Field(description="工单Webhook URL", default=None)
    work_order_push_url: Optional[Any] = Field(description="工单推送URL", default=None)
    status_mapping: Optional[Any] = Field(description="状态映射", default=None)
    priority_mapping: Optional[Any] = Field(description="优先级映射", default=None)
    field_mapping: Optional[Any] = Field(description="字段映射", default=None)
    enabled: Optional[Any] = Field(description="是否启用", default=True)
    sync_direction: Optional[Any] = Field(description="同步方向 push/pull/bidirectional", default='push')
    sync_interval: Optional[Any] = Field(description="同步间隔 分钟", default=60)
    tenant_id: Optional[Any] = Field(description="租户ID", default=None)
    extra_info: Optional[Any] = Field(description="扩展信息", default=None)
