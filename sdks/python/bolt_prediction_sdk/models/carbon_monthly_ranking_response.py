"""
CarbonMonthlyRankingResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CarbonMonthlyRankingResponse(SDKBaseModel):
    """装置级月度碳排风险排行响应"""

    report_month: str = Field(description="报告月份 YYYY-MM")
    total_nodes: int = Field(description="分析节点总数")
    total_monthly_carbon_increment_kg: float = Field(description="月度碳排增量合计 (kgCO₂e)")
    total_monthly_leakage_volume_m3: float = Field(description="月度泄漏量合计 (m³)")
    risk_distribution: Dict[str, int] = Field(description="风险等级分布 {critical, high, medium, low}")
    ranked_items: List[CarbonRiskItemSchema] = Field(description="按优先级排序的碳排风险列表")
    generated_at: datetime = Field(description="生成时间")
