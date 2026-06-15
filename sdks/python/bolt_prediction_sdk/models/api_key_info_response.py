"""
APIKeyInfoResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiKeyInfoResponse(SDKBaseModel):
    """APIKeyInfoResponse"""

    key_id: str = Field(description="密钥ID")
    key_preview: str = Field(description="密钥预览（前8后4位）")
    name: str = Field(description="密钥名称")
    permissions: Optional[List[str]] = Field(description="权限列表", default=['read'])
    rate_limit: Optional[int] = Field(description="速率限制", default=1000)
    is_expired: Optional[bool] = Field(description="是否已过期", default=False)
    expires_at: Optional[Any] = Field(description="过期时间", default=None)
    created_at: Optional[Any] = Field(description="创建时间", default=None)
