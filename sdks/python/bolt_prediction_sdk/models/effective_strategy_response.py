"""
EffectiveStrategyResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EffectiveStrategyResponse(SDKBaseModel):
    """当前生效策略响应（含全局和节点覆盖）"""

    global_config: StrategyConfigItemResponse = Field()
    node_overrides: Optional[List[StrategyConfigItemResponse]] = Field(default=None)
    effective: StrategyConfigItemResponse = Field()
