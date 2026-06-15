"""
CaseSimilaritySearchRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CaseSimilaritySearchRequest(SDKBaseModel):
    """案例相似度检索请求"""

    node_type: Optional[Any] = Field(description="节点类型 bolt/flange", default=None)
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    fault_type: Optional[Any] = Field(description="故障类型", default=None)
    fault_level: Optional[Any] = Field(description="故障级别", default=None)
    sensor_data: Optional[Any] = Field(description="传感器时序数据", default=None)
    sensor_features: Optional[Any] = Field(description="传感器特征", default=None)
    feature_vector: Optional[Any] = Field(description="特征向量", default=None)
    tags: Optional[Any] = Field(description="标签过滤", default=None)
    top_k: Optional[int] = Field(description="返回Top-K相似案例", default=5)
    min_similarity: Optional[float] = Field(description="最低相似度阈值", default=0.0)
    only_approved: Optional[bool] = Field(description="只返回已审核通过的案例", default=True)
    tenant_id: Optional[Any] = Field(description="租户ID过滤", default=None)
