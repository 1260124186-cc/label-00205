"""
PeriodicReportResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class PeriodicReportResponse(SDKBaseModel):
    """周期报告响应（周报/月报）"""

    report_type: str = Field(description="报告类型：weekly/monthly")
    node_id: str = Field(description="节点ID")
    node_type: str = Field(description="节点类型")
    period_start: datetime = Field(description="统计周期开始时间")
    period_end: datetime = Field(description="统计周期结束时间")
    diagnosis_summary: str = Field(description="诊断摘要")
    recommended_actions: List[str] = Field(description="推荐处置措施")
    urgency_level: str = Field(description="整体紧急程度：low/medium/high/critical")
    statistics: ReportStatisticsSchema = Field(description="统计数据")
    generated_at: datetime = Field(description="生成时间")
    model: str = Field(description="使用的模型")
    is_fallback: Optional[bool] = Field(description="是否使用降级模板", default=False)
