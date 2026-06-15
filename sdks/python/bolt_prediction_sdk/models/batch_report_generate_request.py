"""
BatchReportGenerateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BatchReportGenerateRequest(SDKBaseModel):
    """批量生成报告请求"""

    node_type: str = Field(description="节点类型：bolt/flange")
    node_ids: List[str] = Field(description="节点ID列表")
    report_type: Optional[str] = Field(description="报告类型：weekly/monthly", default='weekly')
