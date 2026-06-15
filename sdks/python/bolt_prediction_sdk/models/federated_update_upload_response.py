"""
FederatedUpdateUploadResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedUpdateUploadResponse(SDKBaseModel):
    """上传模型更新响应"""

    client_id: str = Field()
    round_id: int = Field()
    status: str = Field()
    message: str = Field()
    received_at: datetime = Field()
