"""
ESGReportSummarySchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EsgReportSummarySchema(SDKBaseModel):
    """ESG报表汇总数据"""

    reporting_period: str = Field(description="报告期")
    total_devices_analyzed: int = Field(description="分析装置总数")
    estimated_monthly_carbon_increment_kg: float = Field(description="月度碳排增量估算 (kgCO₂e)")
    estimated_monthly_carbon_increment_tons: float = Field(description="月度碳排增量估算 (吨CO₂e)")
    estimated_monthly_leakage_m3: float = Field(description="月度泄漏量估算 (m³)")
    average_carbon_per_device_kg: float = Field(description="单装置平均月度碳排增量 (kgCO₂e)")
    carbon_risk_severity: str = Field(description="碳排风险严重度 高/中/低")
    top5_contribution_ratio: float = Field(description="Top5装置碳排贡献占比")
    risk_distribution: Dict[str, int] = Field(description="风险分布")
