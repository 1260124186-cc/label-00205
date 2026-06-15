"""
CausalGraphEdgeSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CausalGraphEdgeSchema(SDKBaseModel):
    """因果图边"""

    source: str = Field()
    target: str = Field()
    source_idx: int = Field()
    target_idx: int = Field()
    weight: float = Field()
    correlation: float = Field()
    p_value: Optional[Any] = Field(default=None)
    f_stat: Optional[Any] = Field(default=None)
    lag: Optional[Any] = Field(default=None)
    type: str = Field()
