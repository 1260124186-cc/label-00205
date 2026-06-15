"""
DataQualityInfo 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DataQualityInfo(SDKBaseModel):
    """数据质量评估结果

Attributes:
    level: 数据质量等级 full=完整, partial=部分缺失, degraded=降级单变量
    complete_ratio: 完整数据占比 (0-1)
    missing_channels: 被丢弃/降级时缺失的通道列表
    interpolation_count: 插值填充的总数据点数
    interpolation_flags: 可选，每个时间点每通道的插值标记（1=插值 0=原始）
    degradation_applied: 是否触发了降级策略"""

    level: Optional[str] = Field(description="数据质量等级: full / partial / degraded", default='full')
    complete_ratio: Optional[float] = Field(description="完整数据占比 0-1", default=1.0)
    missing_channels: Optional[List[str]] = Field(description="缺失或降级丢弃的通道列表", default=None)
    interpolation_count: Optional[int] = Field(description="插值填充的总点数", default=0)
    degradation_applied: Optional[bool] = Field(description="是否因缺失严重触发了单变量降级", default=False)
    actual_channels_used: Optional[List[str]] = Field(description="实际参与模型计算的通道", default=None)
