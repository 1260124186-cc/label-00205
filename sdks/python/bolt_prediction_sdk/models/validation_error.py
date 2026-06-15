"""
ValidationError 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ValidationError(SDKBaseModel):
    """ValidationError"""

    loc: List[Any] = Field()
    msg: str = Field()
    type: str = Field()
    input: Optional[Any] = Field(default=None)
    ctx: Optional[Dict[str, Any]] = Field(default=None)
