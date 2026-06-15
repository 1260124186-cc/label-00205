"""
TenantAPIKeyCreateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantApiKeyCreateRequest(SDKBaseModel):
    """TenantAPIKeyCreateRequest"""

    key_name: Optional[Any] = Field(description="密钥名称", default=None)
    permissions: Optional[Any] = Field(description="权限列表", default=None)
    rate_limit: Optional[int] = Field(description="速率限制 每分钟", default=1000)
    user_id: Optional[Any] = Field(description="关联用户ID", default=None)
    expires_at: Optional[Any] = Field(description="过期时间", default=None)
