"""
ModelVersionCompareRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ModelVersionCompareRequest(SDKBaseModel):
    """模型版本对比请求"""

    version1: str = Field()
    version2: str = Field()
