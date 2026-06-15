"""
DegradationParamsSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DegradationParamsSchema(SDKBaseModel):
    """预紧力劣化模型参数"""

    nominal_preload: Optional[float] = Field(description="额定预紧力 (kN)", default=600.0)
    min_effective_preload_ratio: Optional[float] = Field(description="最小有效压紧比阈值", default=0.6)
    relaxation_rate_per_month: Optional[float] = Field(description="自然松弛月速率", default=0.015)
    temperature_acceleration_factor: Optional[float] = Field(description="高温加速因子 (每°C高于40)", default=0.002)
    vibration_acceleration_factor: Optional[float] = Field(description="振动加速因子", default=0.003)
    cycle_acceleration_factor: Optional[float] = Field(description="压力循环加速因子", default=0.0001)
