"""
AnomalyQueryRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyQueryRequest(SDKBaseModel):
    """异常查询请求

支持按 sensor_id、时间范围、类型、确认状态等多维度查询。"""

    sensor_id: Optional[Any] = Field(description="传感器/螺栓ID", default=None)
    start_time: Optional[Any] = Field(description="开始时间", default=None)
    end_time: Optional[Any] = Field(description="结束时间", default=None)
    anomaly_type: Optional[Any] = Field(description="异常类型", default=None)
    classification: Optional[Any] = Field(description="异常分类", default=None)
    is_confirmed: Optional[Any] = Field(description="是否已确认", default=None)
    is_false_positive: Optional[Any] = Field(description="是否为误报", default=None)
    min_score: Optional[Any] = Field(description="最低异常评分", default=None)
    max_score: Optional[Any] = Field(description="最高异常评分", default=None)
    limit: Optional[int] = Field(description="返回数量限制", default=100)
    offset: Optional[int] = Field(description="偏移量", default=0)
    sort_by: Optional[str] = Field(description="排序字段", default='original_time')
    sort_order: Optional[str] = Field(description="排序方向 asc/desc", default='desc')
