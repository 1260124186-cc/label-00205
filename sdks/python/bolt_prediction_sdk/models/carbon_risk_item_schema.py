"""
CarbonRiskItemSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CarbonRiskItemSchema(SDKBaseModel):
    """碳排风险排行单项"""

    rank: Optional[Any] = Field(description="排名", default=None)
    node_id: str = Field(description="节点ID")
    node_type: str = Field(description="节点类型 bolt/flange/device")
    node_name: str = Field(description="节点名称")
    hi_score: float = Field(description="健康度指数 HI 0-100")
    hi_level: str = Field(description="HI等级 excellent/good/fair/poor/critical")
    carbon_risk_score: float = Field(description="碳排风险评分 0-100")
    carbon_risk_level: str = Field(description="碳排风险等级 low/medium/high/critical")
    monthly_leakage_volume_m3: float = Field(description="月度估算泄漏量 (m³)")
    monthly_carbon_increment_kg: float = Field(description="月度碳排增量 (kgCO₂e)")
    priority_score: float = Field(description="综合优先级评分")
    trend: str = Field(description="趋势 stable/gradual_decline/accelerating_decline/recovering")
    recommendations: Optional[List[str]] = Field(description="推荐措施", default=None)
