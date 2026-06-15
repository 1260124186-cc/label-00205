"""
FederatedAggregatorConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedAggregatorConfig(SDKBaseModel):
    """聚合器配置"""

    strategy: Optional[str] = Field(description="聚合策略: fedavg/weighted_avg/median/trimmed_mean/fedprox/fedopt", default='weighted_avg')
    trim_ratio: Optional[float] = Field(description="修剪均值比例", default=0.1)
    mu: Optional[float] = Field(description="FedProx近端项系数", default=0.01)
    server_learning_rate: Optional[float] = Field(description="服务器学习率", default=1.0)
    min_clients_per_round: Optional[int] = Field(description="每轮最少客户端数", default=2)
    enable_outlier_detection: Optional[bool] = Field(description="是否启用异常值检测", default=True)
