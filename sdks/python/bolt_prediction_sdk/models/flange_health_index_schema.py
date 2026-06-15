"""
FlangeHealthIndexSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FlangeHealthIndexSchema(SDKBaseModel):
    """法兰面健康度指数（聚合）"""

    flange_id: str = Field()
    flange_name: Optional[Any] = Field(default=None)
    hi_score: float = Field(description="法兰面综合健康度")
    hi_level: str = Field(description="健康等级")
    worst_bolt_hi: float = Field(description="最差螺栓健康度")
    worst_bolt_id: str = Field(description="最差螺栓ID")
    average_bolt_hi: float = Field(description="平均螺栓健康度")
    median_bolt_hi: float = Field(description="螺栓健康度中位数")
    degradation_rate: float = Field(description="劣化速率（HI/天）")
    bolt_count: int = Field(description="螺栓总数")
    healthy_bolt_count: int = Field(description="健康螺栓数(HI>=70)")
    warning_bolt_count: int = Field(description="预警螺栓数(50<=HI<70)")
    critical_bolt_count: int = Field(description="危险螺栓数(HI<50)")
    bolts_health: List[BoltHealthIndexSchema] = Field(description="各螺栓健康度详情")
    trend: Optional[Any] = Field(default=None)
    calculate_time: datetime = Field()
