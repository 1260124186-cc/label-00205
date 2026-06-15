"""
BoltEnsemblePredictionResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltEnsemblePredictionResponse(SDKBaseModel):
    """螺栓集成学习预测调试响应

Attributes:
    bolt_id: 螺栓ID
    prediction_source: 预测来源
    ensemble_method: 集成方法: hard / soft / weighted
    final_status: 最终状态
    final_status_code: 最终状态代码
    final_confidence: 最终置信度
    final_probs: 最终概率分布
    weights: 各预测器权重
    individual_results: 各子模型分项结果
    individual_probs: 各子模型概率分布
    model_version: 模型版本
    duration_ms: 预测耗时(ms)
    ema_accuracy: EMA准确率
    performance_history: 历史表现记录"""

    bolt_id: str = Field()
    prediction_source: str = Field()
    ensemble_method: str = Field()
    final_status: str = Field()
    final_status_code: int = Field()
    final_confidence: float = Field()
    final_probs: Optional[Any] = Field(default=None)
    weights: Dict[str, float] = Field()
    individual_results: List[Dict[str, Any]] = Field()
    individual_probs: Dict[str, Any] = Field()
    model_version: str = Field()
    duration_ms: float = Field()
    ema_accuracy: Dict[str, float] = Field()
    performance_history: Dict[str, List[float]] = Field()
