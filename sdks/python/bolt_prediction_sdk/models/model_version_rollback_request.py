"""
ModelVersionRollbackRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelVersionRollbackRequest(SDKBaseModel):
    """回滚模型版本请求"""

    model_type: str = Field(description="模型类型 bolt/flange")
    node_id: str = Field(description="节点ID")
    version: Optional[Any] = Field(description="目标版本号，不填则回滚到上一版本", default=None)
