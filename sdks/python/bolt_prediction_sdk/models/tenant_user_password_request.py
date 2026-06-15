"""
TenantUserPasswordRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantUserPasswordRequest(SDKBaseModel):
    """TenantUserPasswordRequest"""

    new_password: str = Field(description="新密码")
