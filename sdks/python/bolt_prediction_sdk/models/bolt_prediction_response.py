"""
BoltPredictionResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltPredictionResponse(SDKBaseModel):
    """螺栓预测响应

Attributes:
    bolt_id: 螺栓ID
    status: 预测状态
    status_code: 状态代码
    confidence: 置信度
    risk_score: 风险评分
    risk_level: 风险等级
    diagnosis: 诊断结论
    recommendations: 推荐措施
    prediction_time: 预测时间
    model_version: 模型版本号
    shadow_version: Shadow模式版本号（如有）
    shadow_result: Shadow模式预测结果（如有）"""

    bolt_id: str = Field()
    status: str = Field()
    status_code: int = Field()
    confidence: float = Field()
    risk_score: float = Field()
    risk_level: str = Field()
    diagnosis: str = Field()
    recommendations: List[str] = Field()
    prediction_time: datetime = Field()
    model_version: Optional[Any] = Field(description="模型版本号", default=None)
    shadow_version: Optional[Any] = Field(description="Shadow模式版本号", default=None)
    shadow_result: Optional[Any] = Field(description="Shadow模式预测结果", default=None)
    fault_detail: Optional[Any] = Field(description="故障类型细分详情", default=None)
    prediction_source: Optional[Any] = Field(description="预测来源: lstm / ensemble / rule", default=None)
    ensemble: Optional[Any] = Field(description="Ensemble集成学习详情（触发时返回）", default=None)
