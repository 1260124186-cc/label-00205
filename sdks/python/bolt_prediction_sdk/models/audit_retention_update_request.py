"""
AuditRetentionUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AuditRetentionUpdateRequest(SDKBaseModel):
    """更新审计记录保留年限请求"""

    retention_years: int = Field(description="保留年限")
