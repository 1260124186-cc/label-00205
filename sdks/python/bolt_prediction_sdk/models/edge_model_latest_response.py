"""
EdgeModelLatestResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeModelLatestResponse(SDKBaseModel):
    """EdgeModelLatestResponse"""

    version: str = Field()
    model_type: str = Field()
    node_id: Optional[Any] = Field(default=None)
    download_url: str = Field()
    file_hash: str = Field()
    file_size: int = Field()
    created_at: str = Field()
    metrics: Optional[Any] = Field(default=None)
