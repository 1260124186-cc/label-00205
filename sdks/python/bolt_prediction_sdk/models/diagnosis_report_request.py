"""
DiagnosisReportRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DiagnosisReportRequest(SDKBaseModel):
    """单次诊断报告生成请求"""

    status: str = Field(description="状态：正常/关注级预警/检查级预警/紧急级预警/故障")
    risk_score: float = Field(description="风险评分(0-10)，分数越低风险越高")
    node_type: Optional[str] = Field(description="节点类型：bolt/flange", default='bolt')
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    fault_type: Optional[Any] = Field(description="故障类型：loosening/preload_decrease/severe_anomaly/failure", default=None)
    trend: Optional[Any] = Field(description="趋势：stable/decreasing/increasing/fluctuating", default=None)
    recent_values: Optional[Any] = Field(description="近期预紧力数值列表", default=None)
    historical_incidents: Optional[Any] = Field(description="历史同类事件数", default=None)
