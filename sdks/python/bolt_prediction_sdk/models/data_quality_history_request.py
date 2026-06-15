"""
DataQualityHistoryRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DataQualityHistoryRequest(SDKBaseModel):
    """获取质量历史请求"""

    sensor_id: str = Field(description="传感器ID")
    start_time: Optional[Any] = Field(description="开始时间", default=None)
    end_time: Optional[Any] = Field(description="结束时间", default=None)
    limit: Optional[int] = Field(description="返回数量限制", default=100)
