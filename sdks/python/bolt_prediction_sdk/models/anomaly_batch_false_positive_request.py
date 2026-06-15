"""
AnomalyBatchFalsePositiveRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyBatchFalsePositiveRequest(SDKBaseModel):
    """批量标注误报请求"""

    anomaly_ids: List[int] = Field(description="异常记录ID列表")
    confirmed_by: Optional[Any] = Field(description="标注人ID", default=None)
    confirm_note: Optional[Any] = Field(description="标注备注", default=None)
