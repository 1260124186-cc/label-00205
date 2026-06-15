"""
ESGReportFragmentResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EsgReportFragmentResponse(SDKBaseModel):
    """ESG报表片段响应"""

    report_period: str = Field(description="报告期")
    generated_at: datetime = Field(description="生成时间")
    summary: EsgReportSummarySchema = Field(description="汇总数据")
    top_risk_items: List[CarbonRiskItemSchema] = Field(description="高风险装置列表")
    trend_analysis: EsgTrendAnalysisSchema = Field(description="趋势分析")
    recommendations: List[str] = Field(description="建议措施")
    methodology_note: Optional[Any] = Field(description="方法学说明", default=None)
    csv_content: Optional[Any] = Field(description="CSV格式内容（format=csv时返回）", default=None)
