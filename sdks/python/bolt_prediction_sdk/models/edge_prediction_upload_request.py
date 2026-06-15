"""
EdgePredictionUploadRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgePredictionUploadRequest(SDKBaseModel):
    """EdgePredictionUploadRequest"""

    device_id: str = Field(description="边缘设备ID")
    predictions: List[Dict[str, Any]] = Field(description="预测结果列表")
