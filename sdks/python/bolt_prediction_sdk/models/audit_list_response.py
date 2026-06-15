"""
AuditListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AuditListResponse(SDKBaseModel):
    """审计记录列表响应"""

    total: int = Field()
    items: List[AuditRecordResponse] = Field()
