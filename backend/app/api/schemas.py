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

class HealthComponentStatus(BaseModel):
    """组件健康状态"""
    status: str
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str
    timestamp: datetime
    components: Optional[Dict[str, HealthComponentStatus]] = None


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


class FaultPatternSchema(BaseModel):
    """故障模式特征"""
    trend_slope: float = Field(..., description="趋势斜率")
    volatility: float = Field(..., description="波动率")
    sudden_changes: int = Field(..., description="骤降/突变点数量")
    min_value: float = Field(..., description="最小值")
    max_value: float = Field(..., description="最大值")
    mean_value: float = Field(..., description="平均值")


class FaultDetailSchema(BaseModel):
    """故障类型细分详情"""
    fault_type: str = Field(..., description="故障类型: loosening/overload/fracture/fatigue/corrosion")
    fault_confidence: float = Field(..., description="故障分类置信度")
    fault_name: str = Field(..., description="故障类型中文名")
    severity: int = Field(..., description="严重程度 1-10")
    evidence: List[str] = Field(default_factory=list, description="判定依据")
    recommendations: List[str] = Field(default_factory=list, description="故障类型差异化推荐措施")
    pattern: Optional[FaultPatternSchema] = Field(None, description="故障模式特征证据")


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
        model_version: 模型版本号
        shadow_version: Shadow模式版本号（如有）
        shadow_result: Shadow模式预测结果（如有）
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
    model_version: Optional[str] = Field(None, description="模型版本号")
    shadow_version: Optional[str] = Field(None, description="Shadow模式版本号")
    shadow_result: Optional[Dict[str, Any]] = Field(None, description="Shadow模式预测结果")
    fault_detail: Optional[FaultDetailSchema] = Field(None, description="故障类型细分详情")
    prediction_source: Optional[str] = Field(None, description="预测来源: lstm / ensemble / rule")
    ensemble: Optional[Dict[str, Any]] = Field(None, description="Ensemble集成学习详情（触发时返回）")


class EnsemblePredictorResultSchema(BaseModel):
    """
    单个预测器的结果"""
    predictor_name: str
    prediction: int
    status: str
    confidence: float
    probs: Optional[List[float]] = None
    weight: Optional[float] = None


class BoltEnsemblePredictionResponse(BaseModel):
    """
    螺栓集成学习预测调试响应

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
        performance_history: 历史表现记录
    """
    bolt_id: str
    prediction_source: str
    ensemble_method: str
    final_status: str
    final_status_code: int
    final_confidence: float
    final_probs: Optional[List[float]] = None
    weights: Dict[str, float]
    individual_results: List[Dict[str, Any]]
    individual_probs: Dict[str, Optional[List[float]]]
    model_version: str
    duration_ms: float
    ema_accuracy: Dict[str, float]
    performance_history: Dict[str, List[float]]


class BoltEnsemblePredictionRequest(BaseModel):
    """
    螺栓集成学习预测调试请求
    """
    bolt_id: str = Field(..., description="螺栓唯一标识")
    data: List[float] = Field(..., description="预紧力时序数据")
    version: Optional[str] = Field(None, description="模型版本号")
    method: Optional[str] = Field(None, description="投票策略: hard / soft / weighted")
    weights: Optional[Dict[str, float]] = Field(None, description="自定义权重")

    class Config:
        json_schema_extra = {
            "example": {
                "bolt_id": "B001",
                "data": [605.2, 603.1, 600.8, 598.5, 595.3, 590.1, 585.7],
                "method": "weighted",
                "weights": {"lstm": 0.5, "rule": 0.3, "statistical": 0.2}
            }
        }


# ==================== 多变量/多传感器预测 ====================

class MultivariateChannelSchema(BaseModel):
    """
    单通道时序元数据

    Attributes:
        name: 通道名称（如 preload / temperature / humidity / vibration / torque / pressure）
        unit: 物理单位（可选）
        description: 中文描述（可选）
    """
    name: str = Field(..., description="通道名称: preload/temperature/humidity/vibration/torque/pressure 或自定义")
    unit: Optional[str] = Field(None, description="物理单位, 如 kN / °C / % / g / N·m / MPa")
    description: Optional[str] = Field(None, description="通道中文描述")


class DataQualityInfo(BaseModel):
    """
    数据质量评估结果

    Attributes:
        level: 数据质量等级 full=完整, partial=部分缺失, degraded=降级单变量
        complete_ratio: 完整数据占比 (0-1)
        missing_channels: 被丢弃/降级时缺失的通道列表
        interpolation_count: 插值填充的总数据点数
        interpolation_flags: 可选，每个时间点每通道的插值标记（1=插值 0=原始）
        degradation_applied: 是否触发了降级策略
    """
    level: str = Field("full", description="数据质量等级: full / partial / degraded")
    complete_ratio: float = Field(1.0, description="完整数据占比 0-1")
    missing_channels: List[str] = Field(default_factory=list, description="缺失或降级丢弃的通道列表")
    interpolation_count: int = Field(0, description="插值填充的总点数")
    degradation_applied: bool = Field(False, description="是否因缺失严重触发了单变量降级")
    actual_channels_used: List[str] = Field(default_factory=list, description="实际参与模型计算的通道")


class TemperatureCompensationInfo(BaseModel):
    """
    温度耦合补偿信息

    Attributes:
        applied: 是否执行了温度补偿
        temperature_coefficient: 估计的温度系数 α (kN/°C)
        correlation: 温度与预紧力的皮尔逊相关系数
        original_mean_preload: 补偿前平均预紧力
        compensated_mean_preload: 补偿后平均预紧力
        delta_t_mean: 平均温度波动
    """
    applied: bool = False
    temperature_coefficient: Optional[float] = None
    correlation: Optional[float] = None
    original_mean_preload: Optional[float] = None
    compensated_mean_preload: Optional[float] = None
    delta_t_mean: Optional[float] = None


class FeatureImportanceInfo(BaseModel):
    """特征重要性分析（各通道对预测结果的贡献度）"""
    preload: float = Field(0.0, description="预紧力通道重要性")
    temperature: float = Field(0.0, description="温度通道重要性")
    humidity: float = Field(0.0, description="湿度通道重要性")
    vibration: float = Field(0.0, description="振动通道重要性")
    torque: float = Field(0.0, description="扭矩通道重要性")
    others: Dict[str, float] = Field(default_factory=dict, description="其他扩展通道的重要性")


class BoltMultivariatePredictionRequest(BaseModel):
    """
    螺栓多变量耦合预测请求

    请求支持两种数据格式：
    1. channels 分开提供（各通道时间戳可以不同，服务端会自动对齐插值）
    2. aligned_data 统一提供（各通道已在同一时间网格上，仅需缺失值插值）

    Attributes:
        bolt_id: 螺栓唯一标识
        channels: 分通道提供的时序数据 {通道名: [[时间, 值], ...]}
        aligned_data: 已对齐的多通道数据 [[时间, 通道1, 通道2, ...], ...]
        aligned_channel_names: 使用 aligned_data 时必须提供，对应列的通道名称（不含时间列）
        timestamps: 可选，统一目标时间网格
        apply_temp_compensation: 是否执行温度耦合补偿（默认 True）
        enable_degradation: 缺失严重时是否降级为单变量预测（默认 True）
        version: 模型版本号（可选）
    """
    bolt_id: str = Field(..., description="螺栓唯一标识")

    channels: Optional[Dict[str, List[List[Any]]]] = Field(
        None,
        description="分通道数据 {channel_name: [[timestamp, value], ...]}，时间戳可不对齐",
        examples=[{
            "preload": [["2025-02-01 00:00:00", 600.0], ["2025-02-01 00:01:00", 599.5]],
            "temperature": [["2025-02-01 00:00:30", 25.3], ["2025-02-01 00:01:30", 25.8]],
            "humidity": [["2025-02-01 00:00:00", 45.2], ["2025-02-01 00:01:00", 44.8]],
        }]
    )

    aligned_data: Optional[List[List[Any]]] = Field(
        None,
        description="已对齐的多通道数据（首列为时间戳），形状(N, 1 + C)",
        examples=[[
            ["2025-02-01 00:00:00", 600.0, 25.3, 45.2, 0.02, 120.5],
            ["2025-02-01 00:01:00", 599.5, 25.8, 44.8, 0.03, 120.3],
        ]]
    )
    aligned_channel_names: Optional[List[str]] = Field(
        None,
        description="aligned_data 除去时间列后的各通道名，顺序与列对应",
        examples=[["preload", "temperature", "humidity", "vibration", "torque"]]
    )

    timestamps: Optional[List[Any]] = Field(
        None,
        description="目标时间戳列表（可选），不填则自动推导统一时间网格"
    )

    apply_temp_compensation: bool = Field(True, description="是否执行温度耦合补偿")
    enable_degradation: bool = Field(True, description="缺失严重时是否自动降级为单变量预测")
    version: Optional[str] = Field(None, description="模型版本号")

    class Config:
        json_schema_extra = {
            "example": {
                "bolt_id": "B001",
                "channels": {
                    "preload": [
                        ["2025-02-01 00:00:00", 600.0],
                        ["2025-02-01 00:01:00", 599.5],
                        ["2025-02-01 00:02:00", 598.8],
                        ["2025-02-01 00:03:00", 597.3],
                        ["2025-02-01 00:04:00", 595.1],
                    ],
                    "temperature": [
                        ["2025-02-01 00:00:00", 25.3],
                        ["2025-02-01 00:02:00", 26.1],
                        ["2025-02-01 00:04:00", 27.5],
                    ],
                    "humidity": [
                        ["2025-02-01 00:00:00", 45.2],
                        ["2025-02-01 00:01:00", 44.8],
                        ["2025-02-01 00:02:00", 44.5],
                        ["2025-02-01 00:03:00", 44.1],
                        ["2025-02-01 00:04:00", 43.9],
                    ],
                    "vibration": [
                        ["2025-02-01 00:00:00", 0.02],
                        ["2025-02-01 00:02:00", 0.05],
                    ],
                    "torque": [
                        ["2025-02-01 00:00:00", 120.5],
                        ["2025-02-01 00:04:00", 119.8],
                    ]
                },
                "apply_temp_compensation": True,
                "enable_degradation": True
            }
        }


class BoltMultivariatePredictionResponse(BaseModel):
    """
    螺栓多变量耦合预测响应

    在标准螺栓预测响应基础上，新增：
    - data_quality: 数据质量评估（含降级信息）
    - channels_info: 实际使用的通道元数据
    - temp_compensation: 温度耦合补偿详情
    - feature_importance: 各通道特征重要性（可解释性）
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
    model_version: Optional[str] = Field(None, description="模型版本号")

    # ==== 多变量扩展字段 ====
    input_dim_actual: int = Field(..., description="实际输入模型的通道数")
    channels_info: List[MultivariateChannelSchema] = Field(default_factory=list, description="实际使用的通道元数据")
    data_quality: DataQualityInfo = Field(..., description="数据质量评估与降级信息")
    temp_compensation: Optional[TemperatureCompensationInfo] = Field(None, description="温度耦合补偿详情")
    feature_importance: Optional[FeatureImportanceInfo] = Field(None, description="各通道特征重要性（可解释性）")
    sequence_length_used: int = Field(0, description="实际送入模型的序列长度")
    prediction_source: str = Field("multivariate_lstm", description="预测来源: multivariate_lstm / degraded_univariate / fallback")

    fault_detail: Optional[FaultDetailSchema] = Field(None, description="故障类型细分详情")
    shadow_version: Optional[str] = Field(None, description="Shadow模式版本号")
    shadow_result: Optional[Dict[str, Any]] = Field(None, description="Shadow模式预测结果")


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


class CausalGraphNodeSchema(BaseModel):
    """因果图节点"""
    id: str
    index: int
    in_degree: int
    out_degree: int
    total_degree: int
    centrality: float


class CausalGraphEdgeSchema(BaseModel):
    """因果图边"""
    source: str
    target: str
    source_idx: int
    target_idx: int
    weight: float
    correlation: float
    p_value: Optional[float] = None
    f_stat: Optional[float] = None
    lag: Optional[int] = None
    type: str


class CausalGraphSchema(BaseModel):
    """因果图"""
    nodes: List[CausalGraphNodeSchema]
    edges: List[CausalGraphEdgeSchema]
    adjacency_matrix: List[List[float]]
    edge_weights: List[List[float]]
    bolt_ids: List[str]


class LeadingBoltSchema(BaseModel):
    """领先螺栓信息"""
    bolt_id: str
    index: int
    leading_score: float
    out_degree: int
    in_degree: int
    net_degree: int
    out_strength: float
    in_strength: float
    net_strength: float
    trend_leadership: float
    is_leading: bool


class PropagationPathSchema(BaseModel):
    """传播路径"""
    path: List[str]
    path_indices: List[int]
    depth: int
    total_weight: float
    avg_weight: float


class PropagationPathsSchema(BaseModel):
    """传播路径分析结果"""
    source_bolt: str
    source_idx: int
    paths: List[PropagationPathSchema]
    total_path_count: int
    reachable_bolts: List[str]
    propagation_distance: Dict[str, Optional[int]]
    max_depth: int


class RootCauseBoltSchema(BaseModel):
    """根因螺栓信息"""
    bolt_id: str
    index: int
    root_cause_score: float
    status_code: int
    health_index: float
    is_abnormal: bool


class RootCauseAnalysisSchema(BaseModel):
    """根因分析结果"""
    root_cause_bolt: Optional[RootCauseBoltSchema] = None
    root_cause_ranking: List[RootCauseBoltSchema]
    abnormal_bolts: List[str]
    is_unbalanced_loosening: bool
    total_bolts: int
    abnormal_count: int


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
    correlation_matrix: Optional[List[List[float]]] = None
    causal_graph: Optional[CausalGraphSchema] = None
    leading_bolts: Optional[List[LeadingBoltSchema]] = None
    propagation_paths: Optional[PropagationPathsSchema] = None
    root_cause_analysis: Optional[RootCauseAnalysisSchema] = None
    root_cause_measures: Optional[str] = None
    model_version: Optional[str] = Field(None, description="模型版本号")
    shadow_version: Optional[str] = Field(None, description="Shadow模式版本号")
    shadow_result: Optional[Dict[str, Any]] = Field(None, description="Shadow模式预测结果")
    fault_detail: Optional[FaultDetailSchema] = Field(None, description="故障类型细分详情")


# ==================== 风险评估 ====================

class RiskProbabilityDistributionSchema(BaseModel):
    p_high: float = Field(..., description="高风险概率")
    p_medium: float = Field(..., description="中风险概率")
    p_low: float = Field(..., description="低风险概率")


class FactorContributionSchema(BaseModel):
    name: str = Field(..., description="因子名称")
    display_name: str = Field(..., description="因子显示名")
    raw_score: float = Field(..., description="原始评分")
    weight: float = Field(..., description="权重")
    weighted_score: float = Field(..., description="加权评分")
    contribution_ratio: float = Field(..., description="贡献度占比")
    direction: str = Field(..., description="方向: risk_up/risk_down")


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
    probability_distribution: Optional[RiskProbabilityDistributionSchema] = Field(
        None, description="风险概率分布 P(高/中/低)"
    )
    factor_contributions: Optional[List[FactorContributionSchema]] = Field(
        None, description="各因子贡献度"
    )


class RiskAssessExplainRequest(BaseModel):
    node_id: str = Field(..., description="节点ID（螺栓或法兰面）")
    node_type: str = Field(..., description="节点类型: bolt/flange")
    data: List[List[Any]] = Field(..., description="预紧力时序数据")


class RiskAssessExplainResponse(BaseModel):
    node_id: str
    node_type: str
    risk_score: float
    risk_level: str
    probability_distribution: RiskProbabilityDistributionSchema
    factor_contributions: List[FactorContributionSchema]
    base_value: float = Field(..., description="基准值（所有因子评分均值）")
    total_contribution: float = Field(..., description="总贡献度偏移")
    summary: str = Field(..., description="可读性总结")


class RiskCalibrationUpdateRequest(BaseModel):
    node_type: str = Field(..., description="节点类型 bolt/flange/production_line")
    node_id: str = Field(..., description="节点ID")
    prior_weights: Optional[Dict[str, float]] = Field(None, description="自定义权重覆盖")
    risk_thresholds: Optional[Dict[str, Any]] = Field(None, description="自定义阈值覆盖")
    description: Optional[str] = Field(None, description="变更说明")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


class RiskCalibrationResponse(BaseModel):
    node_type: str
    node_id: str
    prior_weights: Dict[str, float]
    risk_thresholds: Dict[str, Any]
    version: int = 1
    is_active: bool = True
    description: Optional[str] = None
    create_time: Optional[datetime] = None


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
    version: Optional[str] = None
    file_hash: Optional[str] = None
    create_time: Optional[datetime] = None
    training_session_id: Optional[str] = None
    description: Optional[str] = None
    validation_samples: Optional[int] = None
    is_incremental: Optional[bool] = None
    parent_version: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    version_history: Optional[List[Dict[str, Any]]] = None


# ==================== 训练体系增强 ====================

class EarlyStoppingConfig(BaseModel):
    """早停配置"""
    enabled: bool = Field(default=True, description="是否启用早停")
    patience: int = Field(default=10, ge=1, description="耐心轮数，连续多少轮无提升则停止")
    min_delta: float = Field(default=0.001, ge=0, description="最小改进阈值")
    mode: str = Field(default="min", description="监控模式 min=损失最小化/max=准确率最大化")


class LRSchedulerConfig(BaseModel):
    """学习率调度器配置"""
    type: str = Field(
        default="none",
        description="调度器类型: none/reduce_on_plateau/step/cosine"
    )
    factor: Optional[float] = Field(default=0.5, description="reduce_on_plateau衰减因子")
    patience: Optional[int] = Field(default=5, description="reduce_on_plateau耐心轮数")
    min_lr: Optional[float] = Field(default=1e-6, description="最小学习率")
    step_size: Optional[int] = Field(default=20, description="step衰减步长（epoch数）")
    gamma: Optional[float] = Field(default=0.5, description="step衰减因子")
    t_max: Optional[int] = Field(default=None, description="cosine最大迭代轮数")
    eta_min: Optional[float] = Field(default=1e-6, description="cosine最小学习率")


class ClassImbalanceConfig(BaseModel):
    """类别不平衡处理配置"""
    strategy: str = Field(
        default="weighted_loss",
        description="不平衡处理策略: weighted_loss/oversampling/none"
    )
    oversampling_ratio: Optional[float] = Field(default=1.0, description="过采样倍率")


class IncrementalTrainingConfig(BaseModel):
    """增量训练配置"""
    enabled: bool = Field(default=False, description="是否增量训练")
    freeze_layers: Optional[List[str]] = Field(
        default=None,
        description="冻结的层名称列表，如 ['lstm1', 'lstm2']"
    )
    base_model_version: Optional[str] = Field(
        default=None,
        description="基础模型版本号，None则使用最新版本"
    )


class FocalLossConfig(BaseModel):
    """Focal Loss配置"""
    enabled: bool = Field(default=False, description="是否启用Focal Loss")
    gamma: float = Field(default=2.0, description="聚焦参数gamma，难例加权系数")
    alpha: Optional[List[float]] = Field(default=None, description="类别权重alpha列表")


class TrainingConfigSchema(BaseModel):
    """完整训练配置"""
    epochs: Optional[int] = Field(default=None, description="总训练轮数")
    batch_size: Optional[int] = Field(default=None, description="批次大小")
    learning_rate: Optional[float] = Field(default=None, description="初始学习率")
    validation_split: Optional[float] = Field(default=None, description="验证集比例")
    early_stopping: Optional[EarlyStoppingConfig] = Field(default=None, description="早停配置")
    lr_scheduler: Optional[LRSchedulerConfig] = Field(default=None, description="学习率调度配置")
    class_imbalance: Optional[ClassImbalanceConfig] = Field(default=None, description="类别不平衡处理配置")
    incremental: Optional[IncrementalTrainingConfig] = Field(default=None, description="增量训练配置")
    focal_loss: Optional[FocalLossConfig] = Field(default=None, description="Focal Loss配置")


class EnhancedTrainingRequest(BaseModel):
    """增强版模型训练请求"""
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID，空则训练所有")
    force_retrain: bool = Field(default=False, description="是否强制重新训练")
    data_source: str = Field(default="db", description="数据来源: db/csv/manual")
    is_incremental: bool = Field(default=False, description="是否增量训练")
    base_model_version: Optional[str] = Field(default=None, description="增量训练的基础版本")
    freeze_layers: Optional[List[str]] = Field(default=None, description="冻结的层名称")
    training_config: Optional[TrainingConfigSchema] = Field(default=None, description="详细训练配置")

    class Config:
        json_schema_extra = {
            "example": {
                "model_type": "bolt",
                "node_id": "B001",
                "force_retrain": True,
                "is_incremental": False,
                "training_config": {
                    "epochs": 100,
                    "batch_size": 32,
                    "learning_rate": 0.001,
                    "early_stopping": {
                        "enabled": True,
                        "patience": 15,
                        "min_delta": 0.0001,
                        "mode": "min"
                    },
                    "lr_scheduler": {
                        "type": "reduce_on_plateau",
                        "factor": 0.5,
                        "patience": 5,
                        "min_lr": 0.000001
                    },
                    "class_imbalance": {
                        "strategy": "weighted_loss"
                    },
                    "focal_loss": {
                        "enabled": False,
                        "gamma": 2.0
                    }
                }
            }
        }


class EnhancedTrainingResponse(BaseModel):
    """增强版模型训练响应"""
    session_id: str = Field(..., description="训练会话ID，用于查询状态")
    model_type: str
    node_id: Optional[str]
    status: str = Field(..., description="启动状态: started/error")
    message: str = Field(..., description="描述信息")
    is_incremental: bool = Field(default=False, description="是否增量训练")


class TrainingProgressSchema(BaseModel):
    """训练进度信息"""
    phase: Optional[str] = Field(None, description="当前阶段")
    current_epoch: Optional[int] = Field(None, description="当前epoch")
    total_epochs: Optional[int] = Field(None, description="总epoch数")
    current_loss: Optional[float] = Field(None, description="当前损失")
    current_acc: Optional[float] = Field(None, description="当前准确率")
    bolt_id: Optional[str] = Field(None, description="当前训练的螺栓ID")
    flange_id: Optional[str] = Field(None, description="当前训练的法兰面ID")


class TrainingStatusResponse(BaseModel):
    """训练状态查询响应"""
    session_id: str = Field(..., description="训练会话ID")
    model_type: Optional[str] = Field(None, description="模型类型")
    node_id: Optional[str] = Field(None, description="节点ID")
    status: str = Field(..., description="状态: pending/running/completed/failed/not_found")
    message: str = Field(..., description="状态描述")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    is_incremental: Optional[bool] = Field(None, description="是否增量训练")
    data_source: Optional[str] = Field(None, description="数据来源")
    total_epochs: Optional[int] = Field(None, description="总epoch数")
    current_epoch: Optional[int] = Field(None, description="当前epoch")
    best_epoch: Optional[int] = Field(None, description="最佳epoch")
    best_val_acc: Optional[float] = Field(None, description="最佳验证准确率")
    best_val_loss: Optional[float] = Field(None, description="最佳验证损失")
    final_train_acc: Optional[float] = Field(None, description="最终训练准确率")
    final_train_loss: Optional[float] = Field(None, description="最终训练损失")
    final_val_acc: Optional[float] = Field(None, description="最终验证准确率")
    final_val_loss: Optional[float] = Field(None, description="最终验证损失")
    precision: Optional[float] = Field(None, description="精确率")
    recall: Optional[float] = Field(None, description="召回率")
    f1_score: Optional[float] = Field(None, description="F1分数")
    samples_count: Optional[int] = Field(None, description="训练样本数")
    val_samples_count: Optional[int] = Field(None, description="验证样本数")
    error_message: Optional[str] = Field(None, description="错误信息（失败时）")
    progress: Optional[TrainingProgressSchema] = Field(None, description="训练进度（运行中时）")


class TrainingSessionItemSchema(BaseModel):
    """训练会话列表项"""
    session_id: str = Field(..., description="训练会话ID")
    model_type: Optional[str] = Field(None)
    model_id: Optional[str] = Field(None, description="节点ID")
    status: str = Field(..., description="状态")
    start_time: Optional[datetime] = Field(None)
    end_time: Optional[datetime] = Field(None)
    best_val_acc: Optional[float] = Field(None)
    f1_score: Optional[float] = Field(None)
    samples_count: Optional[int] = Field(None)
    error_message: Optional[str] = Field(None)


class TrainingSessionListResponse(BaseModel):
    """训练会话列表响应"""
    total: int = Field(..., description="总数量")
    items: List[TrainingSessionItemSchema] = Field(default_factory=list, description="会话列表")


class LabelImportCSVRequest(BaseModel):
    """CSV标注导入请求"""
    csv_path: str = Field(..., description="CSV文件路径")
    node_type: str = Field(..., description="节点类型: bolt/flange")
    label_column: Optional[str] = Field(None, description="标签列名，自动检测")
    id_column: Optional[str] = Field(None, description="节点ID列名，自动检测")
    data_column: Optional[str] = Field(None, description="数据点列名")
    timestamp_column: Optional[str] = Field(None, description="时间戳列名")
    labeler_name: Optional[str] = Field(None, description="标注人姓名")
    auto_approve: bool = Field(default=True, description="是否自动审核通过")
    skip_errors: bool = Field(default=True, description="是否跳过错误行")


class LabelImportDBRequest(BaseModel):
    """数据库标注导入请求"""
    source_table: str = Field(..., description="源表名")
    node_type: str = Field(..., description="节点类型: bolt/flange")
    id_field: str = Field(..., description="节点ID字段名")
    label_field: str = Field(..., description="标签字段名")
    data_field: Optional[str] = Field(None, description="数据点字段名")
    timestamp_field: Optional[str] = Field(None, description="时间戳字段名")
    where_clause: Optional[str] = Field(None, description="WHERE条件，不带WHERE关键字")
    labeler_name: Optional[str] = Field(None, description="标注人姓名")
    auto_approve: bool = Field(default=True, description="是否自动审核通过")


class LabelImportResultSchema(BaseModel):
    """标注导入结果"""
    total: int = Field(0, description="总行数")
    imported: int = Field(0, description="成功导入数")
    skipped: int = Field(0, description="跳过数")
    duplicates: int = Field(0, description="重复数")
    errors: int = Field(0, description="错误数")
    error_details: Optional[List[Dict[str, Any]]] = Field(default=None, description="错误详情")


class LabelImportResponse(BaseModel):
    """标注导入响应"""
    status: str = Field(..., description="状态: success/error")
    message: str = Field(..., description="描述信息")
    result: Optional[LabelImportResultSchema] = Field(default=None, description="导入结果统计")


class LabelImportFileItemSchema(BaseModel):
    """可导入文件列表项"""
    filename: str = Field(..., description="文件名")
    path: str = Field(..., description="文件完整路径")
    size_bytes: int = Field(0, description="文件大小（字节）")
    modified_time: Optional[datetime] = Field(None, description="修改时间")


class LabelImportFileListResponse(BaseModel):
    """可导入文件列表响应"""
    total: int = Field(..., description="文件数量")
    items: List[LabelImportFileItemSchema] = Field(default_factory=list, description="文件列表")


class ModelVersionSchema(BaseModel):
    """模型版本信息"""
    version: str = Field(..., description="版本号 vX.Y.Z")
    create_time: datetime
    is_active: bool = Field(default=False)
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    training_samples: Optional[int] = None
    validation_samples: Optional[int] = None
    training_duration_seconds: Optional[float] = None
    parent_version: Optional[str] = None
    training_session_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class ModelVersionListResponse(BaseModel):
    """模型版本列表响应"""
    model_type: str
    node_id: str
    total: int = Field(..., description="版本数量")
    items: List[ModelVersionSchema] = Field(default_factory=list, description="版本列表")


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


class StrategyConfigUpdateRequest(BaseModel):
    """预警策略动态配置更新请求"""
    scope: str = Field('global', description="作用域: global/bolt/flange/production_line")
    node_type: Optional[str] = Field(None, description="节点类型 bolt/flange/production_line，scope非global时必填")
    node_id: Optional[str] = Field(None, description="节点ID，scope非global时必填")
    strategy_type: int = Field(..., ge=1, le=2, description="策略类型: 1=应报尽报, 2=精准报警")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1, description="置信度阈值")
    false_positive_threshold: Optional[float] = Field(None, ge=0, le=1, description="误报容忍度")
    false_negative_threshold: Optional[float] = Field(None, ge=0, le=1, description="漏报容忍度")
    description: Optional[str] = Field(None, description="变更说明")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


class StrategyConfigItemResponse(BaseModel):
    """单条策略配置响应"""
    id: int
    scope: str = 'global'
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    strategy_type: int
    confidence_threshold: float
    false_positive_threshold: Optional[float] = None
    false_negative_threshold: Optional[float] = None
    version: int = 1
    is_active: bool = True
    description: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


class EffectiveStrategyResponse(BaseModel):
    """当前生效策略响应（含全局和节点覆盖）"""
    global_config: StrategyConfigItemResponse
    node_overrides: List[StrategyConfigItemResponse] = Field(default_factory=list)
    effective: StrategyConfigItemResponse


class StrategyConfigListResponse(BaseModel):
    """策略配置列表响应"""
    total: int
    items: List[StrategyConfigItemResponse]


class StrategyRollbackRequest(BaseModel):
    """策略回滚请求"""
    target_version: int = Field(..., ge=1, description="回滚目标版本号")
    scope: str = Field('global', description="作用域")
    node_type: Optional[str] = Field(None, description="节点类型")
    node_id: Optional[str] = Field(None, description="节点ID")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


class StrategyAuditLogResponse(BaseModel):
    """策略审计日志响应"""
    id: int
    config_id: int
    scope: str
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    action: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    version_before: Optional[int] = None
    version_after: Optional[int] = None
    change_summary: Optional[str] = None
    operator_id: Optional[str] = None
    operator_name: Optional[str] = None
    create_time: Optional[datetime] = None


class StrategyAuditLogListResponse(BaseModel):
    """策略审计日志列表响应"""
    total: int
    items: List[StrategyAuditLogResponse]


class StrategyNodeOverrideDeleteRequest(BaseModel):
    """删除节点级策略覆盖请求"""
    node_type: str = Field(..., description="节点类型 bolt/flange/production_line")
    node_id: str = Field(..., description="节点ID")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")


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
    model_type: str = Field(..., description="模型类型 bolt/flange")
    node_id: str = Field(..., description="节点ID")
    version: str = Field(..., description="目标版本号")


class ModelVersionRollbackRequest(BaseModel):
    """回滚模型版本请求"""
    model_type: str = Field(..., description="模型类型 bolt/flange")
    node_id: str = Field(..., description="节点ID")
    version: Optional[str] = Field(None, description="目标版本号，不填则回滚到上一版本")


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


# ============================================================
# 配置中心模块
# ============================================================

# ---------- 预警策略配置 ----------

class WarningStrategyConfigSchema(BaseModel):
    """预警策略配置"""
    strategy_type: int = Field(..., ge=1, le=2, description="策略类型: 1=应报尽报, 2=精准报警")
    strategy_1_confidence_threshold: float = Field(0.7, ge=0, le=1, description="策略1置信度阈值")
    strategy_1_false_positive_threshold: float = Field(0.05, ge=0, le=1, description="策略1误报率阈值")
    strategy_2_confidence_threshold: float = Field(0.95, ge=0, le=1, description="策略2置信度阈值")
    strategy_2_false_negative_threshold: float = Field(0.10, ge=0, le=1, description="策略2漏报率阈值")


# ---------- 阈值配置 ----------

class ThresholdConfigSchema(BaseModel):
    """预警阈值配置"""
    high_risk_threshold: int = Field(3, ge=1, le=10, description="高风险阈值")
    medium_risk_threshold: int = Field(7, ge=1, le=10, description="中风险阈值")
    min_normal_preload: float = Field(400, ge=0, description="正常预紧力最小值")
    max_normal_preload: float = Field(800, ge=0, description="正常预紧力最大值")
    warning_deviation: float = Field(0.1, ge=0, le=1, description="预警偏差比例")
    critical_deviation: float = Field(0.2, ge=0, le=1, description="紧急偏差比例")
    auto_create_work_order_level: int = Field(3, ge=1, le=4, description="自动创建工单的最低告警级别")
    default_upgrade_minutes: int = Field(30, ge=0, description="默认未处理升级时间（分钟）")


# ---------- 调度任务 ----------

class ScheduledJobSchema(BaseModel):
    """调度任务信息"""
    id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    enabled: bool = Field(..., description="是否启用")
    cron: str = Field(..., description="Cron表达式")
    next_run: Optional[datetime] = Field(None, description="下次执行时间")
    description: Optional[str] = Field(None, description="任务描述")


class SchedulerJobUpdateRequest(BaseModel):
    """调度任务更新请求"""
    enabled: Optional[bool] = Field(None, description="是否启用")
    cron: Optional[str] = Field(None, description="Cron表达式")


class SchedulerTriggerRequest(BaseModel):
    """手动触发调度任务请求"""
    job_id: str = Field(..., description="任务ID")


class JobExecutionLogSchema(BaseModel):
    """任务执行日志"""
    id: int = Field(..., description="日志ID")
    job_name: str = Field(..., description="任务名称")
    job_type: str = Field(..., description="任务类型")
    trigger_type: str = Field(..., description="触发类型")
    status: str = Field(..., description="状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[int] = Field(None, description="执行时长（秒）")
    total_nodes: int = Field(0, description="处理节点总数")
    success_count: int = Field(0, description="成功节点数")
    failed_count: int = Field(0, description="失败节点数")
    skipped_count: int = Field(0, description="跳过节点数")
    shard_index: Optional[int] = Field(None, description="分片索引")
    shard_total: Optional[int] = Field(None, description="总分片数")
    bolt_id_min: Optional[str] = Field(None, description="最小bolt_id")
    bolt_id_max: Optional[str] = Field(None, description="最大bolt_id")
    instance_id: Optional[str] = Field(None, description="执行实例ID")
    error_summary: Optional[Dict[str, Any]] = Field(None, description="错误摘要")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    create_time: datetime = Field(..., description="创建时间")


class JobExecutionLogListResponse(BaseModel):
    """任务执行日志列表响应"""
    total: int = Field(..., description="总记录数")
    items: List[JobExecutionLogSchema] = Field(..., description="日志列表")


class LeaderStatusSchema(BaseModel):
    """Leader选举状态"""
    leader_key: str = Field(..., description="Leader锁键")
    leader_id: str = Field(..., description="当前Leader实例ID")
    lease_expire_time: datetime = Field(..., description="租约过期时间")
    last_heartbeat: datetime = Field(..., description="最后心跳时间")
    version: int = Field(..., description="版本号")
    is_expired: bool = Field(..., description="租约是否已过期")
    is_current_instance: bool = Field(..., description="当前实例是否为Leader")


class SchedulerTriggerResponse(BaseModel):
    """调度任务触发响应"""
    job_name: str = Field(..., description="任务名称")
    status: str = Field(..., description="状态: triggered/skipped")
    message: str = Field(..., description="消息")
    log_id: Optional[int] = Field(None, description="任务执行日志ID")
    is_leader: Optional[bool] = Field(None, description="是否为Leader节点")


# ---------- 配置中心整体响应 ----------

class ConfigCenterResponse(BaseModel):
    """配置中心整体响应"""
    warning_strategy: WarningStrategyConfigSchema
    thresholds: ThresholdConfigSchema
    scheduled_jobs: List[ScheduledJobSchema]
    updated_at: datetime


# ============================================================
# 异常检测增强与闭环
# ============================================================

class AnomalyDataResponse(BaseModel):
    """
    异常数据响应模型

    对应 sc_anomaly_data 表的完整字段，
    包含异常信息、分类、确认标注等。
    """
    id: int
    sensor_id: str
    anomaly_value: Optional[float] = None
    anomaly_type: Optional[str] = None
    anomaly_score: Optional[float] = None
    original_time: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    classification: Optional[str] = None
    classification_confidence: Optional[float] = None
    collection_subtype: Optional[str] = None
    true_anomaly_subtype: Optional[str] = None
    classification_evidence: Optional[Dict[str, Any]] = None
    is_confirmed: bool = False
    is_false_positive: bool = False
    confirmed_by: Optional[str] = None
    confirmed_time: Optional[datetime] = None
    confirm_note: Optional[str] = None
    tenant_id: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnomalyQueryRequest(BaseModel):
    """
    异常查询请求

    支持按 sensor_id、时间范围、类型、确认状态等多维度查询。
    """
    sensor_id: Optional[str] = Field(None, description="传感器/螺栓ID")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    anomaly_type: Optional[str] = Field(None, description="异常类型")
    classification: Optional[str] = Field(None, description="异常分类")
    is_confirmed: Optional[bool] = Field(None, description="是否已确认")
    is_false_positive: Optional[bool] = Field(None, description="是否为误报")
    min_score: Optional[float] = Field(None, description="最低异常评分")
    max_score: Optional[float] = Field(None, description="最高异常评分")
    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
    sort_by: str = Field("original_time", description="排序字段")
    sort_order: str = Field("desc", description="排序方向 asc/desc")


class AnomalyListResponse(BaseModel):
    """
    异常列表响应
    """
    total: int = Field(..., description="总记录数")
    items: List[AnomalyDataResponse] = Field(..., description="异常数据列表")


class AnomalyConfirmRequest(BaseModel):
    """
    确认异常请求

    将异常标记为真实异常。
    """
    anomaly_id: int = Field(..., description="异常记录ID")
    confirmed_by: Optional[str] = Field(None, description="确认人ID")
    confirm_note: Optional[str] = Field(None, description="确认备注")


class AnomalyFalsePositiveRequest(BaseModel):
    """
    标注误报请求

    将异常标记为误报。
    """
    anomaly_id: int = Field(..., description="异常记录ID")
    confirmed_by: Optional[str] = Field(None, description="标注人ID")
    confirm_note: Optional[str] = Field(None, description="标注备注")


class AnomalyBatchConfirmRequest(BaseModel):
    """
    批量确认异常请求
    """
    anomaly_ids: List[int] = Field(..., description="异常记录ID列表")
    confirmed_by: Optional[str] = Field(None, description="确认人ID")
    confirm_note: Optional[str] = Field(None, description="确认备注")


class AnomalyBatchFalsePositiveRequest(BaseModel):
    """
    批量标注误报请求
    """
    anomaly_ids: List[int] = Field(..., description="异常记录ID列表")
    confirmed_by: Optional[str] = Field(None, description="标注人ID")
    confirm_note: Optional[str] = Field(None, description="标注备注")


class AnomalyBatchResultResponse(BaseModel):
    """
    批量操作结果响应
    """
    total: int = Field(0, description="总数量")
    success: int = Field(0, description="成功数量")
    failed: int = Field(0, description="失败数量")
    failed_ids: List[int] = Field(default_factory=list, description="失败的ID列表")


class AnomalyStatisticsResponse(BaseModel):
    """
    异常统计响应
    """
    total_count: int = Field(0, description="异常总数")
    confirmed_count: int = Field(0, description="已确认数")
    unconfirmed_count: int = Field(0, description="未确认数")
    false_positive_count: int = Field(0, description="误报数")
    true_anomaly_count: int = Field(0, description="真实异常数")
    false_positive_rate: float = Field(0.0, description="误报率")
    type_distribution: Optional[Dict[str, int]] = None
    classification_distribution: Optional[Dict[str, int]] = None
    time_range: Optional[Dict[str, Any]] = None


class AnomalyWarningImpactResponse(BaseModel):
    """
    异常对预警等级影响分析响应
    """
    sensor_id: str
    should_upgrade: bool = Field(False, description="是否需要提升预警等级")
    original_level: int = Field(..., description="原始预警等级")
    upgraded_level: int = Field(..., description="提升后的预警等级")
    anomaly_count: int = Field(0, description="时间窗口内的异常数")
    threshold: int = Field(0, description="异常数阈值")
    window_minutes: int = Field(0, description="时间窗口（分钟）")


# ==================== API密钥管理与审计日志 ====================

class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., description="密钥名称", min_length=1, max_length=200)
    permissions: List[str] = Field(default=["read"], description="权限列表: read/write/admin")
    rate_limit: int = Field(default=1000, ge=1, le=100000, description="每小时请求限制")
    expires_hours: Optional[int] = Field(None, description="有效期（小时），None表示永不过期")


class APIKeyCreateResponse(BaseModel):
    key: str = Field(..., description="生成的API密钥（仅创建时返回完整密钥）")
    key_id: str = Field(..., description="密钥ID")
    name: str = Field(..., description="密钥名称")
    permissions: List[str] = Field(default=["read"], description="权限列表")
    rate_limit: int = Field(default=1000, description="速率限制")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    created_at: str = Field(..., description="创建时间")


class APIKeyInfoResponse(BaseModel):
    key_id: str = Field(..., description="密钥ID")
    key_preview: str = Field(..., description="密钥预览（前8后4位）")
    name: str = Field(..., description="密钥名称")
    permissions: List[str] = Field(default=["read"], description="权限列表")
    rate_limit: int = Field(default=1000, description="速率限制")
    is_expired: bool = Field(False, description="是否已过期")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    created_at: Optional[str] = Field(None, description="创建时间")


class APIKeyListResponse(BaseModel):
    total: int = Field(..., description="总数")
    items: List[APIKeyInfoResponse] = Field(default=[], description="密钥列表")


class APIKeyRotateResponse(BaseModel):
    old_key_id: str = Field(..., description="旧密钥ID")
    new_key: str = Field(..., description="新密钥（仅轮换时返回完整密钥）")
    new_key_id: str = Field(..., description="新密钥ID")
    old_key_grace_expires: datetime = Field(..., description="旧密钥宽限期截止时间")
    permissions: List[str] = Field(default=["read"], description="权限列表（继承旧密钥）")
    rate_limit: int = Field(default=1000, description="速率限制")


class APIKeyRevokeResponse(BaseModel):
    key_id: str = Field(..., description="被吊销的密钥ID")
    revoked: bool = Field(True, description="是否成功吊销")


class APIAuditLogResponse(BaseModel):
    id: int
    key_id: str = Field("", description="API密钥ID")
    key_name: str = Field("", description="密钥名称")
    method: str = Field("", description="HTTP方法")
    path: str = Field("", description="请求路径")
    status_code: int = Field(0, description="响应状态码")
    client_ip: str = Field("", description="客户端IP")
    request_id: str = Field("", description="请求ID")
    extra_info: Dict[str, Any] = Field(default={}, description="扩展信息")
    create_time: datetime


class APIAuditLogListResponse(BaseModel):
    total: int = Field(..., description="总数")
    items: List[APIAuditLogResponse] = Field(default=[], description="审计日志列表")


class RateLimitStatusResponse(BaseModel):
    key_id: str = Field(..., description="密钥ID")
    limit: int = Field(..., description="速率限制（请求/小时）")
    remaining: int = Field(..., description="剩余请求次数")
    used: int = Field(..., description="已使用请求次数")


# ============================================================
# LLM 智能诊断报告
# ============================================================

class DiagnosisReportRequest(BaseModel):
    """
    单次诊断报告生成请求
    """
    status: str = Field(..., description="状态：正常/关注级预警/检查级预警/紧急级预警/故障")
    risk_score: float = Field(..., description="风险评分(0-10)，分数越低风险越高")
    node_type: str = Field("bolt", description="节点类型：bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID")
    fault_type: Optional[str] = Field(None, description="故障类型：loosening/preload_decrease/severe_anomaly/failure")
    trend: Optional[str] = Field(None, description="趋势：stable/decreasing/increasing/fluctuating")
    recent_values: Optional[List[float]] = Field(None, description="近期预紧力数值列表")
    historical_incidents: Optional[int] = Field(None, description="历史同类事件数")


class DiagnosisReportResponse(BaseModel):
    """
    诊断报告响应
    """
    diagnosis_summary: str = Field(..., description="诊断摘要（200字内）")
    recommended_actions: List[str] = Field(..., description="推荐处置措施（分步骤）")
    urgency_level: str = Field(..., description="紧急程度：low/medium/high/critical")
    model: str = Field(..., description="使用的模型")
    tokens_used: int = Field(0, description="Token用量")
    latency_ms: float = Field(0.0, description="生成延迟（毫秒）")
    is_fallback: bool = Field(False, description="是否使用降级模板")


class ReportGenerateRequest(BaseModel):
    """
    周期报告生成请求（周报/月报）
    """
    node_type: str = Field(..., description="节点类型：bolt/flange")
    node_id: str = Field(..., description="节点ID（螺栓ID或法兰面ID）")
    report_type: str = Field("weekly", description="报告类型：weekly/monthly")
    use_llm: Optional[bool] = Field(True, description="是否使用LLM生成（默认True，不可用时自动降级）")


class ReportStatisticsSchema(BaseModel):
    """报告统计数据"""
    prediction_count: int = Field(0, description="预测次数")
    avg_risk_score: float = Field(0.0, description="平均风险评分")
    min_risk_score: float = Field(0.0, description="最低风险评分（最高风险）")
    max_risk_score: float = Field(0.0, description="最高风险评分（最低风险）")
    status_distribution: Dict[str, int] = Field(default_factory=dict, description="状态分布")
    trend: str = Field("stable", description="整体趋势")
    max_status: str = Field("正常", description="周期内最高状态")
    fault_types: List[str] = Field(default_factory=list, description="出现的故障类型")


class PeriodicReportResponse(BaseModel):
    """
    周期报告响应（周报/月报）
    """
    report_type: str = Field(..., description="报告类型：weekly/monthly")
    node_id: str = Field(..., description="节点ID")
    node_type: str = Field(..., description="节点类型")
    period_start: datetime = Field(..., description="统计周期开始时间")
    period_end: datetime = Field(..., description="统计周期结束时间")
    diagnosis_summary: str = Field(..., description="诊断摘要")
    recommended_actions: List[str] = Field(..., description="推荐处置措施")
    urgency_level: str = Field(..., description="整体紧急程度：low/medium/high/critical")
    statistics: ReportStatisticsSchema = Field(..., description="统计数据")
    generated_at: datetime = Field(..., description="生成时间")
    model: str = Field(..., description="使用的模型")
    is_fallback: bool = Field(False, description="是否使用降级模板")


class BatchReportGenerateRequest(BaseModel):
    """
    批量生成报告请求
    """
    node_type: str = Field(..., description="节点类型：bolt/flange")
    node_ids: List[str] = Field(..., description="节点ID列表")
    report_type: str = Field("weekly", description="报告类型：weekly/monthly")


class BatchReportResponse(BaseModel):
    """批量报告响应"""
    total: int = Field(0, description="总数")
    success: int = Field(0, description="成功数量")
    failed: int = Field(0, description="失败数量")
    results: List[PeriodicReportResponse] = Field(default_factory=list, description="成功的报告列表")
    errors: Dict[str, str] = Field(default_factory=dict, description="失败的节点及错误信息")


# ============================================================
# 碳排与能效关联分析模块
# ============================================================

# ---------- 碳排风险排行 ----------

class CarbonRiskItemSchema(BaseModel):
    """碳排风险排行单项"""
    rank: Optional[int] = Field(None, description="排名")
    node_id: str = Field(..., description="节点ID")
    node_type: str = Field(..., description="节点类型 bolt/flange/device")
    node_name: str = Field(..., description="节点名称")
    hi_score: float = Field(..., description="健康度指数 HI 0-100")
    hi_level: str = Field(..., description="HI等级 excellent/good/fair/poor/critical")
    carbon_risk_score: float = Field(..., description="碳排风险评分 0-100")
    carbon_risk_level: str = Field(..., description="碳排风险等级 low/medium/high/critical")
    monthly_leakage_volume_m3: float = Field(..., description="月度估算泄漏量 (m³)")
    monthly_carbon_increment_kg: float = Field(..., description="月度碳排增量 (kgCO₂e)")
    priority_score: float = Field(..., description="综合优先级评分")
    trend: str = Field(..., description="趋势 stable/gradual_decline/accelerating_decline/recovering")
    recommendations: List[str] = Field(default_factory=list, description="推荐措施")


class CarbonMonthlyRankingRequest(BaseModel):
    """装置级月度碳排风险排行请求"""
    nodes: List[Dict[str, Any]] = Field(
        ...,
        description="节点数据列表，每项包含: node_id, node_type(可选), node_name(可选), "
                    "hi_score, hi_level, preload_history, timestamps(可选), "
                    "service_age_months(可选), avg_temperature(可选), "
                    "seal_age_years(可选), operating_pressure_mpa(可选), energy_source(可选)"
    )
    top_n: Optional[int] = Field(None, description="返回前N名，None表示全部", ge=1)


class CarbonMonthlyRankingResponse(BaseModel):
    """装置级月度碳排风险排行响应"""
    report_month: str = Field(..., description="报告月份 YYYY-MM")
    total_nodes: int = Field(..., description="分析节点总数")
    total_monthly_carbon_increment_kg: float = Field(..., description="月度碳排增量合计 (kgCO₂e)")
    total_monthly_leakage_volume_m3: float = Field(..., description="月度泄漏量合计 (m³)")
    risk_distribution: Dict[str, int] = Field(..., description="风险等级分布 {critical, high, medium, low}")
    ranked_items: List[CarbonRiskItemSchema] = Field(..., description="按优先级排序的碳排风险列表")
    generated_at: datetime = Field(..., description="生成时间")


# ---------- HI + 碳排并列展示 ----------

class HICarbonDualItemSchema(BaseModel):
    """HI与碳排并列展示单项"""
    node_id: str = Field(..., description="节点ID")
    node_type: str = Field(..., description="节点类型")
    node_name: str = Field(..., description="节点名称")
    hi_score: float = Field(..., description="健康度指数 0-100")
    hi_level: str = Field(..., description="HI等级")
    hi_trend: str = Field(..., description="HI趋势 improving/stable/declining")
    degradation_rate_per_month: float = Field(..., description="预紧力月劣化速率")
    estimated_leakage_rate_m3_hour: float = Field(..., description="估算泄漏率 (m³/h)")
    monthly_carbon_increment_kg: float = Field(..., description="月度碳排增量 (kgCO₂e)")
    carbon_risk_level: str = Field(..., description="碳排风险等级 low/medium/high/critical")
    carbon_trend: str = Field(..., description="碳排趋势 increasing/stable/decreasing")


class HICarbonDualViewRequest(BaseModel):
    """HI rollup 与碳排并列展示请求"""
    nodes: List[Dict[str, Any]] = Field(
        ...,
        description="节点数据列表，每项包含: node_id, node_type(可选), node_name(可选), "
                    "hi_score, hi_level, hi_trend(可选), preload_history, "
                    "timestamps(可选), service_age_months(可选), avg_temperature(可选), "
                    "seal_age_years(可选), operating_pressure_mpa(可选)"
    )


class HICarbonDualViewResponse(BaseModel):
    """HI rollup 与碳排并列展示响应"""
    report_month: str = Field(..., description="报告月份 YYYY-MM")
    total_nodes: int = Field(..., description="节点总数")
    items: List[HICarbonDualItemSchema] = Field(..., description="HI与碳排并列数据列表")
    generated_at: datetime = Field(..., description="生成时间")


# ---------- ESG 报表导出 ----------

class ESGReportExportRequest(BaseModel):
    """ESG报表片段导出请求"""
    nodes: List[Dict[str, Any]] = Field(
        ...,
        description="节点数据列表，格式同 CarbonMonthlyRankingRequest"
    )
    format: str = Field("json", description="导出格式 json/csv/html")
    include_methodology: bool = Field(True, description="是否包含方法学说明")
    top_n: Optional[int] = Field(10, description="返回前N名高风险装置", ge=1)


class ESGReportSummarySchema(BaseModel):
    """ESG报表汇总数据"""
    reporting_period: str = Field(..., description="报告期")
    total_devices_analyzed: int = Field(..., description="分析装置总数")
    estimated_monthly_carbon_increment_kg: float = Field(..., description="月度碳排增量估算 (kgCO₂e)")
    estimated_monthly_carbon_increment_tons: float = Field(..., description="月度碳排增量估算 (吨CO₂e)")
    estimated_monthly_leakage_m3: float = Field(..., description="月度泄漏量估算 (m³)")
    average_carbon_per_device_kg: float = Field(..., description="单装置平均月度碳排增量 (kgCO₂e)")
    carbon_risk_severity: str = Field(..., description="碳排风险严重度 高/中/低")
    top5_contribution_ratio: float = Field(..., description="Top5装置碳排贡献占比")
    risk_distribution: Dict[str, int] = Field(..., description="风险分布")


class ESGTrendAnalysisSchema(BaseModel):
    """ESG趋势分析"""
    overall_trend: str = Field(..., description="整体趋势 deteriorating/stable/improving")
    improving_count: int = Field(..., description="改善装置数")
    stable_count: int = Field(..., description="稳定装置数")
    declining_count: int = Field(..., description="劣化装置数")
    key_observation: str = Field(..., description="关键观察结论")


class ESGReportFragmentResponse(BaseModel):
    """ESG报表片段响应"""
    report_period: str = Field(..., description="报告期")
    generated_at: datetime = Field(..., description="生成时间")
    summary: ESGReportSummarySchema = Field(..., description="汇总数据")
    top_risk_items: List[CarbonRiskItemSchema] = Field(..., description="高风险装置列表")
    trend_analysis: ESGTrendAnalysisSchema = Field(..., description="趋势分析")
    recommendations: List[str] = Field(..., description="建议措施")
    methodology_note: Optional[str] = Field(None, description="方法学说明")
    csv_content: Optional[str] = Field(None, description="CSV格式内容（format=csv时返回）")


# ---------- 模型系数配置 ----------

class DegradationParamsSchema(BaseModel):
    """预紧力劣化模型参数"""
    nominal_preload: float = Field(600.0, description="额定预紧力 (kN)")
    min_effective_preload_ratio: float = Field(0.6, description="最小有效压紧比阈值")
    relaxation_rate_per_month: float = Field(0.015, description="自然松弛月速率")
    temperature_acceleration_factor: float = Field(0.002, description="高温加速因子 (每°C高于40)")
    vibration_acceleration_factor: float = Field(0.003, description="振动加速因子")
    cycle_acceleration_factor: float = Field(0.0001, description="压力循环加速因子")


class LeakageParamsSchema(BaseModel):
    """泄漏率估算模型参数"""
    base_leakage_rate_m3_per_hour: float = Field(0.0, description="基准泄漏率 (m³/h)")
    critical_leakage_threshold: float = Field(0.05, description="临界泄漏压紧比阈值")
    preload_leakage_sensitivity: float = Field(2.5, description="预紧力泄漏敏感度指数")
    seal_aging_factor_per_year: float = Field(0.08, description="密封年老化系数")
    pressure_sensitivity: float = Field(1.2, description="压力敏感度")


class EnergyCarbonParamsSchema(BaseModel):
    """能耗与碳排增量模型参数"""
    energy_per_leakage_unit: float = Field(8.5, description="单位泄漏能耗 (kWh/m³)")
    carbon_factor_electricity: float = Field(0.5839, description="电力排放因子 (kgCO₂e/kWh)")
    carbon_factor_natural_gas: float = Field(2.1622, description="天然气排放因子 (kgCO₂e/kWh)")
    carbon_factor_steam: float = Field(0.11, description="蒸汽排放因子 (kgCO₂e/kWh)")
    compressor_efficiency: float = Field(0.75, description="压缩机效率 0-1")
    recovery_rate: float = Field(0.0, description="泄漏回收率 0-1")
    base_monthly_energy_kwh: float = Field(10000.0, description="基准月度能耗 (kWh)")
    base_monthly_carbon_kg: float = Field(5839.0, description="基准月度碳排 (kgCO₂e)")


class CarbonModelConfigResponse(BaseModel):
    """碳排模型系数配置响应"""
    degradation: DegradationParamsSchema = Field(..., description="预紧力劣化模型参数")
    leakage: LeakageParamsSchema = Field(..., description="泄漏率估算模型参数")
    energy_carbon: EnergyCarbonParamsSchema = Field(..., description="能耗与碳排模型参数")


class CarbonModelConfigUpdateRequest(BaseModel):
    """碳排模型系数配置更新请求"""
    degradation: Optional[DegradationParamsSchema] = Field(None, description="预紧力劣化模型参数（可选更新）")
    leakage: Optional[LeakageParamsSchema] = Field(None, description="泄漏率估算模型参数（可选更新）")
    energy_carbon: Optional[EnergyCarbonParamsSchema] = Field(None, description="能耗与碳排模型参数（可选更新）")
    operator_id: Optional[str] = Field(None, description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")
    description: Optional[str] = Field(None, description="变更说明")


# ============================================================
# 合规与检验标准检查引擎
# ============================================================

class ChecklistItemSchema(BaseModel):
    """检验清单条目"""
    item_code: str = Field(..., description="检验项编码")
    content: str = Field(..., description="检验内容")
    is_mandatory: bool = Field(False, description="是否必检项")
    severity: str = Field("medium", description="严重度 critical/high/medium/low")
    inspection_method: Optional[str] = Field(None, description="检验方法")
    acceptance_criteria: Optional[str] = Field(None, description="合格标准")
    standard_code: Optional[str] = Field(None, description="所属标准编码")
    standard_name: Optional[str] = Field(None, description="所属标准名称")
    checked: bool = Field(False, description="是否已检验")
    auto_checked: bool = Field(False, description="是否自动勾选")
    result: Optional[str] = Field(None, description="检验结果 pass/fail/auto_required/na")
    evidence: Optional[Dict[str, Any]] = Field(None, description="检验证据（含预测证据截图数据）")
    inspector_id: Optional[str] = Field(None, description="检验人ID")
    inspector_name: Optional[str] = Field(None, description="检验人姓名")
    inspect_time: Optional[str] = Field(None, description="检验时间")
    remarks: Optional[str] = Field(None, description="备注")


class StandardTemplateCreateRequest(BaseModel):
    """创建标准模板请求"""
    code: str = Field(..., min_length=1, max_length=64, description="标准编码")
    name: str = Field(..., min_length=1, max_length=256, description="标准名称")
    description: Optional[str] = Field(None, description="标准描述")
    version: Optional[str] = Field("1.0", description="标准版本")
    category: Optional[str] = Field("general", description="装置类别")
    checklist_items: List[ChecklistItemSchema] = Field(default_factory=list, description="检验清单条目")


class StandardTemplateUpdateRequest(BaseModel):
    """更新标准模板请求"""
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    checklist_items: Optional[List[ChecklistItemSchema]] = None


class StandardTemplateResponse(BaseModel):
    """标准模板响应"""
    id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    category: Optional[str] = None
    checklist_items: List[ChecklistItemSchema] = Field(default_factory=list)
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class StandardTemplateListResponse(BaseModel):
    """标准模板列表响应"""
    total: int
    items: List[StandardTemplateResponse]


class InspectionTaskCreateRequest(BaseModel):
    """创建检验任务请求"""
    work_order_id: int = Field(..., description="关联工单ID")
    equipment_type: str = Field(..., description="装置类型")
    standard_codes: Optional[List[str]] = Field(None, description="适用标准编码列表（空则按装置类型自动匹配）")
    node_type: Optional[str] = Field(None, description="节点类型 bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID")
    alert_level: Optional[int] = Field(None, ge=1, le=4, description="关联预警级别")
    auto_check_mandatory: bool = Field(True, description="紧急预警时是否自动勾选必检项")


class InspectionItemCheckRequest(BaseModel):
    """检验项勾选请求"""
    item_code: str = Field(..., description="检验项编码")
    result: str = Field(..., description="检验结果 pass/fail/na")
    inspector_id: Optional[str] = Field(None, description="检验人ID")
    inspector_name: Optional[str] = Field(None, description="检验人姓名")
    evidence: Optional[Dict[str, Any]] = Field(None, description="检验证据（含预测证据截图数据字段）")
    remarks: Optional[str] = Field(None, description="备注")


class AutoCheckMandatoryRequest(BaseModel):
    """自动勾选必检项请求"""
    alert_level: int = Field(..., ge=1, le=4, description="预警级别")
    prediction_evidence: Optional[Dict[str, Any]] = Field(None, description="预测证据数据（含截图数据）")


class InspectionTaskResponse(BaseModel):
    """检验任务响应"""
    id: int
    task_no: str
    work_order_id: Optional[int] = None
    equipment_type: Optional[str] = None
    standard_codes: List[str] = Field(default_factory=list)
    checklist_items: List[ChecklistItemSchema] = Field(default_factory=list)
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    alert_level: Optional[int] = None
    completion_score: float = 0.0
    status: str = "pending"
    auto_check_mandatory: bool = True
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class InspectionTaskListResponse(BaseModel):
    """检验任务列表响应"""
    total: int
    items: List[InspectionTaskResponse]


class WorkOrderCloseCheckResponse(BaseModel):
    """工单关闭检查响应"""
    can_close: bool
    completion_score: float = 0.0
    min_required_score: float = 80.0
    mandatory_unchecked: List[Dict[str, Any]] = Field(default_factory=list)
    mandatory_unchecked_count: int = 0
    reason: str = ""


class InspectionPdfExportResponse(BaseModel):
    """检验PDF导出响应"""
    html_content: str = Field(..., description="HTML内容，可直接转PDF")
    export_time: str


# ============================================================
# 备件库存与 RUL 联动模块
# ============================================================

# ---------- 螺栓-SKU 映射 ----------

class BoltSkuMappingCreate(BaseModel):
    """创建螺栓-SKU映射请求"""
    bolt_model: str = Field(..., description="螺栓型号", max_length=100)
    bolt_spec: Optional[str] = Field(None, description="螺栓规格描述", max_length=200)
    material: Optional[str] = Field(None, description="材质", max_length=100)
    standard: Optional[str] = Field(None, description="标准（如GB/T、DIN）", max_length=100)
    diameter: Optional[float] = Field(None, description="公称直径(mm)")
    length: Optional[float] = Field(None, description="公称长度(mm)")
    grade: Optional[str] = Field(None, description="性能等级", max_length=50)
    sku_code: str = Field(..., description="备件SKU编码", max_length=100)
    sku_name: str = Field(..., description="备件名称", max_length=200)
    unit: Optional[str] = Field("个", description="计量单位", max_length=20)
    unit_price: Optional[float] = Field(None, description="单价")
    supplier: Optional[str] = Field(None, description="供应商", max_length=200)
    manufacturer: Optional[str] = Field(None, description="生产厂家", max_length=200)
    lead_time_days: Optional[int] = Field(7, description="采购周期(天)")
    min_order_qty: Optional[int] = Field(1, description="最小订货量")
    is_active: Optional[bool] = Field(True, description="是否启用")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class BoltSkuMappingUpdate(BaseModel):
    """更新螺栓-SKU映射请求"""
    bolt_model: Optional[str] = Field(None, description="螺栓型号")
    bolt_spec: Optional[str] = Field(None, description="螺栓规格描述")
    material: Optional[str] = Field(None, description="材质")
    standard: Optional[str] = Field(None, description="标准")
    diameter: Optional[float] = Field(None, description="公称直径(mm)")
    length: Optional[float] = Field(None, description="公称长度(mm)")
    grade: Optional[str] = Field(None, description="性能等级")
    sku_name: Optional[str] = Field(None, description="备件名称")
    unit: Optional[str] = Field(None, description="计量单位")
    unit_price: Optional[float] = Field(None, description="单价")
    supplier: Optional[str] = Field(None, description="供应商")
    manufacturer: Optional[str] = Field(None, description="生产厂家")
    lead_time_days: Optional[int] = Field(None, description="采购周期(天)")
    min_order_qty: Optional[int] = Field(None, description="最小订货量")
    is_active: Optional[bool] = Field(None, description="是否启用")


class BoltSkuMappingResponse(BaseModel):
    """螺栓-SKU映射响应"""
    id: int
    bolt_model: str
    bolt_spec: Optional[str] = None
    material: Optional[str] = None
    standard: Optional[str] = None
    diameter: Optional[float] = None
    length: Optional[float] = None
    grade: Optional[str] = None
    sku_code: str
    sku_name: str
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    supplier: Optional[str] = None
    manufacturer: Optional[str] = None
    lead_time_days: Optional[int] = None
    min_order_qty: Optional[int] = None
    is_active: bool
    tenant_id: Optional[int] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class BoltSkuMappingListResponse(BaseModel):
    """螺栓-SKU映射列表响应"""
    total: int
    items: List[BoltSkuMappingResponse]


class BoltSkuQueryRequest(BaseModel):
    """螺栓-SKU映射查询请求"""
    bolt_model: Optional[str] = Field(None, description="螺栓型号（模糊匹配）")
    sku_code: Optional[str] = Field(None, description="SKU编码（精确匹配）")
    material: Optional[str] = Field(None, description="材质")
    standard: Optional[str] = Field(None, description="标准")
    is_active: Optional[bool] = Field(None, description="是否启用")
    limit: int = Field(100, ge=1, le=500, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


# ---------- 库存查询 ----------

class SparePartInventoryResponse(BaseModel):
    """备件库存响应"""
    id: int
    sku_code: str
    sku_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    quantity_on_order: int
    reorder_point: Optional[int] = None
    safety_stock: Optional[int] = None
    abc_category: Optional[str] = None
    turnover_rate: Optional[float] = None
    unit_price: Optional[float] = None
    stock_value: Optional[float] = None
    tenant_id: Optional[int] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class SparePartInventoryListResponse(BaseModel):
    """备件库存列表响应"""
    total: int
    items: List[SparePartInventoryResponse]


class StockAvailabilityCheckResponse(BaseModel):
    """库存可用性检查响应"""
    sku_code: str
    sku_name: Optional[str] = None
    required_quantity: int
    is_available: bool
    stock_status: str
    available_quantity: int
    shortage_quantity: int
    warehouse_code: Optional[str] = None
    reorder_point: Optional[int] = None
    safety_stock: Optional[int] = None
    unit_price: Optional[float] = None
    shortage_cost: Optional[float] = None


# ---------- 备件需求 ----------

class SparePartDemandFromRulRequest(BaseModel):
    """根据RUL生成备件需求请求"""
    bolt_id: str = Field(..., description="螺栓ID")
    bolt_model: str = Field(..., description="螺栓型号")
    rul_days: float = Field(..., description="RUL剩余天数", ge=0)
    current_hi: Optional[float] = Field(None, description="当前健康度指数")
    failure_threshold: Optional[float] = Field(30, description="故障阈值HI")
    estimated_failure_date: Optional[datetime] = Field(None, description="预计故障日期")
    node_type: Optional[str] = Field("bolt", description="节点类型")
    device_id: Optional[str] = Field(None, description="装置ID")
    device_name: Optional[str] = Field(None, description="装置名称")
    required_quantity: Optional[int] = Field(1, description="需求数量", ge=1)
    source_type: Optional[str] = Field("rul", description="需求来源")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class SparePartDemandResponse(BaseModel):
    """备件需求响应"""
    id: int
    demand_no: str
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    bolt_model: Optional[str] = None
    sku_code: str
    sku_name: Optional[str] = None
    required_quantity: int
    urgency: Optional[str] = None
    priority: Optional[int] = None
    rul_days: Optional[float] = None
    estimated_failure_date: Optional[datetime] = None
    required_date: Optional[datetime] = None
    stock_status: Optional[str] = None
    available_quantity: Optional[int] = None
    shortage_quantity: Optional[int] = None
    work_order_id: Optional[int] = None
    work_order_priority_upgraded: Optional[bool] = None
    status: Optional[str] = None
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    approved_by: Optional[str] = None
    approved_time: Optional[datetime] = None
    fulfilled_by: Optional[str] = None
    fulfilled_time: Optional[datetime] = None
    tenant_id: Optional[int] = None
    extra_info: Optional[Dict[str, Any]] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class SparePartDemandListResponse(BaseModel):
    """备件需求列表响应"""
    total: int
    items: List[SparePartDemandResponse]


class SparePartDemandApproveRequest(BaseModel):
    """审批备件需求请求"""
    demand_id: int = Field(..., description="需求ID")
    approved: bool = Field(..., description="是否批准")
    approver_id: Optional[str] = Field(None, description="审批人ID")
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    comment: Optional[str] = Field(None, description="审批意见")


class SparePartDemandFulfillRequest(BaseModel):
    """完成备件需求请求"""
    demand_id: int = Field(..., description="需求ID")
    fulfilled_quantity: Optional[int] = Field(None, description="实际发放数量，默认等于需求数量")
    fulfiller_id: Optional[str] = Field(None, description="发放人ID")
    fulfiller_name: Optional[str] = Field(None, description="发放人姓名")
    warehouse_code: Optional[str] = Field(None, description="仓库编码")


class SparePartRulScanRequest(BaseModel):
    """批量扫描RUL生成备件需求请求"""
    rul_threshold_days: Optional[int] = Field(30, description="RUL阈值天数")
    device_id: Optional[str] = Field(None, description="装置ID，None表示全部")
    auto_create_work_order: Optional[bool] = Field(True, description="缺货时是否自动创建工单")
    auto_upgrade_priority: Optional[bool] = Field(True, description="缺货时是否自动升级工单优先级")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class SparePartRulScanResponse(BaseModel):
    """批量扫描RUL响应"""
    scanned_count: int
    below_threshold_count: int
    new_demands_created: int
    work_orders_created: int
    work_orders_upgraded: int
    skipped_demands: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime


# ---------- 装置需求汇总 ----------

class SparePartDemandSummaryRequest(BaseModel):
    """生成装置需求汇总请求"""
    device_id: str = Field(..., description="装置ID")
    device_name: Optional[str] = Field(None, description="装置名称")
    include_pending: Optional[bool] = Field(True, description="是否包含待处理需求")
    include_approved: Optional[bool] = Field(True, description="是否包含已批准需求")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class SparePartDemandSummaryResponse(BaseModel):
    """装置需求汇总响应"""
    id: int
    summary_no: str
    device_id: str
    device_name: Optional[str] = None
    report_period_start: datetime
    report_period_end: datetime
    total_sku_types: int
    total_quantity: int
    total_value: Optional[float] = None
    shortage_sku_count: int
    urgent_demand_count: int
    critical_demand_count: int
    normal_demand_count: int
    demand_details: Optional[List[Dict[str, Any]]] = None
    stock_analysis: Optional[Dict[str, Any]] = None
    purchase_recommendations: Optional[List[Dict[str, Any]]] = None
    generated_by: Optional[str] = None
    tenant_id: Optional[int] = None
    extra_info: Optional[Dict[str, Any]] = None
    create_time: datetime

    class Config:
        from_attributes = True


class SparePartDemandSummaryListResponse(BaseModel):
    """装置需求汇总列表响应"""
    total: int
    items: List[SparePartDemandSummaryResponse]


# ---------- 采购优化 ----------

class PurchaseAnalysisRequest(BaseModel):
    """采购分析请求"""
    sku_code: str = Field(..., description="SKU编码")
    service_level: Optional[float] = Field(None, description="服务水平 0-1", ge=0, le=1)
    safety_stock_days: Optional[int] = Field(None, description="安全库存天数", ge=1)


class PurchaseAnalysisResponse(BaseModel):
    """采购分析响应"""
    sku_code: str
    sku_name: Optional[str] = None
    unit_price: Optional[float] = None
    abc_category: Optional[str] = None
    demand_statistics: Dict[str, Any]
    lead_time_statistics: Dict[str, Any]
    safety_stock: Dict[str, Any]
    eoq: Dict[str, Any]
    reorder_point: Dict[str, Any]
    recommendations: List[Dict[str, Any]]


class PurchaseConfigSaveRequest(BaseModel):
    """保存采购配置请求"""
    sku_code: str = Field(..., description="SKU编码")
    service_level: Optional[float] = Field(None, description="服务水平", ge=0, le=1)
    safety_stock_days: Optional[int] = Field(None, description="安全库存天数", ge=1)
    lead_time_days: Optional[int] = Field(None, description="提前期(天)", ge=1)
    review_period_days: Optional[int] = Field(None, description="盘点周期(天)", ge=1)
    min_order_qty: Optional[int] = Field(None, description="最小订货量", ge=1)
    max_order_qty: Optional[int] = Field(None, description="最大订货量", ge=1)
    order_cost: Optional[float] = Field(None, description="单次订货成本", ge=0)
    holding_cost_rate: Optional[float] = Field(None, description="持有成本率", ge=0, le=1)
    description: Optional[str] = Field(None, description="备注")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class PurchaseConfigResponse(BaseModel):
    """采购配置响应"""
    id: int
    sku_code: str
    sku_name: Optional[str] = None
    abc_category: Optional[str] = None
    lead_time_days: Optional[int] = None
    review_period_days: Optional[int] = None
    avg_daily_consumption: Optional[float] = None
    max_daily_consumption: Optional[float] = None
    safety_stock_days: Optional[int] = None
    calculated_safety_stock: Optional[int] = None
    reorder_point: Optional[int] = None
    economic_order_qty: Optional[int] = None
    min_order_qty: Optional[int] = None
    max_order_qty: Optional[int] = None
    order_cost: Optional[float] = None
    holding_cost_rate: Optional[float] = None
    unit_price: Optional[float] = None
    service_level: Optional[float] = None
    demand_variability: Optional[float] = None
    lead_time_variability: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    tenant_id: Optional[int] = None
    extra_info: Optional[Dict[str, Any]] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class PurchasePlanRequest(BaseModel):
    """生成采购计划请求"""
    device_id: Optional[str] = Field(None, description="装置ID，None表示全部")
    include_rul_demand: Optional[bool] = Field(True, description="是否包含基于RUL的预测需求")
    tenant_id: Optional[int] = Field(None, description="租户ID")


class PurchasePlanResponse(BaseModel):
    """采购计划响应"""
    plan_id: str
    generated_time: datetime
    device_id: Optional[str] = None
    include_rul_demand: bool
    total_items: int
    total_estimated_cost: float
    items: List[Dict[str, Any]]
    summary: Dict[str, Any]


# ==================== 3D数字孪生可视化 ====================

class BoltStatusDataSchema(BaseModel):
    """螺栓状态数据（用于3D可视化）"""
    bolt_id: str = Field(..., description="螺栓ID")
    status_code: Optional[int] = Field(None, description="状态代码 0-4")
    status: Optional[str] = Field(None, description="状态名称")
    hi_score: Optional[float] = Field(None, description="健康度HI分数 0-100")
    hi_level: Optional[str] = Field(None, description="健康等级")
    risk_level: Optional[str] = Field(None, description="风险等级 low/medium/high/critical")
    risk_score: Optional[float] = Field(None, description="风险评分 1-10")
    confidence: Optional[float] = Field(None, description="置信度 0-1")
    diagnosis: Optional[str] = Field(None, description="诊断结论")
    recommendations: Optional[List[str]] = Field(None, description="推荐措施")


class Flange3DCreateRequest(BaseModel):
    """创建法兰3D场景请求"""
    flange_id: str = Field(..., description="法兰面ID")
    bolt_ids: Optional[List[str]] = Field(None, description="螺栓ID列表")
    bolt_count: Optional[int] = Field(8, description="螺栓数量（bolt_ids为空时使用）")
    bolt_data: Optional[List[BoltStatusDataSchema]] = Field(None, description="螺栓状态数据列表")
    bolt_coordinate_csv: Optional[str] = Field(None, description="螺栓坐标映射表CSV内容")
    bolt_coordinate_json: Optional[str] = Field(None, description="螺栓坐标映射表JSON内容")
    visualization_mode: Optional[str] = Field("status", description="可视化模式: status/hi/risk")
    flange_params: Optional[Dict[str, Any]] = Field(None, description="法兰模型参数")

    class Config:
        json_schema_extra = {
            "example": {
                "flange_id": "FL001",
                "bolt_count": 8,
                "visualization_mode": "status",
                "bolt_data": [
                    {"bolt_id": "B001", "status_code": 0, "hi_score": 95.0, "risk_level": "low"},
                    {"bolt_id": "B002", "status_code": 2, "hi_score": 60.0, "risk_level": "medium"},
                ]
            }
        }


class Flange3DExportRequest(BaseModel):
    """导出法兰3D场景请求"""
    flange_id: str = Field(..., description="法兰面ID")
    format: Optional[str] = Field("threejs", description="导出格式: gltf/threejs/unity/all")
    visualization_mode: Optional[str] = Field(None, description="可视化模式（可选，不填则使用原模式）")


class Flange3DUpdateRequest(BaseModel):
    """更新螺栓状态（增量更新）请求"""
    flange_id: str = Field(..., description="法兰面ID")
    bolt_data: List[BoltStatusDataSchema] = Field(..., description="螺栓状态数据列表")
    visualization_mode: Optional[str] = Field(None, description="可视化模式（可选）")


class Flange3DExplosionRequest(BaseModel):
    """爆炸图位置请求"""
    flange_id: str = Field(..., description="法兰面ID")
    explosion_factor: Optional[float] = Field(1.0, description="爆炸因子 0-1")


class BoltCoordinateItemSchema(BaseModel):
    """螺栓坐标项"""
    bolt_id: str
    x: float
    y: float
    z: float
    angle: Optional[float] = None
    radius: Optional[float] = None
    position_index: Optional[int] = None


class Flange3DSceneInfoResponse(BaseModel):
    """法兰3D场景信息响应"""
    flange_id: str
    visualization_mode: str
    bolt_count: int
    bolt_ids: List[str]
    flange_params: Dict[str, Any]
    bolt_coordinates: List[BoltCoordinateItemSchema]


class Flange3DExportResponse(BaseModel):
    """法兰3D导出响应"""
    flange_id: str
    format: str
    visualization_mode: str
    export_time: datetime
    data: Dict[str, Any]


class Flange3DUpdateResponse(BaseModel):
    """螺栓状态更新响应"""
    flange_id: str
    updated_count: int
    visualization_mode: str
    bolt_updates: List[Dict[str, Any]]
    update_time: datetime


class Flange3DExplosionResponse(BaseModel):
    """爆炸图位置响应"""
    flange_id: str
    explosion_factor: float
    bolt_positions: Dict[str, List[float]]


class Flange3DListResponse(BaseModel):
    """3D场景列表响应"""
    total: int
    scenes: List[str]


# ============================================================
# 超参优化 (HPO) 模块
# ============================================================

# ---------- 搜索空间配置 ----------

class SearchSpaceParamSchema(BaseModel):
    """搜索空间单个参数配置"""
    param_type: str = Field(..., description="参数类型: INT/FLOAT/CATEGORICAL/LOG_UNIFORM/DISCRETE_UNIFORM")
    low: Optional[float] = Field(None, description="最小值")
    high: Optional[float] = Field(None, description="最大值")
    choices: Optional[List[Any]] = Field(None, description="可选值列表，用于 CATEGORICAL")
    q: Optional[float] = Field(None, description="步长，用于 DISCRETE_UNIFORM")
    step: Optional[int] = Field(None, description="整数步长，用于 INT")
    log: Optional[bool] = Field(False, description="是否对数空间")


class SearchSpaceSchema(BaseModel):
    """搜索空间配置"""
    num_layers: Optional[SearchSpaceParamSchema] = Field(None, description="层数搜索空间")
    hidden_size: Optional[SearchSpaceParamSchema] = Field(None, description="隐藏层大小搜索空间")
    dropout_rate: Optional[SearchSpaceParamSchema] = Field(None, description="Dropout率搜索空间")
    learning_rate: Optional[SearchSpaceParamSchema] = Field(None, description="学习率搜索空间")
    sequence_length: Optional[SearchSpaceParamSchema] = Field(None, description="序列长度搜索空间")
    custom_params: Optional[Dict[str, SearchSpaceParamSchema]] = Field(None, description="自定义搜索参数")
    fixed_params: Optional[Dict[str, Any]] = Field(None, description="固定参数值，不参与搜索")


# ---------- 优化目标配置 ----------

class ObjectiveConfigSchema(BaseModel):
    """优化目标配置"""
    f1_weight: float = Field(1.0, ge=0, le=10, description="F1分数权重")
    false_positive_penalty: float = Field(0.5, ge=0, le=10, description="误报惩罚系数")
    latency_weight: float = Field(0.3, ge=0, le=10, description="推理延迟权重")
    latency_threshold_ms: float = Field(100.0, gt=0, description="推理延迟阈值(ms)")
    f1_min_threshold: Optional[float] = Field(None, ge=0, le=1, description="F1最小阈值约束")
    latency_max_penalty: float = Field(1.0, ge=0, description="延迟最大惩罚系数")
    false_negative_penalty: Optional[float] = Field(0.3, ge=0, description="漏报惩罚系数")


# ---------- 请求模型 ----------

class HPOCreateStudyRequest(BaseModel):
    """创建HPO研究请求"""
    study_name: str = Field(..., description="研究名称", min_length=1, max_length=200)
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID，空表示全局")
    node_type: Optional[str] = Field(None, description="节点类型")
    framework: str = Field("optuna", description="优化框架: optuna/ray_tune")
    optimizer: str = Field("tpe", description="优化算法: tpe/random/cmaes/grid/asha/bayesopt")
    max_trials: int = Field(50, ge=1, le=1000, description="最大试验次数")
    max_concurrent_trials: int = Field(2, ge=1, le=32, description="最大并发试验数")
    min_trials_to_prune: int = Field(5, ge=0, description="开始剪枝的最小试验数")
    pruner_type: str = Field("median", description="剪枝类型: median/hyperband/none")
    search_space: Optional[SearchSpaceSchema] = Field(None, description="自定义搜索空间")
    objective_config: Optional[ObjectiveConfigSchema] = Field(None, description="自定义优化目标配置")
    per_node_hpo_enabled: bool = Field(False, description="是否启用per-node超参优化")
    node_scope: str = Field("global", description="节点范围: global/per_node_type/per_node")
    created_by: Optional[str] = Field(None, description="创建人")
    tenant_id: int = Field(0, description="租户ID")

    class Config:
        json_schema_extra = {
            "example": {
                "study_name": "螺栓模型LSTM调参",
                "model_type": "bolt",
                "framework": "optuna",
                "optimizer": "tpe",
                "max_trials": 50,
                "max_concurrent_trials": 2,
                "objective_config": {
                    "f1_weight": 1.0,
                    "false_positive_penalty": 0.5,
                    "latency_threshold_ms": 100.0,
                    "latency_weight": 0.3
                }
            }
        }


class HPOStartStudyRequest(BaseModel):
    """启动HPO研究请求"""
    study_id: str = Field(..., description="研究ID")
    auto_apply_best: bool = Field(True, description="是否自动应用最优配置")


class HPOApplyConfigRequest(BaseModel):
    """应用最优配置请求"""
    study_id: str = Field(..., description="研究ID")
    node_ids: Optional[List[str]] = Field(None, description="指定节点ID列表，空则应用到研究关联的节点")


class HPOSetNodeOverrideRequest(BaseModel):
    """设置节点超参覆盖请求"""
    study_id: str = Field(..., description="研究ID")
    node_id: str = Field(..., description="节点ID")
    node_type: str = Field(..., description="节点类型")
    search_space_override: Optional[SearchSpaceSchema] = Field(None, description="搜索空间覆盖")
    fixed_params: Optional[Dict[str, Any]] = Field(None, description="固定参数值")
    tenant_id: int = Field(0, description="租户ID")


# ---------- 响应模型 ----------

class HPOTrialSchema(BaseModel):
    """试验记录"""
    trial_id: str
    study_id: str
    model_type: str
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    framework: str
    status: str
    trial_number: int
    num_layers: Optional[int] = None
    hidden_size: Optional[int] = None
    dropout_rate: Optional[float] = None
    learning_rate: Optional[float] = None
    sequence_length: Optional[int] = None
    params: Optional[Dict[str, Any]] = None
    val_f1_score: Optional[float] = None
    val_precision: Optional[float] = None
    val_recall: Optional[float] = None
    false_positive_rate: Optional[float] = None
    false_negative_rate: Optional[float] = None
    inference_latency_ms: Optional[float] = None
    training_time_seconds: Optional[float] = None
    objective_value: Optional[float] = None
    latency_constraint_violated: Optional[bool] = None
    f1_constraint_violated: Optional[bool] = None
    training_session_id: Optional[str] = None
    error_message: Optional[str] = None
    pruned_reason: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


class HPOStudySchema(BaseModel):
    """研究记录"""
    study_id: str
    study_name: str
    model_type: str
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    framework: str
    optimizer: str
    max_trials: int
    max_concurrent_trials: int
    status: str
    search_space: Optional[Dict[str, Any]] = None
    objective_config: Optional[Dict[str, Any]] = None
    f1_weight: float
    false_positive_penalty: float
    latency_threshold_ms: float
    latency_weight: float
    best_trial_id: Optional[str] = None
    best_params: Optional[Dict[str, Any]] = None
    best_objective_value: Optional[float] = None
    per_node_hpo_enabled: bool
    node_scope: str
    created_by: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    create_time: datetime
    update_time: datetime


class HPONodeOverrideSchema(BaseModel):
    """节点超参覆盖记录"""
    study_id: str
    node_id: str
    node_type: str
    search_space_override: Optional[Dict[str, Any]] = None
    fixed_params: Optional[Dict[str, Any]] = None
    best_params: Optional[Dict[str, Any]] = None
    best_trial_id: Optional[str] = None
    best_objective_value: Optional[float] = None
    applied_to_training: bool
    applied_time: Optional[datetime] = None
    create_time: datetime
    update_time: datetime


class HPOCreateStudyResponse(BaseModel):
    """创建HPO研究响应"""
    success: bool
    message: str
    study_id: str
    study_name: str
    model_type: str
    framework: str
    search_space: Dict[str, Any]
    objective_config: Dict[str, Any]
    max_trials: int
    per_node_hpo_enabled: bool


class HPOStartStudyResponse(BaseModel):
    """启动HPO研究响应"""
    study_id: str
    status: str
    message: str
    best_params: Optional[Dict[str, Any]] = None
    best_value: Optional[float] = None
    total_trials: Optional[int] = None
    auto_apply_result: Optional[Dict[str, Any]] = None


class HPOStudyStatusResponse(BaseModel):
    """研究状态响应"""
    success: bool
    study: HPOStudySchema
    trials: Dict[str, Any]
    best_trial: Optional[HPOTrialSchema] = None


class HPOStudyListResponse(BaseModel):
    """研究列表响应"""
    success: bool
    total: int
    studies: List[HPOStudySchema]


class HPOTrialListResponse(BaseModel):
    """试验列表响应"""
    success: bool
    total: int
    trials: List[HPOTrialSchema]


class HPOApplyConfigResponse(BaseModel):
    """应用最优配置响应"""
    success: Optional[bool] = None
    message: Optional[str] = None
    model_type: Optional[str] = None
    node_id: Optional[str] = None
    best_params: Optional[Dict[str, Any]] = None
    objective_value: Optional[float] = None
    training_config: Optional[Dict[str, Any]] = None
    saved_to_db: Optional[bool] = None
    total: Optional[int] = None
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    success: Optional[List[str]] = None
    failed: Optional[List[Dict[str, Any]]] = None


class HPOCompareConfigResponse(BaseModel):
    """配置比较响应"""
    success: bool
    best_params: Dict[str, Any]
    best_metrics: Dict[str, Any]
    current_params: Optional[Dict[str, Any]] = None
    current_metrics: Optional[Dict[str, Any]] = None
    param_changes: Dict[str, Any]
    metric_changes: Dict[str, Any]
    has_changes: bool
    improvement: float


class HPONodeOverrideResponse(BaseModel):
    """节点超参覆盖响应"""
    success: bool
    message: str
    study_id: Optional[str] = None
    node_id: Optional[str] = None
    search_space_override: Optional[Dict[str, Any]] = None
    fixed_params: Optional[Dict[str, Any]] = None


# ============================================================
# 风险热力图与传播可视化
# ============================================================

# ---------- 图节点 ----------

class RiskGraphNodeSchema(BaseModel):
    """风险图节点"""
    id: str
    name: str
    node_type: str
    level: int
    risk_score: float
    risk_level: str
    status_code: int
    status: str
    confidence: float
    parent_id: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    extra_info: Optional[Dict[str, Any]] = None


# ---------- 图边 ----------

class RiskGraphEdgeSchema(BaseModel):
    """风险图边"""
    source: str
    target: str
    weight: float
    weight_type: str
    co_fault_weight: float = 0.0
    physical_weight: float = 0.0
    granger_weight: float = 0.0
    granger_p_value: Optional[float] = None
    granger_lag: Optional[int] = None
    co_fault_count: int = 0
    extra_info: Optional[Dict[str, Any]] = None


# ---------- 传播图 ----------

class PropagationGraphResponse(BaseModel):
    """传播图响应"""
    nodes: List[RiskGraphNodeSchema]
    edges: List[RiskGraphEdgeSchema]
    node_count: int
    edge_count: int
    graph_type: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


# ---------- GeoJSON 热力图 ----------

class GeoJSONHeatmapRequest(BaseModel):
    """GeoJSON热力图请求"""
    tenant_id: int = Field(..., description="租户ID")
    node_type: Optional[str] = Field("all", description="节点类型: all/bolt/flange/unit")
    value_field: Optional[str] = Field("risk_score", description="热力值字段")
    aggregate_level: Optional[str] = Field(None, description="聚合层级: group/factory/unit/flange")


# ---------- ECharts 图结构 ----------

class EChartsGraphRequest(BaseModel):
    """ECharts图结构请求"""
    tenant_id: int = Field(..., description="租户ID")
    graph_type: Optional[str] = Field("composite", description="图类型")
    layout: Optional[str] = Field("force", description="布局类型: force/circular/none")
    include_levels: Optional[List[str]] = Field(None, description="包含的节点级别")


class EChartsGraphResponse(BaseModel):
    """ECharts图结构响应"""
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    categories: List[Dict[str, str]]
    layout: str
    metadata: Dict[str, Any]


# ---------- 时间切片 ----------

class TimeSliceRequest(BaseModel):
    """时间切片请求"""
    tenant_id: int = Field(..., description="租户ID")
    history_hours: Optional[int] = Field(24, description="历史时长（小时）", ge=1, le=168)
    interval_minutes: Optional[int] = Field(60, description="时间间隔（分钟）", ge=5, le=360)
    include_edges: Optional[bool] = Field(False, description="是否包含边")
    use_mock: Optional[bool] = Field(True, description="是否使用模拟数据")


class TimeSliceNodeSchema(BaseModel):
    """时间切片节点"""
    id: str
    name: str
    node_type: str
    level: int
    risk_score: float
    risk_level: str
    status_code: int
    status: str
    confidence: float
    parent_id: Optional[str] = None


class TimeSliceDataSchema(BaseModel):
    """时间切片数据"""
    timestamp: str
    slice_index: int
    nodes: List[TimeSliceNodeSchema]
    edges: Optional[List[RiskGraphEdgeSchema]] = None
    stats: Optional[Dict[str, Any]] = None


class TimeSeriesResponse(BaseModel):
    """时间序列响应"""
    time_slices: List[TimeSliceDataSchema]
    total_slices: int
    time_range: Dict[str, str]
    interval_minutes: int
    metadata: Dict[str, Any]


# ---------- 传播路径 ----------

class PropagationPathRequest(BaseModel):
    """传播路径请求"""
    tenant_id: int = Field(..., description="租户ID")
    source_node: str = Field(..., description="源节点ID")
    top_k: Optional[int] = Field(10, description="返回前k条路径", ge=1, le=100)
    max_depth: Optional[int] = Field(3, description="最大路径深度", ge=1, le=10)


class PropagationPathSchema(BaseModel):
    """传播路径"""
    path: List[str]
    total_weight: float
    avg_weight: float
    depth: int


class PropagationPathListResponse(BaseModel):
    """传播路径列表响应"""
    source_node: str
    total_paths: int
    paths: List[PropagationPathSchema]


# ---------- 风险汇总 ----------

class RiskSummaryResponse(BaseModel):
    """风险汇总响应"""
    total_nodes: int
    total_edges: int
    avg_risk_score: float
    max_risk_score: float
    min_risk_score: float
    risk_distribution: Dict[str, int]
    high_risk_ratio: float
    high_risk_nodes: List[RiskGraphNodeSchema]
    timestamp: str


# ---------- 边权重配置 ----------

class EdgeWeightConfigRequest(BaseModel):
    """边权重配置请求"""
    co_fault_weight: Optional[float] = Field(None, description="共故障权重", ge=0, le=1)
    physical_weight: Optional[float] = Field(None, description="物理邻接权重", ge=0, le=1)
    granger_weight: Optional[float] = Field(None, description="Granger因果权重", ge=0, le=1)


class EdgeWeightConfigResponse(BaseModel):
    """边权重配置响应"""
    co_fault_weight: float
    physical_weight: float
    granger_weight: float


# ---------- 显著变化检测 ----------

class SignificantChangeRequest(BaseModel):
    """显著变化检测请求"""
    tenant_id: int = Field(..., description="租户ID")
    threshold: Optional[float] = Field(2.0, description="变化阈值", gt=0, le=10)
    history_hours: Optional[int] = Field(24, description="历史时长（小时）")
    use_mock: Optional[bool] = Field(True, description="是否使用模拟数据")


class SignificantChangeItemSchema(BaseModel):
    """显著变化项"""
    node_id: str
    node_name: str
    prev_risk: float
    curr_risk: float
    delta: float
    direction: str


class SignificantChangeSliceSchema(BaseModel):
    """显著变化切片"""
    slice_index: int
    timestamp: str
    change_count: int
    changes: List[SignificantChangeItemSchema]


class SignificantChangeListResponse(BaseModel):
    """显著变化列表响应"""
    total_slices: int
    change_slices: int
    threshold: float
    changes: List[SignificantChangeSliceSchema]


# ---------- WebSocket 消息 ----------

class WSMessageSchema(BaseModel):
    """WebSocket消息"""
    type: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str


# ---------- 增量更新 ----------

class IncrementalUpdateSchema(BaseModel):
    """增量更新"""
    type: str
    data: Dict[str, Any]
