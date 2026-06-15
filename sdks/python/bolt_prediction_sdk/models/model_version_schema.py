"""
ModelVersionSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelVersionSchema(SDKBaseModel):
    """模型版本信息"""

    version: str = Field()
    model_id: str = Field()
    model_type: str = Field()
    created_at: datetime = Field()
    file_path: str = Field()
    file_hash: str = Field()
    metrics: Optional[Dict[str, float]] = Field(default=None)
    config: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=False)
    description: Optional[str] = Field(default='')
