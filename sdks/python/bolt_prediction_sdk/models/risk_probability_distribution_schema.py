"""
RiskProbabilityDistributionSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RiskProbabilityDistributionSchema(SDKBaseModel):
    """RiskProbabilityDistributionSchema"""

    p_high: float = Field(description="高风险概率")
    p_medium: float = Field(description="中风险概率")
    p_low: float = Field(description="低风险概率")
