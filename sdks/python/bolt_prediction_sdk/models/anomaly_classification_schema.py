"""
AnomalyClassificationSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyClassificationSchema(SDKBaseModel):
    """异常分类结果"""

    anomaly_id: Optional[Any] = Field(default=None)
    sensor_id: str = Field()
    anomaly_value: float = Field()
    anomaly_type: str = Field()
    classification: str = Field()
    classification_confidence: float = Field()
    collection_subtype: Optional[Any] = Field(default=None)
    true_anomaly_subtype: Optional[Any] = Field(default=None)
    evidence: Dict[str, Any] = Field()
    original_time: Optional[Any] = Field(default=None)
