"""
DiagnosisReportResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DiagnosisReportResponse(SDKBaseModel):
    """诊断报告响应"""

    diagnosis_summary: str = Field(description="诊断摘要（200字内）")
    recommended_actions: List[str] = Field(description="推荐处置措施（分步骤）")
    urgency_level: str = Field(description="紧急程度：low/medium/high/critical")
    model: str = Field(description="使用的模型")
    tokens_used: Optional[int] = Field(description="Token用量", default=0)
    latency_ms: Optional[float] = Field(description="生成延迟（毫秒）", default=0.0)
    is_fallback: Optional[bool] = Field(description="是否使用降级模板", default=False)
