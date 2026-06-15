"""
ThresholdConfigSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ThresholdConfigSchema(SDKBaseModel):
    """预警阈值配置"""

    high_risk_threshold: Optional[int] = Field(description="高风险阈值", default=3)
    medium_risk_threshold: Optional[int] = Field(description="中风险阈值", default=7)
    min_normal_preload: Optional[float] = Field(description="正常预紧力最小值", default=400)
    max_normal_preload: Optional[float] = Field(description="正常预紧力最大值", default=800)
    warning_deviation: Optional[float] = Field(description="预警偏差比例", default=0.1)
    critical_deviation: Optional[float] = Field(description="紧急偏差比例", default=0.2)
    auto_create_work_order_level: Optional[int] = Field(description="自动创建工单的最低告警级别", default=3)
    default_upgrade_minutes: Optional[int] = Field(description="默认未处理升级时间（分钟）", default=30)
