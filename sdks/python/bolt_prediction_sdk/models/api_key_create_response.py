"""
APIKeyCreateResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiKeyCreateResponse(SDKBaseModel):
    """APIKeyCreateResponse"""

    key: str = Field(description="生成的API密钥（仅创建时返回完整密钥）")
    key_id: str = Field(description="密钥ID")
    name: str = Field(description="密钥名称")
    permissions: Optional[List[str]] = Field(description="权限列表", default=['read'])
    rate_limit: Optional[int] = Field(description="速率限制", default=1000)
    expires_at: Optional[Any] = Field(description="过期时间", default=None)
    created_at: str = Field(description="创建时间")
