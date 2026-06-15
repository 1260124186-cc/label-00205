"""
FaultPatternSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FaultPatternSchema(SDKBaseModel):
    """故障模式特征"""

    trend_slope: float = Field(description="趋势斜率")
    volatility: float = Field(description="波动率")
    sudden_changes: int = Field(description="骤降/突变点数量")
    min_value: float = Field(description="最小值")
    max_value: float = Field(description="最大值")
    mean_value: float = Field(description="平均值")
