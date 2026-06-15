"""
KnowledgeCaseResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class KnowledgeCaseResponse(SDKBaseModel):
    """案例响应"""

    id: int = Field()
    case_no: str = Field()
    case_title: str = Field()
    node_type: Optional[Any] = Field(default=None)
    node_id: Optional[Any] = Field(default=None)
    fault_type: Optional[Any] = Field(default=None)
    fault_level: Optional[Any] = Field(default=None)
    working_condition: Optional[Any] = Field(default=None)
    sensor_features: Optional[Any] = Field(default=None)
    diagnosis: Optional[Any] = Field(default=None)
    root_cause: Optional[Any] = Field(default=None)
    treatment_plan: Optional[Any] = Field(default=None)
    effect_evaluation: Optional[Any] = Field(default=None)
    effectiveness_score: Optional[Any] = Field(default=None)
    status: str = Field()
    version: int = Field()
    tenant_id: Optional[Any] = Field(default=None)
    creator_id: Optional[Any] = Field(default=None)
    creator_name: Optional[Any] = Field(default=None)
    reviewer_id: Optional[Any] = Field(default=None)
    reviewer_name: Optional[Any] = Field(default=None)
    review_time: Optional[Any] = Field(default=None)
    review_comment: Optional[Any] = Field(default=None)
    source_alert_id: Optional[Any] = Field(default=None)
    source_prediction_id: Optional[Any] = Field(default=None)
    tags: Optional[Any] = Field(default=None)
    similarity_score: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
    update_time: datetime = Field()
