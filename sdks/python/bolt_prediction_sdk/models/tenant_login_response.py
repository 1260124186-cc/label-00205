"""
TenantLoginResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TenantLoginResponse(SDKBaseModel):
    """TenantLoginResponse"""

    token: str = Field()
    tenant_id: int = Field()
    user_id: int = Field()
    username: str = Field()
    role: str = Field()
    expires_at: datetime = Field()
