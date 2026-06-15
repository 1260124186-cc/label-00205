"""
FederatedModelHistoryResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedModelHistoryResponse(SDKBaseModel):
    """获取模型历史响应"""

    model_type: str = Field()
    node_id: str = Field()
    history: List[Dict[str, Any]] = Field()
