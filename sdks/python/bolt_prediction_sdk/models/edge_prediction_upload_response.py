"""
EdgePredictionUploadResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgePredictionUploadResponse(SDKBaseModel):
    """EdgePredictionUploadResponse"""

    device_id: str = Field()
    received_count: int = Field()
    status: str = Field()
    message: str = Field()
