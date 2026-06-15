"""
RateLimitStatusResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RateLimitStatusResponse(SDKBaseModel):
    """RateLimitStatusResponse"""

    key_id: str = Field(description="密钥ID")
    limit: int = Field(description="速率限制（请求/小时）")
    remaining: int = Field(description="剩余请求次数")
    used: int = Field(description="已使用请求次数")
