"""
RiskAssessExplainResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RiskAssessExplainResponse(SDKBaseModel):
    """RiskAssessExplainResponse"""

    node_id: str = Field()
    node_type: str = Field()
    risk_score: float = Field()
    risk_level: str = Field()
    probability_distribution: RiskProbabilityDistributionSchema = Field()
    factor_contributions: List[FactorContributionSchema] = Field()
    base_value: float = Field(description="基准值（所有因子评分均值）")
    total_contribution: float = Field(description="总贡献度偏移")
    summary: str = Field(description="可读性总结")
