"""
TreatmentStepSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TreatmentStepSchema(SDKBaseModel):
    """处置步骤"""

    step_order: int = Field(description="步骤序号")
    action: str = Field(description="处置动作")
    description: Optional[Any] = Field(description="详细描述", default=None)
    tools: Optional[Any] = Field(description="所需工具", default=None)
    duration_minutes: Optional[Any] = Field(description="预计耗时（分钟）", default=None)
    safety_notes: Optional[Any] = Field(description="安全注意事项", default=None)
