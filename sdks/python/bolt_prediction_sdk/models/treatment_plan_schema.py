"""
TreatmentPlanSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class TreatmentPlanSchema(SDKBaseModel):
    """处置方案"""

    plan_name: Optional[Any] = Field(description="方案名称", default=None)
    steps: Optional[List[TreatmentStepSchema]] = Field(description="处置步骤列表", default=None)
    materials: Optional[Any] = Field(description="所需材料", default=None)
    estimated_cost: Optional[Any] = Field(description="预估成本", default=None)
    difficulty_level: Optional[Any] = Field(description="难度等级 easy/medium/hard", default=None)
    personnel_required: Optional[Any] = Field(description="所需人员", default=None)
