"""
MultivariateChannelSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class MultivariateChannelSchema(SDKBaseModel):
    """单通道时序元数据

Attributes:
    name: 通道名称（如 preload / temperature / humidity / vibration / torque / pressure）
    unit: 物理单位（可选）
    description: 中文描述（可选）"""

    name: str = Field(description="通道名称: preload/temperature/humidity/vibration/torque/pressure 或自定义")
    unit: Optional[Any] = Field(description="物理单位, 如 kN / °C / % / g / N·m / MPa", default=None)
    description: Optional[Any] = Field(description="通道中文描述", default=None)
