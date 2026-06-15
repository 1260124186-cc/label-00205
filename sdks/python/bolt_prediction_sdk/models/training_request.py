"""
TrainingRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TrainingRequest(SDKBaseModel):
    """模型训练请求"""

    model_type: str = Field(description="模型类型: bolt/flange")
    node_id: Optional[Any] = Field(description="节点ID，空则训练所有", default=None)
    force_retrain: Optional[bool] = Field(description="是否强制重新训练", default=False)
