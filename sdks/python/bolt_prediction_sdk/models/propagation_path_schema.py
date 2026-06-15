"""
PropagationPathSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class PropagationPathSchema(SDKBaseModel):
    """传播路径"""

    path: List[str] = Field()
    path_indices: List[int] = Field()
    depth: int = Field()
    total_weight: float = Field()
    avg_weight: float = Field()
