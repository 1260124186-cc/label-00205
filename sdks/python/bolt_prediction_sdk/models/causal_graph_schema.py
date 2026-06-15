"""
CausalGraphSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CausalGraphSchema(SDKBaseModel):
    """因果图"""

    nodes: List[CausalGraphNodeSchema] = Field()
    edges: List[CausalGraphEdgeSchema] = Field()
    adjacency_matrix: List[List[float]] = Field()
    edge_weights: List[List[float]] = Field()
    bolt_ids: List[str] = Field()
