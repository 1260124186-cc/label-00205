"""
HICarbonDualViewResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HiCarbonDualViewResponse(SDKBaseModel):
    """HI rollup 与碳排并列展示响应"""

    report_month: str = Field(description="报告月份 YYYY-MM")
    total_nodes: int = Field(description="节点总数")
    items: List[HiCarbonDualItemSchema] = Field(description="HI与碳排并列数据列表")
    generated_at: datetime = Field(description="生成时间")
