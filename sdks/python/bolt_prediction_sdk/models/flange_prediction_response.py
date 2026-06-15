"""
FlangePredictionResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FlangePredictionResponse(SDKBaseModel):
    """法兰面预测响应"""

    flange_id: str = Field()
    status: str = Field()
    status_code: int = Field()
    confidence: float = Field()
    risk_score: float = Field()
    risk_level: str = Field()
    bolt_count: int = Field()
    attention_weights: Optional[Any] = Field(default=None)
    diagnosis: str = Field()
    recommendations: List[str] = Field()
    prediction_time: datetime = Field()
    correlation_matrix: Optional[Any] = Field(default=None)
    causal_graph: Optional[Any] = Field(default=None)
    leading_bolts: Optional[Any] = Field(default=None)
    propagation_paths: Optional[Any] = Field(default=None)
    root_cause_analysis: Optional[Any] = Field(default=None)
    root_cause_measures: Optional[Any] = Field(default=None)
    model_version: Optional[Any] = Field(description="模型版本号", default=None)
    shadow_version: Optional[Any] = Field(description="Shadow模式版本号", default=None)
    shadow_result: Optional[Any] = Field(description="Shadow模式预测结果", default=None)
    fault_detail: Optional[Any] = Field(description="故障类型细分详情", default=None)
