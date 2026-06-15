"""
ReportStatisticsSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ReportStatisticsSchema(SDKBaseModel):
    """报告统计数据"""

    prediction_count: Optional[int] = Field(description="预测次数", default=0)
    avg_risk_score: Optional[float] = Field(description="平均风险评分", default=0.0)
    min_risk_score: Optional[float] = Field(description="最低风险评分（最高风险）", default=0.0)
    max_risk_score: Optional[float] = Field(description="最高风险评分（最低风险）", default=0.0)
    status_distribution: Optional[Dict[str, int]] = Field(description="状态分布", default=None)
    trend: Optional[str] = Field(description="整体趋势", default='stable')
    max_status: Optional[str] = Field(description="周期内最高状态", default='正常')
    fault_types: Optional[List[str]] = Field(description="出现的故障类型", default=None)
