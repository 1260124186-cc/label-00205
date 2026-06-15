"""
AnomalyWarningImpactResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyWarningImpactResponse(SDKBaseModel):
    """异常对预警等级影响分析响应"""

    sensor_id: str = Field()
    should_upgrade: Optional[bool] = Field(description="是否需要提升预警等级", default=False)
    original_level: int = Field(description="原始预警等级")
    upgraded_level: int = Field(description="提升后的预警等级")
    anomaly_count: Optional[int] = Field(description="时间窗口内的异常数", default=0)
    threshold: Optional[int] = Field(description="异常数阈值", default=0)
    window_minutes: Optional[int] = Field(description="时间窗口（分钟）", default=0)
