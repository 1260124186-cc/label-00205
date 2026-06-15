"""
BoltMultivariatePredictionRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltMultivariatePredictionRequest(SDKBaseModel):
    """螺栓多变量耦合预测请求

请求支持两种数据格式：
1. channels 分开提供（各通道时间戳可以不同，服务端会自动对齐插值）
2. aligned_data 统一提供（各通道已在同一时间网格上，仅需缺失值插值）

Attributes:
    bolt_id: 螺栓唯一标识
    channels: 分通道提供的时序数据 {通道名: [[时间, 值], ...]}
    aligned_data: 已对齐的多通道数据 [[时间, 通道1, 通道2, ...], ...]
    aligned_channel_names: 使用 aligned_data 时必须提供，对应列的通道名称（不含时间列）
    timestamps: 可选，统一目标时间网格
    apply_temp_compensation: 是否执行温度耦合补偿（默认 True）
    enable_degradation: 缺失严重时是否降级为单变量预测（默认 True）
    version: 模型版本号（可选）"""

    bolt_id: str = Field(description="螺栓唯一标识")
    channels: Optional[Any] = Field(description="分通道数据 {channel_name: [[timestamp, value], ...]}，时间戳可不对齐", default=None)
    aligned_data: Optional[Any] = Field(description="已对齐的多通道数据（首列为时间戳），形状(N, 1 + C)", default=None)
    aligned_channel_names: Optional[Any] = Field(description="aligned_data 除去时间列后的各通道名，顺序与列对应", default=None)
    timestamps: Optional[Any] = Field(description="目标时间戳列表（可选），不填则自动推导统一时间网格", default=None)
    apply_temp_compensation: Optional[bool] = Field(description="是否执行温度耦合补偿", default=True)
    enable_degradation: Optional[bool] = Field(description="缺失严重时是否自动降级为单变量预测", default=True)
    version: Optional[Any] = Field(description="模型版本号", default=None)
