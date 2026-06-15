"""
IncrementalTrainingConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class IncrementalTrainingConfig(SDKBaseModel):
    """增量训练配置"""

    enabled: Optional[bool] = Field(description="是否增量训练", default=False)
    freeze_layers: Optional[Any] = Field(description="冻结的层名称列表，如 ['lstm1', 'lstm2']", default=None)
    base_model_version: Optional[Any] = Field(description="基础模型版本号，None则使用最新版本", default=None)
