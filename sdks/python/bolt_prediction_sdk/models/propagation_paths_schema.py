"""
PropagationPathsSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class PropagationPathsSchema(SDKBaseModel):
    """传播路径分析结果"""

    source_bolt: str = Field()
    source_idx: int = Field()
    paths: List[PropagationPathSchema] = Field()
    total_path_count: int = Field()
    reachable_bolts: List[str] = Field()
    propagation_distance: Dict[str, Any] = Field()
    max_depth: int = Field()
