"""
ModelVersionCompareResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelVersionCompareResponse(SDKBaseModel):
    """模型版本对比响应"""

    model_id: str = Field()
    version1: str = Field()
    version2: str = Field()
    metrics_comparison: Dict[str, Any] = Field()
    config_diff: Dict[str, Any] = Field()
