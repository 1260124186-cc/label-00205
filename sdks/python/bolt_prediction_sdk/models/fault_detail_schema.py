"""
FaultDetailSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FaultDetailSchema(SDKBaseModel):
    """故障类型细分详情"""

    fault_type: str = Field(description="故障类型: loosening/overload/fracture/fatigue/corrosion")
    fault_confidence: float = Field(description="故障分类置信度")
    fault_name: str = Field(description="故障类型中文名")
    severity: int = Field(description="严重程度 1-10")
    evidence: Optional[List[str]] = Field(description="判定依据", default=None)
    recommendations: Optional[List[str]] = Field(description="故障类型差异化推荐措施", default=None)
    pattern: Optional[Any] = Field(description="故障模式特征证据", default=None)
