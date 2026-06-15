"""
WorkOrderStatsResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkOrderStatsResponse(SDKBaseModel):
    """工单统计响应"""

    total_work_orders: Optional[int] = Field(description="总工单数", default=0)
    closed_work_orders: Optional[int] = Field(description="已关闭工单数", default=0)
    open_work_orders: Optional[int] = Field(description="待处理工单数", default=0)
    in_progress_work_orders: Optional[int] = Field(description="处理中工单数", default=0)
    mttr_hours: Optional[Any] = Field(description="平均修复时间 MTTR 小时", default=None)
    mttr_minutes: Optional[Any] = Field(description="平均修复时间 MTTR 分钟", default=None)
    false_positive_rate: Optional[Any] = Field(description="误报率 0-1", default=None)
    false_positive_count: Optional[int] = Field(description="误报数量", default=0)
    recurrence_rate: Optional[Any] = Field(description="重复故障率 0-1", default=None)
    recurrence_count: Optional[int] = Field(description="重复故障数量", default=0)
    avg_resolve_hours: Optional[Any] = Field(description="平均解决时间 小时", default=None)
    on_time_completion_rate: Optional[Any] = Field(description="按时完成率 0-1", default=None)
    priority_distribution: Optional[Any] = Field(description="优先级分布", default=None)
    status_distribution: Optional[Any] = Field(description="状态分布", default=None)
    time_range: Optional[Any] = Field(description="统计时间范围", default=None)
