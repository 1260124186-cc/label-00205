"""
API请求和响应模型定义

使用Pydantic定义API的输入输出数据结构。

包含:
- 螺栓预测请求/响应
- 法兰面预测请求/响应
- 风险评估请求/响应
- 模型训练请求/响应
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_serializer


# ==================== 基础模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: Optional[str] = None


# ==================== 螺栓预测 ====================

class BoltPredictionRequest(BaseModel):
    """
    螺栓预测请求
    
    Attributes:
        螺栓id: 螺栓唯一标识
        data: 预紧力时序数据 [[时间, 预紧力], ...]
    """
    螺栓id: str = Field(..., description="螺栓唯一标识", alias="bolt_id")
    data: List[List[Any]] = Field(
        ..., 
        description="预紧力时序数据，每个元素为[时间字符串, 预紧力值]",
        min_length=1
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "螺栓id": "B001",
                "data": [
                    ["20250201 00:00:00", 400.00],
                    ["20250201 00:01:00", 401.50],
                    ["20250201 00:02:00", 399.80]
                ]
            }
        }


class BoltPredictionResponse(BaseModel):
    """
    螺栓预测响应
    
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
    """
    bolt_id: str
    status: str
    status_code: int
    confidence: float
    risk_score: float
    risk_level: str
    diagnosis: str
    recommendations: List[str]
    prediction_time: datetime


# ==================== 法兰面预测 ====================

class FlangePredictionRequest(BaseModel):
    """
    法兰面预测请求
    
    Attributes:
        法兰面id: 法兰面唯一标识
        data: 多螺栓预紧力时序数据
    """
    法兰面id: str = Field(..., description="法兰面唯一标识", alias="flange_id")
    data: List[List[List[Any]]] = Field(
        ...,
        description="多螺栓预紧力数据，三维数组[螺栓][时间点][时间,预紧力]"
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "法兰面id": "F001",
                "data": [
                    [["20250201 00:00:00", 605], ["20250201 00:01:00", 509]],
                    [["20250201 00:00:00", 598], ["20250201 00:01:00", 594]]
                ]
            }
        }


class FlangePredictionResponse(BaseModel):
    """法兰面预测响应"""
    flange_id: str
    status: str
    status_code: int
    confidence: float
    risk_score: float
    risk_level: str
    bolt_count: int
    attention_weights: Optional[List[float]] = None
    diagnosis: str
    recommendations: List[str]
    prediction_time: datetime


# ==================== 风险评估 ====================

class RiskAssessmentRequest(BaseModel):
    """风险评估请求"""
    node_id: str = Field(..., description="节点ID（螺栓或法兰面）")
    node_type: str = Field(..., description="节点类型: bolt/flange")
    data: List[List[Any]] = Field(..., description="预紧力时序数据")


class RiskAssessmentResponse(BaseModel):
    """风险评估响应"""
    node_id: str
    node_type: str
    risk_score: float
    risk_level: str
    factors: List[str]
    diagnosis: str
    recommendations: List[str]
    confidence: float


# ==================== 月度预测 ====================

class MonthlyForecastRequest(BaseModel):
    """月度预测请求"""
    node_id: str
    node_type: str
    forecast_days: int = Field(default=30, ge=1, le=90)


class MonthlyForecastResponse(BaseModel):
    """月度预测响应"""
    node_id: str
    node_type: str
    pw_type: str
    fault_type: Optional[str]
    begin_time: Optional[datetime]
    end_time: Optional[datetime]
    confidence: float
    rec_measures: str
    forecast_dates: List[datetime]
    forecast_values: List[float]


# ==================== 模型管理 ====================

class TrainingRequest(BaseModel):
    """模型训练请求"""
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID，空则训练所有")
    force_retrain: bool = Field(default=False, description="是否强制重新训练")


class TrainingResponse(BaseModel):
    """模型训练响应"""
    model_type: str
    node_id: Optional[str]
    status: str
    message: str
    training_time: float
    metrics: Optional[Dict[str, float]] = None


class ModelInfoResponse(BaseModel):
    """模型信息响应"""
    model_type: str
    node_id: str
    is_trained: bool
    last_training_time: Optional[datetime]
    training_samples: Optional[int]
    validation_accuracy: Optional[float]


# ==================== 策略配置 ====================

class StrategyConfigRequest(BaseModel):
    """预警策略配置请求"""
    strategy_type: int = Field(..., ge=1, le=2, description="策略类型: 1=应报尽报, 2=精准报警")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1)
    false_positive_threshold: Optional[float] = Field(None, ge=0, le=1)
    false_negative_threshold: Optional[float] = Field(None, ge=0, le=1)


class StrategyConfigResponse(BaseModel):
    """策略配置响应"""
    strategy_type: int
    confidence_threshold: float
    false_positive_threshold: Optional[float]
    false_negative_threshold: Optional[float]
    updated_at: datetime


# ==================== 联邦学习 ====================

class FederatedClientRegisterRequest(BaseModel):
    """联邦学习客户端注册请求"""
    client_id: str = Field(..., description="客户端/厂区ID")
    factory_name: Optional[str] = Field(None, description="厂区名称")
    location: Optional[str] = Field(None, description="厂区位置")
    client_info: Optional[Dict[str, Any]] = Field(None, description="客户端附加信息")


class FederatedClientRegisterResponse(BaseModel):
    """联邦学习客户端注册响应"""
    client_id: str
    status: str
    message: str
    registered_at: datetime


class FederatedGlobalModelRequest(BaseModel):
    """获取全局模型请求"""
    client_id: str = Field(..., description="客户端ID")
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: str = Field(..., description="节点ID")


class FederatedGlobalModelResponse(BaseModel):
    """获取全局模型响应"""
    model_type: str
    node_id: str
    round_id: int
    version: Optional[int] = None
    weights: Dict[str, Any]
    server_time: datetime
    enable_two_level_arch: bool = True
    metrics: Optional[Dict[str, Any]] = None


class FederatedUpdateUploadRequest(BaseModel):
    """上传模型更新请求"""
    client_id: str = Field(..., description="客户端ID")
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: str = Field(..., description="节点ID")
    round_id: int = Field(..., description="联邦学习轮次ID")
    weights: Dict[str, Any] = Field(..., description="模型更新（权重或差异）")
    num_samples: int = Field(..., description="训练样本数量")
    metrics: Optional[Dict[str, float]] = Field(None, description="训练指标")
    encrypted: bool = Field(False, description="是否加密")
    encrypted_update: Optional[str] = Field(None, description="加密后的更新（Base64编码）")
    update_type: str = Field("difference", description="更新类型: weights/gradients/difference")


class FederatedUpdateUploadResponse(BaseModel):
    """上传模型更新响应"""
    client_id: str
    round_id: int
    status: str
    message: str
    received_at: datetime


class FederatedRoundStartRequest(BaseModel):
    """开始联邦学习轮次请求"""
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: str = Field(..., description="节点ID")
    expected_clients: Optional[List[str]] = Field(None, description="期望参与的客户端列表")


class FederatedRoundStartResponse(BaseModel):
    """开始联邦学习轮次响应"""
    round_id: int
    model_type: str
    node_id: str
    status: str
    expected_clients: List[str]
    started_at: datetime


class FederatedRoundAggregateRequest(BaseModel):
    """聚合模型更新请求"""
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: str = Field(..., description="节点ID")


class FederatedRoundAggregateResponse(BaseModel):
    """聚合模型更新响应"""
    round_id: int
    model_type: str
    node_id: str
    status: str
    message: str
    num_clients_aggregated: int
    version: Optional[int] = None
    metrics: Optional[Dict[str, Any]] = None
    aggregated_at: datetime


class FederatedServerStatusResponse(BaseModel):
    """联邦学习服务器状态响应"""
    registered_clients: int
    active_clients: int
    total_rounds: int
    completed_rounds: int
    failed_rounds: int
    aggregation_strategy: str
    managed_models: List[str]
    current_round: Optional[Dict[str, Any]] = None


class FederatedModelHistoryRequest(BaseModel):
    """获取模型历史请求"""
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: str = Field(..., description="节点ID")


class FederatedModelHistoryResponse(BaseModel):
    """获取模型历史响应"""
    model_type: str
    node_id: str
    history: List[Dict[str, Any]]


class FederatedClientStatusResponse(BaseModel):
    """客户端状态响应"""
    client_id: str
    factory_id: str
    model_type: Optional[str]
    node_id: Optional[str]
    current_round: int
    has_global_model: bool
    has_local_model: bool
    training_count: int
    privacy_mechanism: str
    update_type: str
    two_level_arch_enabled: bool
    last_update_time: Optional[datetime]


class FederatedLocalTrainRequest(BaseModel):
    """本地训练请求"""
    client_id: str = Field(..., description="客户端ID")
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: str = Field(..., description="节点ID")
    local_epochs: Optional[int] = Field(None, description="本地训练轮数")
    fine_tune: bool = Field(False, description="是否执行本地微调（第二层）")
    train_data: Optional[List[Any]] = Field(None, description="训练数据（可选，自动加载）")
    train_labels: Optional[List[int]] = Field(None, description="训练标签（可选，自动加载）")


class FederatedLocalTrainResponse(BaseModel):
    """本地训练响应"""
    client_id: str
    model_type: str
    node_id: str
    status: str
    message: str
    num_samples: int
    training_time: float
    metrics: Dict[str, float]


class FederatedPrivacyConfig(BaseModel):
    """隐私保护配置"""
    mechanism: str = Field("none", description="隐私机制: none/dp/secagg/combined")
    epsilon: float = Field(1.0, description="差分隐私epsilon")
    delta: float = Field(1e-5, description="差分隐私delta")
    noise_scale: float = Field(0.1, description="噪声缩放系数")
    clip_norm: float = Field(1.0, description="梯度裁剪范数")
    num_parties: int = Field(3, description="安全聚合参与方数量")
    secret_share_threshold: int = Field(2, description="秘密共享阈值")


class FederatedAggregatorConfig(BaseModel):
    """聚合器配置"""
    strategy: str = Field("weighted_avg", description="聚合策略: fedavg/weighted_avg/median/trimmed_mean/fedprox/fedopt")
    trim_ratio: float = Field(0.1, description="修剪均值比例")
    mu: float = Field(0.01, description="FedProx近端项系数")
    server_learning_rate: float = Field(1.0, description="服务器学习率")
    min_clients_per_round: int = Field(2, description="每轮最少客户端数")
    enable_outlier_detection: bool = Field(True, description="是否启用异常值检测")
