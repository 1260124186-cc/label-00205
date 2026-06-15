"""
LeakageParamsSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LeakageParamsSchema(SDKBaseModel):
    """泄漏率估算模型参数"""

    base_leakage_rate_m3_per_hour: Optional[float] = Field(description="基准泄漏率 (m³/h)", default=0.0)
    critical_leakage_threshold: Optional[float] = Field(description="临界泄漏压紧比阈值", default=0.05)
    preload_leakage_sensitivity: Optional[float] = Field(description="预紧力泄漏敏感度指数", default=2.5)
    seal_aging_factor_per_year: Optional[float] = Field(description="密封年老化系数", default=0.08)
    pressure_sensitivity: Optional[float] = Field(description="压力敏感度", default=1.2)
