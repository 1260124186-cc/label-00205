"""
AnomalyDataResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyDataResponse(SDKBaseModel):
    """异常数据响应模型

对应 sc_anomaly_data 表的完整字段，
包含异常信息、分类、确认标注等。"""

    id: int = Field()
    sensor_id: str = Field()
    anomaly_value: Optional[Any] = Field(default=None)
    anomaly_type: Optional[Any] = Field(default=None)
    anomaly_score: Optional[Any] = Field(default=None)
    original_time: Optional[Any] = Field(default=None)
    details: Optional[Any] = Field(default=None)
    classification: Optional[Any] = Field(default=None)
    classification_confidence: Optional[Any] = Field(default=None)
    collection_subtype: Optional[Any] = Field(default=None)
    true_anomaly_subtype: Optional[Any] = Field(default=None)
    classification_evidence: Optional[Any] = Field(default=None)
    is_confirmed: Optional[bool] = Field(default=False)
    is_false_positive: Optional[bool] = Field(default=False)
    confirmed_by: Optional[Any] = Field(default=None)
    confirmed_time: Optional[Any] = Field(default=None)
    confirm_note: Optional[Any] = Field(default=None)
    tenant_id: Optional[Any] = Field(default=None)
    create_time: Optional[Any] = Field(default=None)
    update_time: Optional[Any] = Field(default=None)
