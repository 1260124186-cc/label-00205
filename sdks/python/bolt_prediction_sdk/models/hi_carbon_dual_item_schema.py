"""
HICarbonDualItemSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HiCarbonDualItemSchema(SDKBaseModel):
    """HI与碳排并列展示单项"""

    node_id: str = Field(description="节点ID")
    node_type: str = Field(description="节点类型")
    node_name: str = Field(description="节点名称")
    hi_score: float = Field(description="健康度指数 0-100")
    hi_level: str = Field(description="HI等级")
    hi_trend: str = Field(description="HI趋势 improving/stable/declining")
    degradation_rate_per_month: float = Field(description="预紧力月劣化速率")
    estimated_leakage_rate_m3_hour: float = Field(description="估算泄漏率 (m³/h)")
    monthly_carbon_increment_kg: float = Field(description="月度碳排增量 (kgCO₂e)")
    carbon_risk_level: str = Field(description="碳排风险等级 low/medium/high/critical")
    carbon_trend: str = Field(description="碳排趋势 increasing/stable/decreasing")
