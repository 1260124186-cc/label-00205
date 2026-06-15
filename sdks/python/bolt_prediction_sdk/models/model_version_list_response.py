"""
ModelVersionListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelVersionListResponse(SDKBaseModel):
    """模型版本列表响应"""

    model_id: str = Field()
    model_type: str = Field()
    versions: List[ModelVersionSchema] = Field()
