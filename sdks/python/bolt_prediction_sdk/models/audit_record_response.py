"""
AuditRecordResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AuditRecordResponse(SDKBaseModel):
    """审计记录响应"""

    id: int = Field()
    prediction_id: str = Field()
    node_type: str = Field()
    node_id: str = Field()
    input_hash: Optional[Any] = Field(default=None)
    model_version: Optional[Any] = Field(default=None)
    model_type: Optional[Any] = Field(default=None)
    feature_summary: Optional[Any] = Field(default=None)
    intermediate_results: Optional[Any] = Field(default=None)
    final_decision: Optional[Any] = Field(default=None)
    strategy_version: Optional[Any] = Field(default=None)
    strategy_type: Optional[Any] = Field(default=None)
    explainability: Optional[Any] = Field(default=None)
    retention_years: Optional[int] = Field(default=3)
    expire_time: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
