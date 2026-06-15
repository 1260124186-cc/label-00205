"""
JobExecutionLogSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class JobExecutionLogSchema(SDKBaseModel):
    """任务执行日志"""

    id: int = Field(description="日志ID")
    job_name: str = Field(description="任务名称")
    job_type: str = Field(description="任务类型")
    trigger_type: str = Field(description="触发类型")
    status: str = Field(description="状态")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[Any] = Field(description="结束时间", default=None)
    duration_seconds: Optional[Any] = Field(description="执行时长（秒）", default=None)
    total_nodes: Optional[int] = Field(description="处理节点总数", default=0)
    success_count: Optional[int] = Field(description="成功节点数", default=0)
    failed_count: Optional[int] = Field(description="失败节点数", default=0)
    skipped_count: Optional[int] = Field(description="跳过节点数", default=0)
    shard_index: Optional[Any] = Field(description="分片索引", default=None)
    shard_total: Optional[Any] = Field(description="总分片数", default=None)
    bolt_id_min: Optional[Any] = Field(description="最小bolt_id", default=None)
    bolt_id_max: Optional[Any] = Field(description="最大bolt_id", default=None)
    instance_id: Optional[Any] = Field(description="执行实例ID", default=None)
    error_summary: Optional[Any] = Field(description="错误摘要", default=None)
    error_details: Optional[Any] = Field(description="错误详情", default=None)
    create_time: datetime = Field(description="创建时间")
