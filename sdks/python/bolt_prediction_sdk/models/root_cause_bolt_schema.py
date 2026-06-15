"""
RootCauseBoltSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RootCauseBoltSchema(SDKBaseModel):
    """根因螺栓信息"""

    bolt_id: str = Field()
    index: int = Field()
    root_cause_score: float = Field()
    status_code: int = Field()
    health_index: float = Field()
    is_abnormal: bool = Field()
