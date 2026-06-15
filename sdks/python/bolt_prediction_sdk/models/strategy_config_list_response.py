"""
StrategyConfigListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StrategyConfigListResponse(SDKBaseModel):
    """策略配置列表响应"""

    total: int = Field()
    items: List[StrategyConfigItemResponse] = Field()
