"""
BatchReportResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BatchReportResponse(SDKBaseModel):
    """批量报告响应"""

    total: Optional[int] = Field(description="总数", default=0)
    success: Optional[int] = Field(description="成功数量", default=0)
    failed: Optional[int] = Field(description="失败数量", default=0)
    results: Optional[List[PeriodicReportResponse]] = Field(description="成功的报告列表", default=None)
    errors: Optional[Dict[str, str]] = Field(description="失败的节点及错误信息", default=None)
