"""
CausalGraphNodeSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CausalGraphNodeSchema(SDKBaseModel):
    """因果图节点"""

    id: str = Field()
    index: int = Field()
    in_degree: int = Field()
    out_degree: int = Field()
    total_degree: int = Field()
    centrality: float = Field()
