"""
ESGTrendAnalysisSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EsgTrendAnalysisSchema(SDKBaseModel):
    """ESG趋势分析"""

    overall_trend: str = Field(description="整体趋势 deteriorating/stable/improving")
    improving_count: int = Field(description="改善装置数")
    stable_count: int = Field(description="稳定装置数")
    declining_count: int = Field(description="劣化装置数")
    key_observation: str = Field(description="关键观察结论")
