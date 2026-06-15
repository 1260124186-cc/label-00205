"""
EnhancedTrainingRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EnhancedTrainingRequest(SDKBaseModel):
    """增强版模型训练请求"""

    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: Optional[Any] = Field(description="节点ID，空则训练所有", default=None)
    force_retrain: Optional[bool] = Field(description="是否强制重新训练", default=False)
    data_source: Optional[str] = Field(description="数据来源: db/csv/manual", default='db')
    is_incremental: Optional[bool] = Field(description="是否增量训练", default=False)
    base_model_version: Optional[Any] = Field(description="增量训练的基础版本", default=None)
    freeze_layers: Optional[Any] = Field(description="冻结的层名称", default=None)
    training_config: Optional[Any] = Field(description="详细训练配置", default=None)
