"""
QualityDimensionScoreSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class QualityDimensionScoreSchema(SDKBaseModel):
    """维度评分"""

    dimension: str = Field()
    score: float = Field()
    weight: float = Field()
    contributing_rules: List[str] = Field()
