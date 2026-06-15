"""
ESGReportExportRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EsgReportExportRequest(SDKBaseModel):
    """ESG报表片段导出请求"""

    nodes: List[Dict[str, Any]] = Field(description="节点数据列表，格式同 CarbonMonthlyRankingRequest")
    format: Optional[str] = Field(description="导出格式 json/csv/html", default='json')
    include_methodology: Optional[bool] = Field(description="是否包含方法学说明", default=True)
    top_n: Optional[Any] = Field(description="返回前N名高风险装置", default=10)
