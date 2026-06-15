"""
AuditCleanupResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AuditCleanupResponse(SDKBaseModel):
    """清理过期审计记录响应"""

    cleaned_count: int = Field()
    message: str = Field()
