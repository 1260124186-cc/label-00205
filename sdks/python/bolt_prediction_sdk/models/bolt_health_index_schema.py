"""
BoltHealthIndexSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltHealthIndexSchema(SDKBaseModel):
    """螺栓健康度指数"""

    hi_score: float = Field(description="综合健康度指数 0-100")
    hi_level: str = Field(description="健康等级 excellent/good/fair/poor/critical")
    factors: List[HealthIndexFactorSchema] = Field(description="各因子得分详情")
    preload_stability_score: float = Field(description="预紧力稳定性得分")
    alert_frequency_score: float = Field(description="预警频率得分")
    fault_history_score: float = Field(description="故障历史得分")
    environmental_stress_score: float = Field(description="环境应力得分")
    service_age_score: float = Field(description="使用年限得分")
    trend: Optional[Any] = Field(description="健康趋势 improving/stable/declining", default=None)
    trend_rate: Optional[Any] = Field(description="趋势变化率", default=None)
    calculate_time: datetime = Field()
    bolt_id: str = Field()
    bolt_name: Optional[Any] = Field(default=None)
    current_preload: Optional[Any] = Field(default=None)
    nominal_preload: Optional[Any] = Field(default=None)
    preload_deviation: Optional[Any] = Field(default=None)
    last_maintenance_date: Optional[Any] = Field(default=None)
