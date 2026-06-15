"""
AnomalyLinkResultSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyLinkResultSchema(SDKBaseModel):
    """异常联动结果"""

    sensor_id: str = Field()
    total_anomalies: int = Field()
    true_anomalies: int = Field()
    collection_anomalies: int = Field()
    uncertain_anomalies: int = Field()
    mixed_anomalies: int = Field()
    classified_anomalies: List[AnomalyClassificationSchema] = Field()
