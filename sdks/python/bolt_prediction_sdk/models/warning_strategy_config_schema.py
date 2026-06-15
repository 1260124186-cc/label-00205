"""
WarningStrategyConfigSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WarningStrategyConfigSchema(SDKBaseModel):
    """预警策略配置"""

    strategy_type: int = Field(description="策略类型: 1=应报尽报, 2=精准报警")
    strategy_1_confidence_threshold: Optional[float] = Field(description="策略1置信度阈值", default=0.7)
    strategy_1_false_positive_threshold: Optional[float] = Field(description="策略1误报率阈值", default=0.05)
    strategy_2_confidence_threshold: Optional[float] = Field(description="策略2置信度阈值", default=0.95)
    strategy_2_false_negative_threshold: Optional[float] = Field(description="策略2漏报率阈值", default=0.1)
