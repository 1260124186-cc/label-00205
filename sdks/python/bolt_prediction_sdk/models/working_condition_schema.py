"""
WorkingConditionSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkingConditionSchema(SDKBaseModel):
    """工况信息"""

    temperature: Optional[Any] = Field(description="环境温度", default=None)
    pressure: Optional[Any] = Field(description="系统压力", default=None)
    humidity: Optional[Any] = Field(description="环境湿度", default=None)
    vibration: Optional[Any] = Field(description="振动水平", default=None)
    load_condition: Optional[Any] = Field(description="负载状况 light/medium/heavy/overload", default=None)
    operating_hours: Optional[Any] = Field(description="运行时长（小时）", default=None)
    maintenance_cycle: Optional[Any] = Field(description="维护周期", default=None)
    last_maintenance_date: Optional[Any] = Field(description="上次维护日期", default=None)
    equipment_age: Optional[Any] = Field(description="设备使用年限", default=None)
    extra: Optional[Any] = Field(description="其他工况参数", default=None)
