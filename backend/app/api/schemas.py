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


# ============================================================
# 告警与通知模块
# ============================================================

# ---------- 告警规则 ----------

class AlertRuleBase(BaseModel):
    """告警规则基础模型"""
    rule_name: str = Field(..., description="规则名称")
    alert_level: int = Field(..., ge=1, le=4, description="告警级别 1-4")
    node_type: str = Field("all", description="节点类型 bolt/flange/all")
    node_ids: Optional[List[str]] = Field(None, description="节点ID列表，空表示全部")
    min_confidence: float = Field(0.0, ge=0, le=1, description="最低置信度")
    silence_period: int = Field(30, ge=0, description="静默期（分钟）")
    enable_upgrade: bool = Field(True, description="是否启用自动升级")
    upgrade_minutes: int = Field(30, ge=0, description="未处理升级时间（分钟）")
    upgrade_to_level: Optional[int] = Field(None, ge=1, le=4, description="升级到的级别")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="规则描述")


class AlertRuleCreate(AlertRuleBase):
    """创建告警规则请求"""
    pass


class AlertRuleUpdate(BaseModel):
    """更新告警规则请求"""
    rule_name: Optional[str] = None
    alert_level: Optional[int] = Field(None, ge=1, le=4)
    node_type: Optional[str] = None
    node_ids: Optional[List[str]] = None
    min_confidence: Optional[float] = Field(None, ge=0, le=1)
    silence_period: Optional[int] = Field(None, ge=0)
    enable_upgrade: Optional[bool] = None
    upgrade_minutes: Optional[int] = Field(None, ge=0)
    upgrade_to_level: Optional[int] = Field(None, ge=1, le=4)
    enabled: Optional[bool] = None
    description: Optional[str] = None


class AlertRuleResponse(AlertRuleBase):
    """告警规则响应"""
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


# ---------- 告警事件 ----------

class AlertEventResponse(BaseModel):
    """告警事件响应"""
    id: int
    alert_no: str
    rule_id: Optional[int] = None
    alert_level: int
    original_level: Optional[int] = None
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    confidence: Optional[float] = None
    risk_score: Optional[float] = None
    recommendations: Optional[List[str]] = None
    status: str
    handler_id: Optional[str] = None
    handler_name: Optional[str] = None
    handle_time: Optional[datetime] = None
    handle_note: Optional[str] = None
    is_upgraded: bool = False
    upgrade_count: int = 0
    last_upgrade_time: Optional[datetime] = None
    work_order_id: Optional[int] = None
    source_prediction_id: Optional[int] = None
    silence_until: Optional[datetime] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class AlertHandleRequest(BaseModel):
    """处理告警请求"""
    action: str = Field(..., description="处理动作: acknowledge/resolve/ignore")
    handler_id: Optional[str] = Field(None, description="处理人ID")
    handler_name: Optional[str] = Field(None, description="处理人姓名")
    handle_note: Optional[str] = Field(None, description="处理备注")
    silence_minutes: Optional[int] = Field(None, ge=0, description="忽略时的静默期（分钟）")


class AlertListResponse(BaseModel):
    """告警列表响应"""
    total: int
    items: List[AlertEventResponse]


# ---------- 告警订阅 ----------

class AlertSubscriptionBase(BaseModel):
    """告警订阅基础模型"""
    subscriber_type: str = Field(..., description="订阅者类型 role/user/device")
    subscriber_id: str = Field(..., description="订阅者ID")
    subscriber_name: Optional[str] = Field(None, description="订阅者名称")
    min_alert_level: int = Field(1, ge=1, le=4, description="最低订阅级别")
    alert_levels: Optional[List[int]] = Field(None, description="订阅的告警级别列表")
    node_type: str = Field("all", description="节点类型过滤 bolt/flange/all")
    node_ids: Optional[List[str]] = Field(None, description="节点ID列表")
    notify_channels: Optional[List[str]] = Field(None, description="通知渠道列表")
    notify_targets: Optional[Dict[str, List[str]]] = Field(None, description="通知目标 {渠道: [目标]}")
    enabled: bool = Field(True, description="是否启用")


class AlertSubscriptionCreate(AlertSubscriptionBase):
    """创建订阅请求"""
    pass


class AlertSubscriptionUpdate(BaseModel):
    """更新订阅请求"""
    subscriber_type: Optional[str] = None
    subscriber_id: Optional[str] = None
    subscriber_name: Optional[str] = None
    min_alert_level: Optional[int] = Field(None, ge=1, le=4)
    alert_levels: Optional[List[int]] = None
    node_type: Optional[str] = None
    node_ids: Optional[List[str]] = None
    notify_channels: Optional[List[str]] = None
    notify_targets: Optional[Dict[str, List[str]]] = None
    enabled: Optional[bool] = None


class AlertSubscriptionResponse(AlertSubscriptionBase):
    """订阅响应"""
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


# ---------- 通知渠道 ----------

class NotificationChannelBase(BaseModel):
    """通知渠道基础模型"""
    channel_type: str = Field(..., description="渠道类型 email/sms/webhook/dingtalk/wechat")
    channel_name: Optional[str] = Field(None, description="渠道名称")
    config: Optional[Dict[str, Any]] = Field(None, description="渠道配置")
    enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否默认渠道")


class NotificationChannelCreate(NotificationChannelBase):
    """创建通知渠道请求"""
    pass


class NotificationChannelUpdate(BaseModel):
    """更新通知渠道请求"""
    channel_type: Optional[str] = None
    channel_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class NotificationChannelResponse(NotificationChannelBase):
    """通知渠道响应"""
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


# ---------- 通知日志 ----------

class NotificationLogResponse(BaseModel):
    """通知日志响应"""
    id: int
    alert_id: Optional[int] = None
    channel_type: Optional[str] = None
    subscriber_id: Optional[str] = None
    subscriber_name: Optional[str] = None
    target: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    retry_count: int = 0
    send_time: datetime

    class Config:
        from_attributes = True


# ---------- 工单 ----------

class WorkOrderBase(BaseModel):
    """工单基础模型"""
    title: str = Field(..., description="工单标题")
    description: Optional[str] = Field(None, description="工单描述")
    priority: str = Field("medium", description="优先级 low/medium/high/urgent")
    status: Optional[str] = Field("open", description="状态 open/assigned/in_progress/resolved/closed")
    node_type: Optional[str] = Field(None, description="节点类型")
    node_id: Optional[str] = Field(None, description="节点ID")
    alert_level: Optional[int] = Field(None, description="告警级别")
    risk_score: Optional[float] = Field(None, description="风险评分")
    assignee_id: Optional[str] = Field(None, description="处理人ID")
    assignee_name: Optional[str] = Field(None, description="处理人姓名")
    creator_id: Optional[str] = Field("manual", description="创建人ID")
    creator_name: Optional[str] = Field("人工创建", description="创建人姓名")
    due_time: Optional[datetime] = Field(None, description="截止时间")
    recommendations: Optional[List[str]] = Field(None, description="推荐措施")
    extra_info: Optional[Dict[str, Any]] = Field(None, description="扩展信息")


class WorkOrderCreate(WorkOrderBase):
    """创建工单请求"""
    due_hours: Optional[int] = Field(48, description="多少小时后截止，due_time未设置时生效")
    pass


class WorkOrderUpdate(BaseModel):
    """更新工单请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    due_time: Optional[datetime] = None
    recommendations: Optional[List[str]] = None
    extra_info: Optional[Dict[str, Any]] = None


class WorkOrderAssignRequest(BaseModel):
    """指派工单请求"""
    assignee_id: str = Field(..., description="处理人ID")
    assignee_name: str = Field(..., description="处理人姓名")
    assigner_id: Optional[str] = Field(None, description="指派人ID")
    assigner_name: Optional[str] = Field(None, description="指派人姓名")


class WorkOrderResolveRequest(BaseModel):
    """解决工单请求"""
    resolve_note: str = Field(..., description="解决备注")
    resolver_id: Optional[str] = Field(None, description="解决人ID")
    resolver_name: Optional[str] = Field(None, description="解决人姓名")


class WorkOrderStatusUpdateRequest(BaseModel):
    """更新工单状态请求"""
    status: str = Field(..., description="新状态")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")
    note: Optional[str] = Field(None, description="备注")


class WorkOrderResponse(WorkOrderBase):
    """工单响应"""
    id: int
    order_no: str
    alert_id: Optional[int] = None
    resolve_time: Optional[datetime] = None
    resolve_note: Optional[str] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class WorkOrderListResponse(BaseModel):
    """工单列表响应"""
    total: int
    items: List[WorkOrderResponse]


# ---------- 告警调度 ----------

class AlertUpgradeTriggerResponse(BaseModel):
    """手动触发告警升级响应"""
    upgraded_count: int
    message: str


# ============================================================
# 合规审计与模型可解释性
# ============================================================

class AuditRecordResponse(BaseModel):
    """审计记录响应"""
    id: int
    prediction_id: str
    node_type: str
    node_id: str
    input_hash: Optional[str] = None
    model_version: Optional[str] = None
    model_type: Optional[str] = None
    feature_summary: Optional[Dict[str, Any]] = None
    intermediate_results: Optional[Dict[str, Any]] = None
    final_decision: Optional[Dict[str, Any]] = None
    strategy_version: Optional[str] = None
    strategy_type: Optional[int] = None
    explainability: Optional[Dict[str, Any]] = None
    retention_years: int = 3
    expire_time: Optional[datetime] = None
    create_time: datetime

    class Config:
        from_attributes = True


class AuditListResponse(BaseModel):
    """审计记录列表响应"""
    total: int
    items: List[AuditRecordResponse]


class AuditRetentionUpdateRequest(BaseModel):
    """更新审计记录保留年限请求"""
    retention_years: int = Field(..., ge=1, le=30, description="保留年限")


class AuditCleanupResponse(BaseModel):
    """清理过期审计记录响应"""
    cleaned_count: int
    message: str


class AuditExportRequest(BaseModel):
    """审计导出请求"""
    start_time: datetime = Field(..., description="起始时间")
    end_time: datetime = Field(..., description="结束时间")
    node_type: Optional[str] = Field(None, description="节点类型过滤 bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID过滤")
    format: str = Field("csv", description="导出格式 csv/pdf")


class ExplainabilityReportResponse(BaseModel):
    """可解释性报告响应"""
    prediction_id: str
    attention_weights: Optional[Dict[str, Any]] = None
    key_timesteps: Optional[List[Dict[str, Any]]] = None
    risk_factor_decomposition: Optional[Dict[str, Any]] = None
    rule_hits: Optional[List[Dict[str, Any]]] = None
    strategy_adjustment: Optional[Dict[str, Any]] = None


# ============================================================
# 数据质量治理
# ============================================================

class RuleViolationSchema(BaseModel):
    """规则违反详情"""
    rule_type: str
    rule_name: str
    severity: str
    description: str
    violation_indices: List[int]
    violation_values: Optional[List[float]] = None
    threshold: Optional[float] = None
    actual_value: Optional[float] = None


class QualityCheckResultSchema(BaseModel):
    """质量检查结果"""
    sensor_id: str
    total_points: int
    valid_points: int
    overall_score: float
    rule_scores: Dict[str, float]
    violations: List[RuleViolationSchema]
    violation_count: int
    check_time: datetime


class QualityDimensionScoreSchema(BaseModel):
    """维度评分"""
    dimension: str
    score: float
    weight: float
    contributing_rules: List[str]


class SensorQualityScoreSchema(BaseModel):
    """传感器质量评分"""
    sensor_id: str
    overall_score: float
    overall_level: str
    dimensions: Dict[str, QualityDimensionScoreSchema]
    valid_for_training: bool
    confidence_adjustment: float
    rule_violations_count: Dict[str, int]
    calculate_time: datetime


class FilteredDataResultSchema(BaseModel):
    """过滤结果"""
    original_count: int
    filtered_count: int
    removed_indices: List[int]
    removal_reasons: Dict[int, str]
    filter_strategy: str
    confidence_multiplier: float
    adjusted_confidence: Optional[float] = None


class AnomalyClassificationSchema(BaseModel):
    """异常分类结果"""
    anomaly_id: Optional[int] = None
    sensor_id: str
    anomaly_value: float
    anomaly_type: str
    classification: str
    classification_confidence: float
    collection_subtype: Optional[str] = None
    true_anomaly_subtype: Optional[str] = None
    evidence: Dict[str, Any]
    original_time: Optional[datetime] = None


class AnomalyLinkResultSchema(BaseModel):
    """异常联动结果"""
    sensor_id: str
    total_anomalies: int
    true_anomalies: int
    collection_anomalies: int
    uncertain_anomalies: int
    mixed_anomalies: int
    classified_anomalies: List[AnomalyClassificationSchema]


class QualityEvaluationResponse(BaseModel):
    """质量评估完整响应"""
    sensor_id: str
    quality_check: QualityCheckResultSchema
    quality_score: SensorQualityScoreSchema
    filter_result: FilteredDataResultSchema
    anomaly_classification: Optional[AnomalyLinkResultSchema] = None
    evaluate_time: datetime


class ProblemSensorRankingSchema(BaseModel):
    """问题传感器排行"""
    rank: int
    sensor_id: str
    quality_score: float
    quality_level: str
    problem_types: List[str]
    violation_count: int
    anomaly_count: int
    collection_anomaly_ratio: float
    trend: str


class RepairRecommendationSchema(BaseModel):
    """修复建议"""
    sensor_id: str
    problem_type: str
    description: str
    recommendation: str
    priority: str
    estimated_effort: float
    affected_metrics: List[str]
    evidence: Dict[str, Any]


class DailyQualityReportSchema(BaseModel):
    """每日质量报告"""
    report_date: datetime
    total_sensors: int
    average_quality_score: float
    quality_distribution: Dict[str, int]
    problem_sensors: List[ProblemSensorRankingSchema]
    recommendations: List[RepairRecommendationSchema]
    anomaly_statistics: Dict[str, Any]
    quality_trend: List[Dict[str, Any]]
    summary: str
    generated_at: datetime


class DataQualityCheckRequest(BaseModel):
    """数据质量检查请求"""
    sensor_id: str = Field(..., description="传感器/螺栓ID")
    data: List[List[Any]] = Field(
        ...,
        description="时序数据，每个元素为[时间字符串, 数值]",
        min_length=1
    )
    include_anomaly_classification: bool = Field(
        True,
        description="是否包含异常分类"
    )


class DataQualityCheckBatchRequest(BaseModel):
    """批量数据质量检查请求"""
    sensors_data: Dict[str, List[List[Any]]] = Field(
        ...,
        description="传感器数据字典 {sensor_id: [[时间, 数值], ...]}"
    )


class QualityReportRequest(BaseModel):
    """生成质量报告请求"""
    report_date: Optional[datetime] = Field(None, description="报告日期，默认今日")
    sensor_ids: Optional[List[str]] = Field(None, description="传感器ID列表，默认全部")
    save_to_db: bool = Field(True, description="是否保存到数据库")


class DataQualityHistoryRequest(BaseModel):
    """获取质量历史请求"""
    sensor_id: str = Field(..., description="传感器ID")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")


class ConfidenceAdjustmentRequest(BaseModel):
    """置信度调整请求"""
    sensor_id: str = Field(..., description="传感器ID")
    original_confidence: float = Field(..., ge=0.0, le=1.0, description="原始置信度")
    data: List[List[Any]] = Field(
        ...,
        description="时序数据",
        min_length=1
    )


class ConfidenceAdjustmentResponse(BaseModel):
    """置信度调整响应"""
    sensor_id: str
    original_confidence: float
    adjusted_confidence: float
    quality_score: float
    quality_level: str
    adjustment_factor: float
    reasons: List[str]

