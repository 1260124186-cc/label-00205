"""
HTTPValidationError 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HttpValidationError(SDKBaseModel):
    """HTTPValidationError"""

    detail: Optional[List[ValidationError]] = Field(default=None)
