"""
TenantLoginRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantLoginRequest(SDKBaseModel):
    """TenantLoginRequest"""

    tenant_code: str = Field(description="租户编码")
    username: str = Field(description="用户名")
    password: str = Field(description="密码")
