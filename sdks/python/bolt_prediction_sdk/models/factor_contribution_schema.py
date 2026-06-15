"""
FactorContributionSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FactorContributionSchema(SDKBaseModel):
    """FactorContributionSchema"""

    name: str = Field(description="因子名称")
    display_name: str = Field(description="因子显示名")
    raw_score: float = Field(description="原始评分")
    weight: float = Field(description="权重")
    weighted_score: float = Field(description="加权评分")
    contribution_ratio: float = Field(description="贡献度占比")
    direction: str = Field(description="方向: risk_up/risk_down")
