"""
BoltMultivariatePredictionResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class BoltMultivariatePredictionResponse(SDKBaseModel):
    """螺栓多变量耦合预测响应

在标准螺栓预测响应基础上，新增：
- data_quality: 数据质量评估（含降级信息）
- channels_info: 实际使用的通道元数据
- temp_compensation: 温度耦合补偿详情
- feature_importance: 各通道特征重要性（可解释性）"""

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
    input_dim_actual: int = Field(description="实际输入模型的通道数")
    channels_info: Optional[List[MultivariateChannelSchema]] = Field(description="实际使用的通道元数据", default=None)
    data_quality: DataQualityInfo = Field(description="数据质量评估与降级信息")
    temp_compensation: Optional[Any] = Field(description="温度耦合补偿详情", default=None)
    feature_importance: Optional[Any] = Field(description="各通道特征重要性（可解释性）", default=None)
    sequence_length_used: Optional[int] = Field(description="实际送入模型的序列长度", default=0)
    prediction_source: Optional[str] = Field(description="预测来源: multivariate_lstm / degraded_univariate / fallback", default='multivariate_lstm')
    fault_detail: Optional[Any] = Field(description="故障类型细分详情", default=None)
    shadow_version: Optional[Any] = Field(description="Shadow模式版本号", default=None)
    shadow_result: Optional[Any] = Field(description="Shadow模式预测结果", default=None)
