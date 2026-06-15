"""
HealthRollupResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthRollupResponse(SDKBaseModel):
    """健康度汇总报表响应"""

    report_id: Optional[Any] = Field(default=None)
    rollup_data: ProductionLineHealthRollupSchema = Field()
    saved: bool = Field()
