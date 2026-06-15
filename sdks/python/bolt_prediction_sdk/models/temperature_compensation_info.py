"""
TemperatureCompensationInfo 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TemperatureCompensationInfo(SDKBaseModel):
    """温度耦合补偿信息

Attributes:
    applied: 是否执行了温度补偿
    temperature_coefficient: 估计的温度系数 α (kN/°C)
    correlation: 温度与预紧力的皮尔逊相关系数
    original_mean_preload: 补偿前平均预紧力
    compensated_mean_preload: 补偿后平均预紧力
    delta_t_mean: 平均温度波动"""

    applied: Optional[bool] = Field(default=False)
    temperature_coefficient: Optional[Any] = Field(default=None)
    correlation: Optional[Any] = Field(default=None)
    original_mean_preload: Optional[Any] = Field(default=None)
    compensated_mean_preload: Optional[Any] = Field(default=None)
    delta_t_mean: Optional[Any] = Field(default=None)
