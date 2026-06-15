"""
APIKeyRotateResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiKeyRotateResponse(SDKBaseModel):
    """APIKeyRotateResponse"""

    old_key_id: str = Field(description="旧密钥ID")
    new_key: str = Field(description="新密钥（仅轮换时返回完整密钥）")
    new_key_id: str = Field(description="新密钥ID")
    old_key_grace_expires: datetime = Field(description="旧密钥宽限期截止时间")
    permissions: Optional[List[str]] = Field(description="权限列表（继承旧密钥）", default=['read'])
    rate_limit: Optional[int] = Field(description="速率限制", default=1000)
