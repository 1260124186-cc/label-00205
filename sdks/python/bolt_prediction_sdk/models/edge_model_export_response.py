"""
EdgeModelExportResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeModelExportResponse(SDKBaseModel):
    """EdgeModelExportResponse"""

    model_type: str = Field()
    node_id: Optional[Any] = Field(default=None)
    version: str = Field()
    export_format: str = Field()
    package_url: str = Field()
    file_hash: str = Field()
    file_size: int = Field()
    includes_preprocessing: Optional[bool] = Field(default=True)
    includes_signature: Optional[bool] = Field(default=True)
    exported_at: str = Field()
