"""
FilteredDataResultSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FilteredDataResultSchema(SDKBaseModel):
    """过滤结果"""

    original_count: int = Field()
    filtered_count: int = Field()
    removed_indices: List[int] = Field()
    removal_reasons: Dict[str, str] = Field()
    filter_strategy: str = Field()
    confidence_multiplier: float = Field()
    adjusted_confidence: Optional[Any] = Field(default=None)
