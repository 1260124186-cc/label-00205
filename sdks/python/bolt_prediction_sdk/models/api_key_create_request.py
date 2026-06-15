"""
APIKeyCreateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiKeyCreateRequest(SDKBaseModel):
    """APIKeyCreateRequest"""

    name: str = Field(description="密钥名称")
    permissions: Optional[List[str]] = Field(description="权限列表: read/write/admin", default=['read'])
    rate_limit: Optional[int] = Field(description="每小时请求限制", default=1000)
    expires_hours: Optional[Any] = Field(description="有效期（小时），None表示永不过期", default=None)
