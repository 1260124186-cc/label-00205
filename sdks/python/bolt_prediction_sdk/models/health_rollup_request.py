"""
HealthRollupRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthRollupRequest(SDKBaseModel):
    """健康度汇总报表请求"""

    line_id: str = Field(description="产线/装置ID")
    line_name: Optional[Any] = Field(default=None)
    line_type: Optional[str] = Field(description="产线类型", default='production_line')
    report_date: Optional[Any] = Field(description="报告日期，默认今日", default=None)
    include_details: Optional[bool] = Field(description="是否包含详细数据", default=True)
