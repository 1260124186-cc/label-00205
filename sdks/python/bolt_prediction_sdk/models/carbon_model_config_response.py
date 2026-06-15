"""
CarbonModelConfigResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CarbonModelConfigResponse(SDKBaseModel):
    """碳排模型系数配置响应"""

    degradation: DegradationParamsSchema = Field()
    leakage: LeakageParamsSchema = Field()
    energy_carbon: EnergyCarbonParamsSchema = Field(description="能耗与碳排模型参数")
