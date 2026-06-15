"""
ModelVersionActivateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelVersionActivateRequest(SDKBaseModel):
    """激活/回滚模型版本请求"""

    model_type: str = Field(description="模型类型 bolt/flange")
    node_id: str = Field(description="节点ID")
    version: str = Field(description="目标版本号")
