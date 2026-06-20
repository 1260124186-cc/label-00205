"""
模型漂移检测 API 请求和响应模型
"""

from datetime import datetime, date
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ==================== 漂移配置 ====================

class DriftDimensionThresholdsSchema(BaseModel):
    """各维度检测阈值"""
    psi: Optional[float] = Field(0.2, description="PSI阈值，>0.25判定显著漂移")
    ks_p_value: Optional[float] = Field(0.05, description="KS检验p值阈值")
    confidence_drift: Optional[float] = Field(0.15, description="置信度分布漂移KS统计量阈值")
    false_positive_rate: Optional[float] = Field(0.10, description="误报率阈值")
    feature_mean_shift: Optional[float] = Field(2.0, description="特征均值偏移标准差倍数阈值")
    composite_score: Optional[float] = Field(0.6, description="综合漂移分数阈值")


class DriftDimensionWeightsSchema(BaseModel):
    """各维度权重"""
    psi: Optional[float] = Field(0.25, description="PSI维度权重")
    ks: Optional[float] = Field(0.20, description="KS维度权重")
    confidence: Optional[float] = Field(0.25, description="置信度维度权重")
    false_positive: Optional[float] = Field(0.20, description="误报率维度权重")
    feature_shift: Optional[float] = Field(0.10, description="特征偏移维度权重")


class DriftConfigCreateRequest(BaseModel):
    """创建漂移检测配置请求"""
    model_id: str = Field(..., description="模型ID，'default' 表示全局默认")
    model_type: str = Field(..., description="模型类型：bolt / flange")
    enabled: Optional[bool] = Field(True, description="是否启用该模型的漂移检测")
    response_strategy: Optional[str] = Field(
        "notify",
        description="响应策略：notify / shadow_retrain / auto_retrain"
    )
    thresholds: Optional[DriftDimensionThresholdsSchema] = Field(
        default_factory=DriftDimensionThresholdsSchema,
        description="各维度检测阈值"
    )
    weights: Optional[DriftDimensionWeightsSchema] = Field(
        default_factory=DriftDimensionWeightsSchema,
        description="各维度权重"
    )
    consecutive_days_alert: Optional[int] = Field(
        2,
        description="连续N天超阈值才触发响应"
    )
    auto_retrain_min_days: Optional[int] = Field(
        7,
        description="自动重训最小间隔天数"
    )
    notify_channels: Optional[List[str]] = Field(
        default_factory=lambda: ["email"],
        description="通知渠道列表"
    )
    notify_targets: Optional[Dict[str, List[str]]] = Field(
        default_factory=dict,
        description="通知目标（按渠道）"
    )


class DriftConfigUpdateRequest(BaseModel):
    """更新漂移检测配置请求"""
    enabled: Optional[bool] = Field(None, description="是否启用")
    response_strategy: Optional[str] = Field(
        None,
        description="响应策略：notify / shadow_retrain / auto_retrain"
    )
    thresholds: Optional[DriftDimensionThresholdsSchema] = Field(None, description="各维度检测阈值")
    weights: Optional[DriftDimensionWeightsSchema] = Field(None, description="各维度权重")
    consecutive_days_alert: Optional[int] = Field(None, description="连续N天超阈值才触发响应")
    auto_retrain_min_days: Optional[int] = Field(None, description="自动重训最小间隔天数")
    notify_channels: Optional[List[str]] = Field(None, description="通知渠道列表")
    notify_targets: Optional[Dict[str, List[str]]] = Field(None, description="通知目标")


class DriftConfigResponse(BaseModel):
    """漂移检测配置响应"""
    id: Optional[int] = Field(None, description="配置ID")
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型")
    version: Optional[str] = Field(None, description="模型版本")
    enabled: bool = Field(..., description="是否启用")
    response_strategy: str = Field(..., description="响应策略")
    thresholds: Optional[DriftDimensionThresholdsSchema] = Field(None, description="各维度检测阈值")
    weights: Optional[DriftDimensionWeightsSchema] = Field(None, description="各维度权重")
    consecutive_days_alert: Optional[int] = Field(None, description="连续超阈值天数")
    auto_retrain_min_days: Optional[int] = Field(None, description="自动重训最小间隔")
    notify_channels: Optional[List[str]] = Field(None, description="通知渠道")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class DriftConfigListResponse(BaseModel):
    """配置列表响应"""
    total: int = Field(0, description="总配置数")
    items: List[DriftConfigResponse] = Field(default_factory=list, description="配置列表")


# ==================== 漂移基线 ====================

class DriftBaselineStatsSchema(BaseModel):
    """基线统计信息"""
    mean: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    count: Optional[int] = None
    median: Optional[float] = None


class DriftBaselineFeatureStatsSchema(BaseModel):
    """特征维度基线统计"""
    feature_name: str = Field(..., description="特征名称")
    stats: DriftBaselineStatsSchema = Field(..., description="统计量")


class DriftBaselineResponse(BaseModel):
    """漂移基线响应"""
    id: Optional[int] = Field(None, description="基线ID")
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型")
    version: Optional[str] = Field(None, description="模型版本")
    baseline_type: Optional[str] = Field(None, description="基线类型：data_distribution / confidence / feature_stats")
    data_window_start: Optional[date] = Field(None, description="数据窗口开始")
    data_window_end: Optional[date] = Field(None, description="数据窗口结束")
    sample_count: Optional[int] = Field(None, description="样本数量")
    stats: Optional[Dict[str, Any]] = Field(None, description="统计信息（JSON）")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class DriftBaselineListResponse(BaseModel):
    """基线列表响应"""
    total: int = Field(0, description="总基线数")
    items: List[DriftBaselineResponse] = Field(default_factory=list, description="基线列表")


class DriftBaselineCreateRequest(BaseModel):
    """创建漂移基线请求"""
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型：bolt / flange")
    version: Optional[str] = Field(None, description="模型版本，None表示当前活跃版本")
    baseline_type: Optional[str] = Field(
        "all",
        description="基线类型：data_distribution / confidence / feature_stats / all"
    )
    data_window_start: Optional[date] = Field(None, description="数据窗口开始，默认30天前")
    data_window_end: Optional[date] = Field(None, description="数据窗口结束，默认今天")
    force: Optional[bool] = Field(False, description="是否强制覆盖已有基线")


# ==================== 漂移事件 ====================

class DriftEventDimensionDetailSchema(BaseModel):
    """单维度漂移详情"""
    dimension: str = Field(..., description="漂移维度：psi / ks / confidence / false_positive / feature_shift")
    score: float = Field(..., description="该维度漂移分数 0-1")
    threshold: Optional[float] = Field(None, description="该维度阈值")
    is_alert: bool = Field(..., description="是否超阈值")
    details: Optional[Dict[str, Any]] = Field(None, description="详细指标")


class DriftEventResponse(BaseModel):
    """漂移事件响应"""
    id: Optional[int] = Field(None, description="事件ID")
    event_no: Optional[str] = Field(None, description="事件编号")
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型")
    version: Optional[str] = Field(None, description="模型版本")
    detection_date: Optional[date] = Field(None, description="检测日期")
    drift_level: Optional[str] = Field(None, description="漂移等级：none / low / medium / high / critical")
    composite_score: Optional[float] = Field(None, description="综合漂移分数")
    is_alert: Optional[bool] = Field(None, description="是否告警")
    triggered_dimensions: Optional[List[str]] = Field(None, description="触发告警的维度列表")
    dimension_details: Optional[List[DriftEventDimensionDetailSchema]] = Field(
        None,
        description="各维度详细结果"
    )
    feature_drift: Optional[List[Dict[str, Any]]] = Field(None, description="特征漂移详情")
    response_strategy: Optional[str] = Field(None, description="响应策略")
    response_status: Optional[str] = Field(None, description="响应状态：pending / processing / completed / failed / skipped")
    response_detail: Optional[Dict[str, Any]] = Field(None, description="响应执行详情")
    consecutive_days: Optional[int] = Field(None, description="连续告警天数")
    tenant_id: Optional[str] = Field(None, description="租户ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class DriftEventListResponse(BaseModel):
    """漂移事件列表响应"""
    total: int = Field(0, description="总事件数")
    items: List[DriftEventResponse] = Field(default_factory=list, description="事件列表")


class DriftEventQueryRequest(BaseModel):
    """漂移事件查询请求"""
    model_id: Optional[str] = Field(None, description="模型ID过滤")
    model_type: Optional[str] = Field(None, description="模型类型过滤：bolt / flange")
    start_date: Optional[date] = Field(None, description="检测日期开始")
    end_date: Optional[date] = Field(None, description="检测日期结束")
    drift_level: Optional[str] = Field(None, description="漂移等级过滤")
    is_alert: Optional[bool] = Field(None, description="仅查看告警事件")
    response_status: Optional[str] = Field(None, description="响应状态过滤")
    page: Optional[int] = Field(1, ge=1, description="页码")
    page_size: Optional[int] = Field(20, ge=1, le=500, description="每页数量")


# ==================== 手动触发检测/重训 ====================

class DriftManualDetectionRequest(BaseModel):
    """手动触发漂移检测请求"""
    detection_date: Optional[date] = Field(None, description="检测日期，默认今天")
    model_types: Optional[List[str]] = Field(
        None,
        description="模型类型列表，默认全部：['bolt', 'flange']"
    )


class DriftManualDetectionResponse(BaseModel):
    """手动触发漂移检测响应"""
    success: bool = Field(..., description="是否成功启动")
    detection_date: Optional[date] = Field(None, description="检测日期")
    processed_models: Optional[int] = Field(None, description="已处理模型数")
    alert_count: Optional[int] = Field(None, description="产生告警事件数")
    message: Optional[str] = Field(None, description="执行结果描述")


class DriftManualRetrainRequest(BaseModel):
    """手动触发重训请求"""
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型：bolt / flange")
    strategy: Optional[str] = Field(
        "shadow_retrain",
        description="重训策略：shadow_retrain / auto_retrain"
    )
    force: Optional[bool] = Field(False, description="是否忽略最小间隔强制重训")


class DriftManualRetrainResponse(BaseModel):
    """手动触发重训响应"""
    success: bool = Field(..., description="是否成功触发")
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型")
    strategy: str = Field(..., description="采用的策略")
    training_task_id: Optional[str] = Field(None, description="训练任务ID")
    message: Optional[str] = Field(None, description="结果描述")


# ==================== 响应处理 ====================

class DriftProcessPendingResponse(BaseModel):
    """处理待响应事件结果"""
    success: bool = Field(..., description="是否成功执行")
    total_pending: Optional[int] = Field(None, description="待处理事件总数")
    processed_count: Optional[int] = Field(None, description="本次处理数量")
    success_count: Optional[int] = Field(None, description="成功响应数量")
    failed_count: Optional[int] = Field(None, description="失败数量")


class DriftEventAckRequest(BaseModel):
    """确认漂移事件请求"""
    ack_note: Optional[str] = Field(None, description="确认备注")


# ==================== 漂移趋势统计 ====================

class DriftTrendPointSchema(BaseModel):
    """漂移趋势数据点"""
    detection_date: date = Field(..., description="检测日期")
    composite_score: Optional[float] = Field(None, description="综合分数")
    drift_level: Optional[str] = Field(None, description="漂移等级")
    is_alert: Optional[bool] = Field(None, description="是否告警")


class DriftTrendResponse(BaseModel):
    """漂移趋势响应"""
    model_id: str = Field(..., description="模型ID")
    model_type: str = Field(..., description="模型类型")
    points: List[DriftTrendPointSchema] = Field(default_factory=list, description="趋势数据点")
    dimension_trends: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None,
        description="各维度趋势"
    )
