"""
DataQualityCheckRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DataQualityCheckRequest(SDKBaseModel):
    """数据质量检查请求"""

    sensor_id: str = Field(description="传感器/螺栓ID")
    data: List[List[Any]] = Field(description="时序数据，每个元素为[时间字符串, 数值]")
    include_anomaly_classification: Optional[bool] = Field(description="是否包含异常分类", default=True)
