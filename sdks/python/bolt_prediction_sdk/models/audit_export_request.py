"""
AuditExportRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AuditExportRequest(SDKBaseModel):
    """审计导出请求"""

    start_time: datetime = Field(description="起始时间")
    end_time: datetime = Field(description="结束时间")
    node_type: Optional[Any] = Field(description="节点类型过滤 bolt/flange", default=None)
    node_id: Optional[Any] = Field(description="节点ID过滤", default=None)
    format: Optional[str] = Field(description="导出格式 csv/pdf", default='csv')
