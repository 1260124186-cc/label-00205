"""
RiskAssessmentResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RiskAssessmentResponse(SDKBaseModel):
    """风险评估响应"""

    node_id: str = Field()
    node_type: str = Field()
    risk_score: float = Field()
    risk_level: str = Field()
    factors: List[str] = Field()
    diagnosis: str = Field()
    recommendations: List[str] = Field()
    confidence: float = Field()
    probability_distribution: Optional[Any] = Field(description="风险概率分布 P(高/中/低)", default=None)
    factor_contributions: Optional[Any] = Field(description="各因子贡献度", default=None)
