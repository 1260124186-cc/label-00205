"""
RuleViolationSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RuleViolationSchema(SDKBaseModel):
    """规则违反详情"""

    rule_type: str = Field()
    rule_name: str = Field()
    severity: str = Field()
    description: str = Field()
    violation_indices: List[int] = Field()
    violation_values: Optional[Any] = Field(default=None)
    threshold: Optional[Any] = Field(default=None)
    actual_value: Optional[Any] = Field(default=None)
