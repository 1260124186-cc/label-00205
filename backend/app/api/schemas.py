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


# ==================== 工单处置记录 ====================

class DisposalRecordCreate(BaseModel):
    """创建处置记录请求"""
    work_order_id: int = Field(..., description="关联工单ID")
    disposal_type: str = Field(..., description="处置类型 torque_adjustment/replacement/inspection/other")
    disposal_content: str = Field(..., description="处置内容描述")
    disposal_time: Optional[datetime] = Field(None, description="处置时间")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")
    before_value: Optional[float] = Field(None, description="处置前值")
    after_value: Optional[float] = Field(None, description="处置后值")
    materials_used: Optional[List[Dict[str, Any]]] = Field(None, description="使用材料列表")
    photos: Optional[List[str]] = Field(None, description="现场照片URL列表")
    notes: Optional[str] = Field(None, description="备注")
    extra_info: Optional[Dict[str, Any]] = Field(None, description="扩展信息")


class DisposalRecordUpdate(BaseModel):
    """更新处置记录请求"""
    disposal_type: Optional[str] = None
    disposal_content: Optional[str] = None
    disposal_time: Optional[datetime] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    materials_used: Optional[List[Dict[str, Any]]] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None


class DisposalRecordResponse(BaseModel):
    """处置记录响应"""
    id: int
    work_order_id: int
    disposal_type: Optional[str] = None
    disposal_content: Optional[str] = None
    disposal_time: Optional[datetime] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    materials_used: Optional[List[Dict[str, Any]]] = None
    photos: Optional[List[str]] = None
    notes: Optional[str] = None
    extra_info: Optional[Dict[str, Any]] = None
    create_time: datetime

    class Config:
        from_attributes = True


class DisposalRecordListResponse(BaseModel):
    """处置记录列表响应"""
    total: int
    items: List[DisposalRecordResponse]


# ==================== 工单复测数据 ====================

class RetestRecordCreate(BaseModel):
    """创建复测记录请求"""
    work_order_id: int = Field(..., description="关联工单ID")
    retest_time: Optional[datetime] = Field(None, description="复测时间")
    retester_id: Optional[str] = Field(None, description="复测人ID")
    retester_name: Optional[str] = Field(None, description="复测人姓名")
    retest_result: str = Field("pending", description="复测结果 pass/fail/pending")
    measured_value: Optional[float] = Field(None, description="复测测量值")
    data_points: Optional[List[List[Any]]] = Field(None, description="复测数据点 时序数据")
    before_risk_score: Optional[float] = Field(None, description="复测前风险评分")
    after_risk_score: Optional[float] = Field(None, description="复测后风险评分")
    status_after_retest: Optional[str] = Field(None, description="复测后状态 normal/warning/critical")
    confidence: Optional[float] = Field(None, description="复测置信度")
    retest_notes: Optional[str] = Field(None, description="复测备注")
    photos: Optional[List[str]] = Field(None, description="复测照片URL列表")
    extra_info: Optional[Dict[str, Any]] = Field(None, description="扩展信息")
    auto_repredict: Optional[bool] = Field(True, description="是否自动再预测")


class RetestRecordUpdate(BaseModel):
    """更新复测记录请求"""
    retest_time: Optional[datetime] = None
    retester_id: Optional[str] = None
    retester_name: Optional[str] = None
    retest_result: Optional[str] = None
    measured_value: Optional[float] = None
    data_points: Optional[List[List[Any]]] = None
    before_risk_score: Optional[float] = None
    after_risk_score: Optional[float] = None
    status_after_retest: Optional[str] = None
    confidence: Optional[float] = None
    retest_notes: Optional[str] = None
    photos: Optional[List[str]] = None
    extra_info: Optional[Dict[str, Any]] = None


class RetestRecordResponse(BaseModel):
    """复测记录响应"""
    id: int
    work_order_id: int
    retest_time: Optional[datetime] = None
    retester_id: Optional[str] = None
    retester_name: Optional[str] = None
    retest_result: Optional[str] = None
    measured_value: Optional[float] = None
    data_points: Optional[List[List[Any]]] = None
    before_risk_score: Optional[float] = None
    after_risk_score: Optional[float] = None
    status_after_retest: Optional[str] = None
    confidence: Optional[float] = None
    retest_notes: Optional[str] = None
    photos: Optional[List[str]] = None
    extra_info: Optional[Dict[str, Any]] = None
    create_time: datetime

    class Config:
        from_attributes = True


class RetestRecordListResponse(BaseModel):
    """复测记录列表响应"""
    total: int
    items: List[RetestRecordResponse]


# ==================== 预测对比 ====================

class PredictionCompareResponse(BaseModel):
    """预测对比响应"""
    id: int
    work_order_id: int
    retest_id: Optional[int] = None
    original_prediction_id: Optional[int] = None
    retest_prediction_id: Optional[int] = None
    original_status: Optional[str] = None
    retest_status: Optional[str] = None
    original_risk_score: Optional[float] = None
    retest_risk_score: Optional[float] = None
    original_confidence: Optional[float] = None
    retest_confidence: Optional[float] = None
    risk_change: Optional[str] = None
    risk_delta: Optional[float] = None
    status_match: Optional[bool] = None
    is_false_positive: Optional[bool] = None
    is_recurring: Optional[bool] = None
    comparison_detail: Optional[Dict[str, Any]] = None
    create_time: datetime

    class Config:
        from_attributes = True


class PredictionCompareListResponse(BaseModel):
    """预测对比列表响应"""
    total: int
    items: List[PredictionCompareResponse]


# ==================== 统计指标 ====================

class WorkOrderStatsRequest(BaseModel):
    """工单统计请求"""
    start_time: Optional[datetime] = Field(None, description="统计开始时间")
    end_time: Optional[datetime] = Field(None, description="统计结束时间")
    node_type: Optional[str] = Field(None, description="节点类型 bolt/flange")
    priority: Optional[str] = Field(None, description="优先级")


class WorkOrderStatsResponse(BaseModel):
    """工单统计响应"""
    total_work_orders: int = Field(0, description="总工单数")
    closed_work_orders: int = Field(0, description="已关闭工单数")
    open_work_orders: int = Field(0, description="待处理工单数")
    in_progress_work_orders: int = Field(0, description="处理中工单数")
    mttr_hours: Optional[float] = Field(None, description="平均修复时间 MTTR 小时")
    mttr_minutes: Optional[float] = Field(None, description="平均修复时间 MTTR 分钟")
    false_positive_rate: Optional[float] = Field(None, description="误报率 0-1")
    false_positive_count: int = Field(0, description="误报数量")
    recurrence_rate: Optional[float] = Field(None, description="重复故障率 0-1")
    recurrence_count: int = Field(0, description="重复故障数量")
    avg_resolve_hours: Optional[float] = Field(None, description="平均解决时间 小时")
    on_time_completion_rate: Optional[float] = Field(None, description="按时完成率 0-1")
    priority_distribution: Optional[Dict[str, int]] = Field(None, description="优先级分布")
    status_distribution: Optional[Dict[str, int]] = Field(None, description="状态分布")
    time_range: Optional[Dict[str, Any]] = Field(None, description="统计时间范围")


class MttrTrendPoint(BaseModel):
    """MTTR趋势点"""
    date: str
    mttr_hours: Optional[float] = None
    work_order_count: int = 0


class MttrTrendResponse(BaseModel):
    """MTTR趋势响应"""
    trend: List[MttrTrendPoint]
    overall_mttr_hours: Optional[float] = None


# ==================== CMMS/EAM 集成 ====================

class CmmsConfigCreate(BaseModel):
    """创建CMMS配置请求"""
    system_name: str = Field(..., description="系统名称")
    system_type: Optional[str] = Field(None, description="系统类型 maximo/sap_eam/infor/eam/other")
    base_url: Optional[str] = Field(None, description="系统基础URL")
    auth_type: Optional[str] = Field(None, description="认证类型 basic/api_key/oauth2/token")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    work_order_sync: Optional[bool] = Field(False, description="是否同步工单")
    work_order_webhook_url: Optional[str] = Field(None, description="工单Webhook URL")
    work_order_push_url: Optional[str] = Field(None, description="工单推送URL")
    status_mapping: Optional[Dict[str, str]] = Field(None, description="状态映射")
    priority_mapping: Optional[Dict[str, str]] = Field(None, description="优先级映射")
    field_mapping: Optional[Dict[str, Any]] = Field(None, description="字段映射")
    enabled: Optional[bool] = Field(True, description="是否启用")
    sync_direction: Optional[str] = Field("push", description="同步方向 push/pull/bidirectional")
    sync_interval: Optional[int] = Field(60, description="同步间隔 分钟")
    tenant_id: Optional[int] = Field(None, description="租户ID")
    extra_info: Optional[Dict[str, Any]] = Field(None, description="扩展信息")


class CmmsConfigUpdate(BaseModel):
    """更新CMMS配置请求"""
    system_name: Optional[str] = None
    system_type: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    work_order_sync: Optional[bool] = None
    work_order_webhook_url: Optional[str] = None
    work_order_push_url: Optional[str] = None
    status_mapping: Optional[Dict[str, str]] = None
    priority_mapping: Optional[Dict[str, str]] = None
    field_mapping: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    sync_direction: Optional[str] = None
    sync_interval: Optional[int] = None
    extra_info: Optional[Dict[str, Any]] = None


class CmmsConfigResponse(BaseModel):
    """CMMS配置响应"""
    id: int
    system_name: str
    system_type: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    work_order_sync: Optional[bool] = None
    work_order_webhook_url: Optional[str] = None
    work_order_push_url: Optional[str] = None
    status_mapping: Optional[Dict[str, str]] = None
    priority_mapping: Optional[Dict[str, str]] = None
    field_mapping: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    sync_direction: Optional[str] = None
    last_sync_time: Optional[datetime] = None
    sync_interval: Optional[int] = None
    tenant_id: Optional[int] = None
    extra_info: Optional[Dict[str, Any]] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class CmmsConfigListResponse(BaseModel):
    """CMMS配置列表响应"""
    total: int
    items: List[CmmsConfigResponse]


class CmmsSyncRequest(BaseModel):
    """CMMS同步请求"""
    config_id: int = Field(..., description="CMMS配置ID")
    sync_type: str = Field("work_order_create", description="同步类型")
    work_order_id: Optional[int] = Field(None, description="工单ID")


class CmmsSyncResponse(BaseModel):
    """CMMS同步响应"""
    success: bool
    sync_log_id: Optional[int] = None
    external_id: Optional[str] = None
    message: Optional[str] = None


class CmmsSyncLogResponse(BaseModel):
    """CMMS同步日志响应"""
    id: int
    config_id: Optional[int] = None
    sync_type: Optional[str] = None
    sync_direction: Optional[str] = None
    work_order_id: Optional[int] = None
    external_id: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    sync_time: Optional[datetime] = None
    create_time: datetime

    class Config:
        from_attributes = True


class CmmsSyncLogListResponse(BaseModel):
    """CMMS同步日志列表响应"""
    total: int
    items: List[CmmsSyncLogResponse]


class CmmsWebhookResponse(BaseModel):
    """CMMS Webhook响应"""
    success: bool
    message: str
    processed_count: Optional[int] = 0


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


# ==================== 边缘计算 SDK ====================

class EdgeModelLatestRequest(BaseModel):
    model_type: str = Field(..., description="模型类型 bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID")
    edge_device_id: Optional[str] = Field(None, description="边缘设备ID")

class EdgeModelLatestResponse(BaseModel):
    version: str
    model_type: str
    node_id: Optional[str] = None
    download_url: str
    file_hash: str
    file_size: int
    created_at: str
    metrics: Optional[Dict[str, float]] = None

class EdgeModelDownloadResponse(BaseModel):
    version: str
    model_type: str
    node_id: Optional[str] = None
    model_format: str
    download_url: str
    file_hash: str
    file_size: int
    preprocessing_included: bool = True
    signature_included: bool = True

class EdgePredictionUploadRequest(BaseModel):
    device_id: str = Field(..., description="边缘设备ID")
    predictions: List[Dict[str, Any]] = Field(..., description="预测结果列表")

class EdgePredictionUploadResponse(BaseModel):
    device_id: str
    received_count: int
    status: str
    message: str

class EdgeModelExportRequest(BaseModel):
    model_type: str = Field(..., description="模型类型 bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID")
    export_format: str = Field("onnx", description="导出格式 onnx/torchscript")
    version: Optional[str] = Field(None, description="指定版本，None则使用最新")

class EdgeModelExportResponse(BaseModel):
    model_type: str
    node_id: Optional[str] = None
    version: str
    export_format: str
    package_url: str
    file_hash: str
    file_size: int
    includes_preprocessing: bool = True
    includes_signature: bool = True
    exported_at: str

class EdgeDeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="边缘设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    device_type: Optional[str] = Field(None, description="设备类型")
    location: Optional[str] = Field(None, description="设备位置")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="设备能力")

class EdgeDeviceRegisterResponse(BaseModel):
    device_id: str
    status: str
    message: str
    registered_at: str

class EdgeDeviceHeartbeatRequest(BaseModel):
    device_id: str
    model_version: Optional[str] = None
    cache_size: int = 0
    unsynced_count: int = 0

class EdgeDeviceHeartbeatResponse(BaseModel):
    device_id: str
    latest_model_version: Optional[str] = None
    force_sync: bool = False
    server_time: str


# ============================================================
# 多租户与组织架构
# ============================================================

class TenantCreateRequest(BaseModel):
    tenant_code: str = Field(..., min_length=2, max_length=64, description="租户编码")
    tenant_name: str = Field(..., min_length=1, max_length=200, description="租户名称")
    contact_email: Optional[str] = Field(None, description="联系邮箱")
    contact_phone: Optional[str] = Field(None, description="联系电话")
    expire_time: Optional[datetime] = Field(None, description="到期时间")


class TenantUpdateRequest(BaseModel):
    tenant_name: Optional[str] = Field(None, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = Field(None, description="状态 active/suspended/deleted")
    expire_time: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    id: int
    tenant_code: str
    tenant_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    status: str
    settings: Optional[Dict[str, Any]] = None
    expire_time: Optional[datetime] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    total: int
    items: List[TenantResponse]


class OrgNodeCreateRequest(BaseModel):
    tenant_id: int = Field(..., description="所属租户ID")
    parent_id: Optional[int] = Field(None, description="父节点ID, 空表示根节点")
    node_code: Optional[str] = Field(None, max_length=100, description="节点编码")
    node_name: str = Field(..., min_length=1, max_length=200, description="节点名称")
    node_type: str = Field(..., description="节点类型 group/factory/unit/flange/bolt")
    sort_order: int = Field(0, description="排序序号")
    extra_info: Optional[Dict[str, Any]] = Field(None, description="扩展信息")


class OrgNodeUpdateRequest(BaseModel):
    node_name: Optional[str] = Field(None, max_length=200)
    node_code: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    extra_info: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, description="状态 active/inactive")


class OrgNodeResponse(BaseModel):
    id: int
    tenant_id: int
    parent_id: Optional[int] = None
    node_code: Optional[str] = None
    node_name: str
    node_type: str
    path: Optional[str] = None
    level: int
    sort_order: int
    extra_info: Optional[Dict[str, Any]] = None
    status: str
    create_time: datetime
    update_time: datetime
    children: Optional[List["OrgNodeResponse"]] = None

    class Config:
        from_attributes = True


class OrgTreeResponse(BaseModel):
    tenant_id: int
    nodes: List[OrgNodeResponse]


class QuotaUpdateRequest(BaseModel):
    max_models: Optional[int] = Field(None, ge=0)
    max_api_calls_per_day: Optional[int] = Field(None, ge=0)
    max_storage_mb: Optional[int] = Field(None, ge=0)
    max_users: Optional[int] = Field(None, ge=0)
    max_org_nodes: Optional[int] = Field(None, ge=0)


class QuotaResponse(BaseModel):
    tenant_id: int
    max_models: int
    max_api_calls_per_day: int
    max_storage_mb: int
    max_users: int
    max_org_nodes: int
    current_model_count: int
    current_api_calls_today: int
    current_storage_mb: float
    current_user_count: int
    current_org_node_count: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class TenantUserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=100, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: Optional[str] = Field(None, max_length=200, description="显示名称")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    role: str = Field("viewer", description="角色 tenant_admin/admin/operator/viewer")
    org_node_id: Optional[int] = Field(None, description="关联组织节点ID")


class TenantUserUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = Field(None, description="角色 tenant_admin/admin/operator/viewer")
    org_node_id: Optional[int] = None
    status: Optional[str] = Field(None, description="状态 active/disabled")


class TenantUserPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class TenantUserResponse(BaseModel):
    id: int
    tenant_id: int
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    org_node_id: Optional[int] = None
    status: str
    last_login_time: Optional[datetime] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class TenantUserListResponse(BaseModel):
    total: int
    items: List[TenantUserResponse]


class TenantAPIKeyCreateRequest(BaseModel):
    key_name: Optional[str] = Field(None, max_length=200, description="密钥名称")
    permissions: Optional[List[str]] = Field(None, description="权限列表")
    rate_limit: int = Field(1000, ge=1, description="速率限制 每分钟")
    user_id: Optional[int] = Field(None, description="关联用户ID")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class TenantAPIKeyUpdateRequest(BaseModel):
    key_name: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1)
    status: Optional[str] = Field(None, description="状态 active/revoked")
    expires_at: Optional[datetime] = None


class TenantAPIKeyResponse(BaseModel):
    id: int
    tenant_id: int
    api_key: str
    key_name: Optional[str] = None
    permissions: Optional[List[str]] = None
    rate_limit: int
    user_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    status: str
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class TenantAPIKeyCreateResponse(TenantAPIKeyResponse):
    api_key_plain: Optional[str] = Field(None, description="明文密钥, 仅创建时返回一次")


class TenantLoginRequest(BaseModel):
    tenant_code: str = Field(..., description="租户编码")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TenantLoginResponse(BaseModel):
    token: str
    tenant_id: int
    user_id: int
    username: str
    role: str
    expires_at: datetime


# ============================================================
# 知识库与案例推理 (CBR)
# ============================================================

# ---------- 工况信息 ----------

class WorkingConditionSchema(BaseModel):
    """工况信息"""
    temperature: Optional[float] = Field(None, description='环境温度')
    pressure: Optional[float] = Field(None, description='系统压力')
    humidity: Optional[float] = Field(None, description='环境湿度')
    vibration: Optional[float] = Field(None, description='振动水平')
    load_condition: Optional[str] = Field(None, description='负载状况 light/medium/heavy/overload')
    operating_hours: Optional[float] = Field(None, description='运行时长（小时）')
    maintenance_cycle: Optional[str] = Field(None, description='维护周期')
    last_maintenance_date: Optional[datetime] = Field(None, description='上次维护日期')
    equipment_age: Optional[float] = Field(None, description='设备使用年限')
    extra: Optional[Dict[str, Any]] = Field(None, description='其他工况参数')


# ---------- 处置方案 ----------

class TreatmentStepSchema(BaseModel):
    """处置步骤"""
    step_order: int = Field(..., description='步骤序号')
    action: str = Field(..., description='处置动作')
    description: Optional[str] = Field(None, description='详细描述')
    tools: Optional[List[str]] = Field(None, description='所需工具')
    duration_minutes: Optional[int] = Field(None, description='预计耗时（分钟）')
    safety_notes: Optional[str] = Field(None, description='安全注意事项')


class TreatmentPlanSchema(BaseModel):
    """处置方案"""
    plan_name: Optional[str] = Field(None, description='方案名称')
    steps: List[TreatmentStepSchema] = Field(default_factory=list, description='处置步骤列表')
    materials: Optional[List[str]] = Field(None, description='所需材料')
    estimated_cost: Optional[float] = Field(None, description='预估成本')
    difficulty_level: Optional[str] = Field(None, description='难度等级 easy/medium/hard')
    personnel_required: Optional[str] = Field(None, description='所需人员')


# ---------- 效果评估 ----------

class EffectEvaluationSchema(BaseModel):
    """效果评估"""
    overall_rating: Optional[str] = Field(None, description='整体评价 excellent/good/fair/poor')
    effectiveness_score: Optional[float] = Field(None, ge=0, le=100, description='效果评分 0-100')
    fault_resolved: Optional[bool] = Field(None, description='故障是否解决')
    recurrence_within_days: Optional[int] = Field(None, description='多少天内复发')
    actual_cost: Optional[float] = Field(None, description='实际成本')
    actual_duration_minutes: Optional[int] = Field(None, description='实际耗时（分钟）')
    side_effects: Optional[str] = Field(None, description='副作用/不良影响')
    improvement_metrics: Optional[Dict[str, Any]] = Field(None, description='改进指标')
    notes: Optional[str] = Field(None, description='备注')


# ---------- 案例录入 ----------

class KnowledgeCaseCreateRequest(BaseModel):
    """创建案例请求"""
    case_title: str = Field(..., description='案例标题', min_length=1, max_length=500)
    node_type: Optional[str] = Field(None, description='节点类型 bolt/flange')
    node_id: Optional[str] = Field(None, description='节点ID')
    fault_type: Optional[str] = Field(None, description='故障类型')
    fault_level: Optional[int] = Field(None, ge=1, le=4, description='故障级别 1-4')
    working_condition: Optional[WorkingConditionSchema] = Field(None, description='工况信息')
    sensor_data: Optional[List[List[Any]]] = Field(None, description='传感器时序数据 [[时间, 数值], ...]')
    sensor_features: Optional[Dict[str, float]] = Field(None, description='传感器特征 (58维特征名值对)')
    diagnosis: Optional[str] = Field(None, description='诊断结论')
    root_cause: Optional[str] = Field(None, description='根本原因分析')
    treatment_plan: Optional[TreatmentPlanSchema] = Field(None, description='处置方案')
    effect_evaluation: Optional[EffectEvaluationSchema] = Field(None, description='效果评估')
    source_alert_id: Optional[int] = Field(None, description='来源告警ID')
    source_prediction_id: Optional[int] = Field(None, description='来源预测记录ID')
    tags: Optional[List[str]] = Field(None, description='标签列表')
    creator_id: Optional[str] = Field(None, description='创建人ID')
    creator_name: Optional[str] = Field(None, description='创建人姓名')
    tenant_id: Optional[int] = Field(None, description='租户ID')
    submit_for_review: bool = Field(False, description='是否提交审核')


class KnowledgeCaseUpdateRequest(BaseModel):
    """更新案例请求"""
    case_title: Optional[str] = Field(None, description='案例标题')
    fault_type: Optional[str] = Field(None, description='故障类型')
    fault_level: Optional[int] = Field(None, ge=1, le=4, description='故障级别 1-4')
    working_condition: Optional[WorkingConditionSchema] = Field(None, description='工况信息')
    sensor_data: Optional[List[List[Any]]] = Field(None, description='传感器时序数据')
    sensor_features: Optional[Dict[str, float]] = Field(None, description='传感器特征')
    diagnosis: Optional[str] = Field(None, description='诊断结论')
    root_cause: Optional[str] = Field(None, description='根本原因分析')
    treatment_plan: Optional[TreatmentPlanSchema] = Field(None, description='处置方案')
    effect_evaluation: Optional[EffectEvaluationSchema] = Field(None, description='效果评估')
    tags: Optional[List[str]] = Field(None, description='标签列表')
    change_summary: Optional[str] = Field(None, description='变更说明')
    submit_for_review: bool = Field(False, description='是否提交审核')
    operator_id: Optional[str] = Field(None, description='操作人ID')
    operator_name: Optional[str] = Field(None, description='操作人姓名')


# ---------- 案例响应 ----------

class KnowledgeCaseResponse(BaseModel):
    """案例响应"""
    id: int
    case_no: str
    case_title: str
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    fault_type: Optional[str] = None
    fault_level: Optional[int] = None
    working_condition: Optional[Dict[str, Any]] = None
    sensor_features: Optional[Dict[str, Any]] = None
    diagnosis: Optional[str] = None
    root_cause: Optional[str] = None
    treatment_plan: Optional[Dict[str, Any]] = None
    effect_evaluation: Optional[Dict[str, Any]] = None
    effectiveness_score: Optional[float] = None
    status: str
    version: int
    tenant_id: Optional[int] = None
    creator_id: Optional[str] = None
    creator_name: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    review_time: Optional[datetime] = None
    review_comment: Optional[str] = None
    source_alert_id: Optional[int] = None
    source_prediction_id: Optional[int] = None
    tags: Optional[List[str]] = None
    similarity_score: Optional[float] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class KnowledgeCaseListResponse(BaseModel):
    """案例列表响应"""
    total: int
    items: List[KnowledgeCaseResponse]


# ---------- 审核 ----------

class CaseReviewRequest(BaseModel):
    """案例审核请求"""
    review_result: str = Field(..., description='审核结果 approved/rejected/revision_required')
    review_comment: Optional[str] = Field(None, description='审核意见')
    reviewer_id: Optional[str] = Field(None, description='审核人ID')
    reviewer_name: Optional[str] = Field(None, description='审核人姓名')
    review_level: int = Field(1, ge=1, le=3, description='审核级别 1-3')


class CaseReviewResponse(BaseModel):
    """审核记录响应"""
    id: int
    case_id: int
    version: int
    review_level: int
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    review_result: str
    review_comment: Optional[str] = None
    create_time: datetime

    class Config:
        from_attributes = True


# ---------- 版本管理 ----------

class CaseVersionResponse(BaseModel):
    """案例版本响应"""
    id: int
    case_id: int
    version: int
    case_title: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[Dict[str, Any]] = None
    effect_evaluation: Optional[Dict[str, Any]] = None
    effectiveness_score: Optional[float] = None
    change_summary: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    create_time: datetime

    class Config:
        from_attributes = True


class CaseVersionCompareResponse(BaseModel):
    """版本对比响应"""
    case_id: int
    version_from: int
    version_to: int
    changes: Dict[str, Any]


# ---------- 相似度检索 ----------

class CaseSimilaritySearchRequest(BaseModel):
    """案例相似度检索请求"""
    node_type: Optional[str] = Field(None, description='节点类型 bolt/flange')
    node_id: Optional[str] = Field(None, description='节点ID')
    fault_type: Optional[str] = Field(None, description='故障类型')
    fault_level: Optional[int] = Field(None, ge=1, le=4, description='故障级别')
    sensor_data: Optional[List[List[Any]]] = Field(None, description='传感器时序数据')
    sensor_features: Optional[Dict[str, float]] = Field(None, description='传感器特征')
    feature_vector: Optional[List[float]] = Field(None, description='特征向量')
    tags: Optional[List[str]] = Field(None, description='标签过滤')
    top_k: int = Field(5, ge=1, le=50, description='返回Top-K相似案例')
    min_similarity: float = Field(0.0, ge=0, le=1, description='最低相似度阈值')
    only_approved: bool = Field(True, description='只返回已审核通过的案例')
    tenant_id: Optional[int] = Field(None, description='租户ID过滤')


class CaseSimilarityResult(BaseModel):
    """相似度检索结果"""
    case: KnowledgeCaseResponse
    similarity_score: float
    matching_features: List[str]


class CaseSimilaritySearchResponse(BaseModel):
    """相似度检索响应"""
    total: int
    results: List[CaseSimilarityResult]


# ---------- 推荐措施与RAG ----------

class CaseRecommendationResponse(BaseModel):
    """案例推荐响应（用于推荐措施和RAG上下文）"""
    top_k: int
    total_matched: int
    cases: List[KnowledgeCaseResponse]
    aggregated_recommendations: List[str]
    rag_context: str
    confidence_score: float


# ============================================================
# 数字孪生与健康度评分模块
# ============================================================

# ---------- 健康度评分基础模型 ----------

class HealthIndexFactorSchema(BaseModel):
    """健康度因子详情"""
    factor_name: str = Field(..., description='因子名称')
    factor_code: str = Field(..., description='因子代码')
    score: float = Field(..., ge=0, le=100, description='因子得分 0-100')
    weight: float = Field(..., ge=0, le=1, description='因子权重')
    contribution: float = Field(..., description='对总健康度的贡献')
    description: Optional[str] = Field(None, description='因子描述')


class HealthIndexDetailSchema(BaseModel):
    """健康度指数详情"""
    hi_score: float = Field(..., ge=0, le=100, description='综合健康度指数 0-100')
    hi_level: str = Field(..., description='健康等级 excellent/good/fair/poor/critical')
    factors: List[HealthIndexFactorSchema] = Field(..., description='各因子得分详情')
    preload_stability_score: float = Field(..., ge=0, le=100, description='预紧力稳定性得分')
    alert_frequency_score: float = Field(..., ge=0, le=100, description='预警频率得分')
    fault_history_score: float = Field(..., ge=0, le=100, description='故障历史得分')
    environmental_stress_score: float = Field(..., ge=0, le=100, description='环境应力得分')
    service_age_score: float = Field(..., ge=0, le=100, description='使用年限得分')
    trend: Optional[str] = Field(None, description='健康趋势 improving/stable/declining')
    trend_rate: Optional[float] = Field(None, description='趋势变化率')
    calculate_time: datetime


class BoltHealthIndexSchema(HealthIndexDetailSchema):
    """螺栓健康度指数"""
    bolt_id: str
    bolt_name: Optional[str] = None
    current_preload: Optional[float] = None
    nominal_preload: Optional[float] = None
    preload_deviation: Optional[float] = None
    last_maintenance_date: Optional[datetime] = None


class FlangeHealthIndexSchema(BaseModel):
    """法兰面健康度指数（聚合）"""
    flange_id: str
    flange_name: Optional[str] = None
    hi_score: float = Field(..., ge=0, le=100, description='法兰面综合健康度')
    hi_level: str = Field(..., description='健康等级')
    worst_bolt_hi: float = Field(..., description='最差螺栓健康度')
    worst_bolt_id: str = Field(..., description='最差螺栓ID')
    average_bolt_hi: float = Field(..., description='平均螺栓健康度')
    median_bolt_hi: float = Field(..., description='螺栓健康度中位数')
    degradation_rate: float = Field(..., description='劣化速率（HI/天）')
    bolt_count: int = Field(..., description='螺栓总数')
    healthy_bolt_count: int = Field(..., description='健康螺栓数(HI>=70)')
    warning_bolt_count: int = Field(..., description='预警螺栓数(50<=HI<70)')
    critical_bolt_count: int = Field(..., description='危险螺栓数(HI<50)')
    bolts_health: List[BoltHealthIndexSchema] = Field(..., description='各螺栓健康度详情')
    trend: Optional[str] = None
    calculate_time: datetime


class ProductionLineHealthRollupSchema(BaseModel):
    """产线/装置级健康度汇总报表"""
    line_id: str
    line_name: str
    line_type: str = Field(..., description='产线类型 production_line/device/unit')
    overall_hi: float = Field(..., ge=0, le=100, description='整体健康度')
    overall_level: str = Field(..., description='整体健康等级')
    total_flange_count: int = Field(..., description='法兰面总数')
    total_bolt_count: int = Field(..., description='螺栓总数')
    healthy_flange_count: int = Field(..., description='健康法兰面数')
    warning_flange_count: int = Field(..., description='预警法兰面数')
    critical_flange_count: int = Field(..., description='危险法兰面数')
    healthy_bolt_count: int = Field(..., description='健康螺栓数')
    warning_bolt_count: int = Field(..., description='预警螺栓数')
    critical_bolt_count: int = Field(..., description='危险螺栓数')
    worst_flange_hi: float = Field(..., description='最差法兰面健康度')
    worst_flange_id: str = Field(..., description='最差法兰面ID')
    average_degradation_rate: float = Field(..., description='平均劣化速率')
    flanges_health: List[FlangeHealthIndexSchema] = Field(..., description='各法兰面健康度')
    risk_summary: Dict[str, Any] = Field(..., description='风险汇总')
    maintenance_priorities: List[Dict[str, Any]] = Field(..., description='维护优先级排序')
    report_date: datetime
    generate_time: datetime


# ---------- RUL 预测模型 ----------

class RULPredictionPointSchema(BaseModel):
    """RUL预测点"""
    date: datetime
    predicted_hi: float
    lower_bound: float
    upper_bound: float


class RULPredictionSchema(BaseModel):
    """剩余使用寿命预测"""
    node_id: str
    node_type: str = Field(..., description='节点类型 bolt/flange')
    current_hi: float
    rul_days: float = Field(..., ge=0, description='预测剩余使用寿命（天）')
    rul_lower_bound: float = Field(..., description='RUL下限（天）')
    rul_upper_bound: float = Field(..., description='RUL上限（天）')
    rul_confidence: float = Field(..., ge=0, le=1, description='RUL预测置信度')
    failure_threshold: float = Field(default=30, description='故障阈值 HI')
    warning_threshold: float = Field(default=50, description='预警阈值 HI')
    days_to_warning: Optional[float] = Field(None, description='距离预警的天数')
    historical_hi: List[Dict[str, Any]] = Field(..., description='历史HI序列')
    forecast_series: List[RULPredictionPointSchema] = Field(..., description='预测序列')
    degradation_model: str = Field(..., description='劣化模型类型 linear/exponential/polynomial')
    model_params: Dict[str, Any] = Field(..., description='模型参数')
    prediction_date: datetime


# ---------- 劣化曲线模型 ----------

class DegradationCurvePointSchema(BaseModel):
    """劣化曲线点"""
    time_point: datetime
    hi_value: float
    hi_lower: Optional[float] = None
    hi_upper: Optional[float] = None
    is_prediction: bool = Field(default=False, description='是否为预测值')


class DegradationCurveSchema(BaseModel):
    """劣化曲线"""
    node_id: str
    node_type: str
    curve_points: List[DegradationCurvePointSchema]
    degradation_rate: float
    acceleration_rate: Optional[float] = None
    model_type: str
    r_squared: Optional[float] = None


# ---------- 请求模型 ----------

class HealthIndexCalculateRequest(BaseModel):
    """健康度计算请求"""
    node_id: str = Field(..., description='节点ID')
    node_type: str = Field(..., description='节点类型 bolt/flange/line')
    data: Optional[List[List[Any]]] = Field(None, description='预紧力时序数据 [[时间, 预紧力], ...]')
    working_condition: Optional[WorkingConditionSchema] = Field(None, description='工况信息')
    include_history: bool = Field(default=True, description='是否包含历史数据')
    save_to_db: bool = Field(default=True, description='是否保存到数据库')


class HealthIndexBatchCalculateRequest(BaseModel):
    """批量健康度计算请求"""
    nodes: List[Dict[str, Any]] = Field(..., description='节点列表 [{node_id, node_type, data}, ...]')
    working_condition: Optional[WorkingConditionSchema] = None
    save_to_db: bool = True


class HealthIndexHistoryRequest(BaseModel):
    """健康度历史查询请求"""
    node_id: str = Field(..., description='节点ID')
    node_type: str = Field(..., description='节点类型 bolt/flange/line')
    start_time: Optional[datetime] = Field(None, description='开始时间')
    end_time: Optional[datetime] = Field(None, description='结束时间')
    limit: int = Field(default=100, ge=1, le=1000, description='返回数量限制')


class RULPredictionRequest(BaseModel):
    """RUL预测请求"""
    node_id: str = Field(..., description='节点ID')
    node_type: str = Field(..., description='节点类型 bolt/flange')
    forecast_days: int = Field(default=180, ge=30, le=730, description='预测天数')
    failure_threshold: float = Field(default=30, ge=0, le=100, description='故障阈值 HI')
    warning_threshold: float = Field(default=50, ge=0, le=100, description='预警阈值 HI')
    model_type: Optional[str] = Field(None, description='劣化模型类型，None则自动选择')
    use_history_days: int = Field(default=90, ge=7, le=365, description='使用多少天历史数据')


class HealthRollupRequest(BaseModel):
    """健康度汇总报表请求"""
    line_id: str = Field(..., description='产线/装置ID')
    line_name: Optional[str] = None
    line_type: str = Field(default='production_line', description='产线类型')
    report_date: Optional[datetime] = Field(None, description='报告日期，默认今日')
    include_details: bool = Field(default=True, description='是否包含详细数据')


# ---------- 响应模型 ----------

class HealthIndexResponse(BaseModel):
    """健康度计算响应"""
    node_id: str
    node_type: str
    health_data: HealthIndexDetailSchema
    saved: bool
    calculate_time: datetime


class HealthIndexBatchResponse(BaseModel):
    """批量健康度计算响应"""
    total_count: int
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]
    calculate_time: datetime


class HealthIndexHistoryResponse(BaseModel):
    """健康度历史查询响应"""
    node_id: str
    node_type: str
    total: int
    history: List[Dict[str, Any]]
    trend_analysis: Optional[Dict[str, Any]] = None


class RULPredictionResponse(BaseModel):
    """RUL预测响应"""
    node_id: str
    node_type: str
    rul_data: RULPredictionSchema
    calculate_time: datetime


class HealthRollupResponse(BaseModel):
    """健康度汇总报表响应"""
    report_id: Optional[int] = None
    rollup_data: ProductionLineHealthRollupSchema
    saved: bool


# ==================== 流式预测 ====================

# ---------- 请求模型 ----------

class StreamDataIngestRequest(BaseModel):
    """
    流式数据注入请求

    支持单条或微批次数据注入
    """
    node_type: str = Field(..., description="节点类型 bolt/flange")
    node_id: str = Field(..., description="节点ID")
    value: Optional[float] = Field(None, description="单条预紧力值")
    timestamp: Optional[str] = Field(None, description="单条时间戳")
    values: Optional[List[float]] = Field(None, description="批量预紧力值列表")
    timestamps: Optional[List[str]] = Field(None, description="批量时间戳列表")
    data: Optional[List[List[Any]]] = Field(
        None,
        description="时序数据 [[时间, 预紧力], ...]"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="元数据"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "node_type": "bolt",
                "node_id": "B001",
                "value": 400.5,
                "timestamp": "2025-06-14T10:00:00",
                "metadata": {"source": "sensor_01"}
            }
        }


class StreamBatchIngestRequest(BaseModel):
    """
    批量流式数据注入请求
    """
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="消息列表，每个消息包含 node_type, node_id, value/timestamp 或 values/timestamps"
    )


class StreamModeSwitchRequest(BaseModel):
    """
    流式预测模式切换请求
    """
    mode: str = Field(
        ...,
        description="预测模式: batch 或 stream"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "stream"
            }
        }


class StreamConfigUpdateRequest(BaseModel):
    """
    流式预测配置更新请求
    """
    window_size: Optional[int] = Field(None, description="窗口大小", ge=10, le=1000)
    max_concurrent_streams: Optional[int] = Field(
        None, description="最大并发流数", ge=1, le=10000
    )
    rate_per_stream: Optional[float] = Field(
        None, description="每个流的速率限制（每秒）", ge=0.1, le=1000.0
    )


# ---------- 响应模型 ----------

class StreamDataIngestResponse(BaseModel):
    """
    流式数据注入响应
    """
    success: bool
    message: str
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    window_current_size: Optional[int] = None
    window_is_full: Optional[bool] = None
    accepted: bool = True


class StreamBatchIngestResponse(BaseModel):
    """
    批量流式数据注入响应
    """
    success: bool
    total_count: int
    accepted_count: int
    rejected_count: int
    messages: List[Dict[str, Any]] = []


class StreamWindowStatusResponse(BaseModel):
    """
    流式窗口状态响应
    """
    bolt_id: str
    window_size: int
    current_size: int
    is_full: bool
    last_updated: Optional[float] = None
    last_prediction_status: Optional[int] = None
    prediction_count: Optional[int] = None
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None


class StreamEngineStatusResponse(BaseModel):
    """
    流式预测引擎状态响应
    """
    is_running: bool
    mode: str
    active_streams: int
    total_predictions: int
    status_changes: int
    window_manager: Dict[str, Any]
    backpressure: Dict[str, Any]
    events: Dict[str, Any]
    adapters: List[Dict[str, Any]]


class StreamModeSwitchResponse(BaseModel):
    """
    流式预测模式切换响应
    """
    success: bool
    current_mode: str
    message: str


class StreamConfigResponse(BaseModel):
    """
    流式预测配置响应
    """
    success: bool
    config: Dict[str, Any]
    message: str


# ---------- 流事件模型 ----------

class StreamEventSchema(BaseModel):
    """
    流事件数据结构
    """
    event_id: str
    event_type: str
    node_type: str
    node_id: str
    timestamp: str
    data: Dict[str, Any] = {}
    source: str = "stream"
    metadata: Dict[str, Any] = {}


# ============================================================
# 模型管理模块
# ============================================================

class EpochMetricsSchema(BaseModel):
    """Epoch指标"""
    epoch: int
    train_loss: float
    val_loss: Optional[float] = None
    train_acc: Optional[float] = None
    val_acc: Optional[float] = None
    learning_rate: Optional[float] = None
    duration_seconds: float = 0
    timestamp: str


class TrainingSessionSchema(BaseModel):
    """训练会话信息"""
    session_id: str
    model_id: str
    model_type: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_epochs: int = 0
    current_epoch: int = 0
    best_metrics: Dict[str, float] = Field(default_factory=dict)
    metrics_history: List[EpochMetricsSchema] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ModelVersionSchema(BaseModel):
    """模型版本信息"""
    version: str
    model_id: str
    model_type: str
    created_at: datetime
    file_path: str
    file_hash: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False
    description: str = ""


class ModelVersionListResponse(BaseModel):
    """模型版本列表响应"""
    model_id: str
    model_type: str
    versions: List[ModelVersionSchema]


class ModelVersionActivateRequest(BaseModel):
    """激活/回滚模型版本请求"""
    version: str = Field(..., description="目标版本号")


class ModelVersionCompareRequest(BaseModel):
    """模型版本对比请求"""
    version1: str
    version2: str


class ModelVersionCompareResponse(BaseModel):
    """模型版本对比响应"""
    model_id: str
    version1: str
    version2: str
    metrics_comparison: Dict[str, Any]
    config_diff: Dict[str, Any]


class TrainingSessionListResponse(BaseModel):
    """训练会话列表响应"""
    total: int
    items: List[TrainingSessionSchema]


class TrainingStatusResponse(BaseModel):
    """训练状态响应"""
    is_training: bool
    current_session: Optional[TrainingSessionSchema] = None
    recent_sessions: List[TrainingSessionSchema] = Field(default_factory=list)
