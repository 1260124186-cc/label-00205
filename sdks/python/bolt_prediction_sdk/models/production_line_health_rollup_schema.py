"""
ProductionLineHealthRollupSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ProductionLineHealthRollupSchema(SDKBaseModel):
    """产线/装置级健康度汇总报表"""

    line_id: str = Field()
    line_name: str = Field()
    line_type: str = Field(description="产线类型 production_line/device/unit")
    overall_hi: float = Field(description="整体健康度")
    overall_level: str = Field(description="整体健康等级")
    total_flange_count: int = Field(description="法兰面总数")
    total_bolt_count: int = Field(description="螺栓总数")
    healthy_flange_count: int = Field(description="健康法兰面数")
    warning_flange_count: int = Field(description="预警法兰面数")
    critical_flange_count: int = Field(description="危险法兰面数")
    healthy_bolt_count: int = Field(description="健康螺栓数")
    warning_bolt_count: int = Field(description="预警螺栓数")
    critical_bolt_count: int = Field(description="危险螺栓数")
    worst_flange_hi: float = Field(description="最差法兰面健康度")
    worst_flange_id: str = Field(description="最差法兰面ID")
    average_degradation_rate: float = Field(description="平均劣化速率")
    flanges_health: List[FlangeHealthIndexSchema] = Field(description="各法兰面健康度")
    risk_summary: Dict[str, Any] = Field(description="风险汇总")
    maintenance_priorities: List[Dict[str, Any]] = Field(description="维护优先级排序")
    report_date: datetime = Field()
    generate_time: datetime = Field()
