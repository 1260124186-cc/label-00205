"""
LeadingBoltSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LeadingBoltSchema(SDKBaseModel):
    """领先螺栓信息"""

    bolt_id: str = Field()
    index: int = Field()
    leading_score: float = Field()
    out_degree: int = Field()
    in_degree: int = Field()
    net_degree: int = Field()
    out_strength: float = Field()
    in_strength: float = Field()
    net_strength: float = Field()
    trend_leadership: float = Field()
    is_leading: bool = Field()
