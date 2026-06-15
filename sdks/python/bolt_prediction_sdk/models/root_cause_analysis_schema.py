"""
RootCauseAnalysisSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RootCauseAnalysisSchema(SDKBaseModel):
    """根因分析结果"""

    root_cause_bolt: Optional[Any] = Field(default=None)
    root_cause_ranking: List[RootCauseBoltSchema] = Field()
    abnormal_bolts: List[str] = Field()
    is_unbalanced_loosening: bool = Field()
    total_bolts: int = Field()
    abnormal_count: int = Field()
