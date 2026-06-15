"""
APIAuditLogListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiAuditLogListResponse(SDKBaseModel):
    """APIAuditLogListResponse"""

    total: int = Field(description="总数")
    items: Optional[List[ApiAuditLogResponse]] = Field(description="审计日志列表", default=[])
