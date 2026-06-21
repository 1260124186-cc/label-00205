"""
时序数据库 API 请求和响应模型
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ==================== 时序数据写入 ====================

class TimeSeriesDataPointSchema(BaseModel):
    """时序数据点"""
    timestamp: datetime = Field(..., description="时间戳")
    sensor_id: str = Field(..., description="传感器/螺栓ID")
    value: float = Field(..., description="预紧力值")
    fields: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="其他测量字段（温度、湿度等")
    tags: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="标签字段（采集器、分线器等）")


class TimeSeriesWriteRequest(BaseModel):
    """时序数据写入请求（单条）"""
    point: TimeSeriesDataPointSchema


class TimeSeriesBatchWriteRequest(BaseModel):
    """时序数据批量写入请求"""
    points: List[TimeSeriesDataPointSchema] = Field(
        ...,
        min_length=1,
        description="数据点列表")


class TimeSeriesWriteResponse(BaseModel):
    """时序数据写入响应"""
    success: bool
    written_count: int = Field(0, description="成功写入数量")
    message: Optional[str] = None


# ==================== 时序数据查询 ====================

class TimeSeriesQueryRequest(BaseModel):
    """时序数据查询请求"""
    sensor_id: str = Field(..., description="传感器ID")
    start_time: datetime = Field(..., description="起始时间")
    end_time: datetime = Field(..., description="结束时间")
    aggregation: str = Field(
        "auto",
        description="聚合级别: raw/minute/hour/auto")
    limit: Optional[int] = Field(None, description="返回数据点上限")
    order: str = Field("asc", description="排序方向: asc/desc")


class TimeSeriesRawPointSchema(BaseModel):
    """原始数据点响应"""
    timestamp: datetime
    value: float


class TimeSeriesAggregatedPointSchema(BaseModel):
    """聚合数据点响应"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    mean: float
    std: float
    count: int


class TimeSeriesQueryResponse(BaseModel):
    """时序数据查询响应"""
    sensor_id: str
    aggregation: str
    point_count: int
    points: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="数据点列表")


# ==================== 统计分析 ====================

class TimeSeriesStatisticsRequest(BaseModel):
    """统计分析请求"""
    sensor_id: str = Field(..., description="传感器ID")
    start_time: datetime = Field(..., description="起始时间")
    end_time: datetime = Field(..., description="结束时间")


class TimeSeriesStatisticsResponse(BaseModel):
    """统计分析响应"""
    sensor_id: str
    time_range: Dict[str, str]
    total_points: int
    aggregated_points: int
    statistics: Dict[str, float]
    trend: Dict[str, Any]


class TimeSeriesCompareRequest(BaseModel):
    """周期对比请求"""
    sensor_id: str = Field(..., description="传感器ID")
    start_time: datetime = Field(..., description="当前周期起始")
    end_time: datetime = Field(..., description="当前周期结束")
    compare_type: str = Field("mom", description="对比类型: mom=环比, yoy=同比")


class TimeSeriesCompareResponse(BaseModel):
    """周期对比响应"""
    sensor_id: str
    compare_type: str
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    comparison: Dict[str, Any]


# ==================== SQL 查询 ====================

class TimeSeriesSQLRequest(BaseModel):
    """SQL 查询请求"""
    sql: str = Field(..., description="SQL 查询语句")
    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="查询参数")


class TimeSeriesSQLResponse(BaseModel):
    """SQL 查询响应"""
    success: bool
    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    results: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


# ==================== 数据迁移 ====================

class TimeSeriesMigrationRequest(BaseModel):
    """数据迁移请求"""
    start_date: Optional[datetime] = Field(None, description="迁移起始时间")
    end_date: Optional[datetime] = Field(None, description="迁移结束时间")
    sensor_ids: Optional[List[str]] = Field(
        None,
        description="指定传感器ID列表，不指定则迁移全部")
    run_downsampling: bool = Field(
        True,
        description="迁移后是否执行降采样")


class TimeSeriesMigrationResponse(BaseModel):
    """数据迁移响应"""
    total_sensors: int = 0
    completed_sensors: int = 0
    total_records: int = 0
    failed_sensors: List[str] = Field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "started"


class TimeSeriesMigrationStatusResponse(BaseModel):
    """迁移进度查询响应"""
    total_sensors: int = 0
    completed: int = 0
    running: int = 0
    failed: int = 0
    pending: int = 0
    total_records: int = 0


# ==================== 降采样 ====================

class TimeSeriesDownsamplingRequest(BaseModel):
    """降采样请求"""
    level: str = Field("minute", description="聚合级别: minute/hour")
    start_time: Optional[datetime] = Field(None, description="起始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    sensor_ids: Optional[List[str]] = Field(
        None,
        description="指定传感器ID列表")


class TimeSeriesDownsamplingResponse(BaseModel):
    """降采样响应"""
    level: str
    generated_points: int = 0
    success: bool
    message: Optional[str] = None


# ==================== 健康检查 ====================

class TimeSeriesHealthResponse(BaseModel):
    """时序数据库健康检查响应"""
    enabled: bool
    backend: Optional[str] = None
    healthy: bool = False
    message: Optional[str] = None


# ==================== 传感器列表 ====================

class TimeSeriesSensorListResponse(BaseModel):
    """传感器列表响应"""
    sensors: List[str] = Field(default_factory=list)
    total: int = 0


# ==================== 归档管理 - 保留策略 ====================

class RetentionPolicyCreate(BaseModel):
    """创建租户保留策略请求"""
    policy_name: str = Field(..., max_length=100, description="策略名称")
    policy_type: str = Field(
        "operations",
        description="策略类型: compliance(合规7年)/operations(运营1年)/custom(自定义)")
    is_default: bool = Field(True, description="是否为默认策略")
    scope_table: Optional[str] = Field(None, description="适用表名，不指定则全部表")
    scope_sensor_ids: Optional[List[str]] = Field(None, description="适用传感器ID列表")
    scope_aggregation_level: Optional[str] = Field(None, description="适用聚合级别")
    hot_retention_days: int = Field(90, ge=1, le=3650, description="热数据保留天数（MySQL）")
    cold_retention_days: int = Field(365, ge=30, le=36500, description="冷数据保留天数")
    compliance_retention_years: Optional[int] = Field(
        None, ge=1, le=50, description="合规保留年限（仅compliance类型有效）")
    archive_cron: Optional[str] = Field(
        None, description="归档任务cron表达式，不指定则使用全局默认")
    purge_cron: Optional[str] = Field(
        None, description="清理任务cron表达式，不指定则使用全局默认")
    auto_delete_hot: bool = Field(True, description="归档成功后是否自动删除热数据")
    lazy_load_enabled: bool = Field(True, description="是否启用冷数据懒加载")
    storage_class: Optional[str] = Field(
        None, description="冷存储类别: standard/infrequent/archive/deep_archive")
    compression_algo: Optional[str] = Field(
        None, description="压缩算法: snappy/gzip/zstd/brotli/none")
    encryption_enabled: bool = Field(False, description="是否启用服务端加密")
    effective_from: Optional[datetime] = Field(None, description="生效起始时间")
    effective_to: Optional[datetime] = Field(None, description="生效结束时间")
    change_reason: Optional[str] = Field(
        None, max_length=500, description="策略变更原因")
    created_by: Optional[str] = Field(
        None, max_length=100, description="创建人/操作人")
    approved_by: Optional[str] = Field(
        None, max_length=100, description="审批人")


class RetentionPolicyUpdate(BaseModel):
    """更新租户保留策略请求（字段均可选，未指定则保持原值）"""
    policy_name: Optional[str] = Field(None, max_length=100)
    policy_type: Optional[str] = Field(None)
    is_default: Optional[bool] = None
    scope_table: Optional[str] = None
    scope_sensor_ids: Optional[List[str]] = None
    scope_aggregation_level: Optional[str] = None
    hot_retention_days: Optional[int] = Field(None, ge=1, le=3650)
    cold_retention_days: Optional[int] = Field(None, ge=30, le=36500)
    compliance_retention_years: Optional[int] = Field(None, ge=1, le=50)
    archive_cron: Optional[str] = None
    purge_cron: Optional[str] = None
    auto_delete_hot: Optional[bool] = None
    lazy_load_enabled: Optional[bool] = None
    storage_class: Optional[str] = None
    compression_algo: Optional[str] = None
    encryption_enabled: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    change_reason: Optional[str] = Field(None, max_length=500)
    approved_by: Optional[str] = Field(None, max_length=100)


class RetentionPolicyResponse(BaseModel):
    """租户保留策略响应"""
    tenant_id: int
    policy_name: str
    policy_type: str
    is_default: bool
    is_active: bool
    priority: int
    scope_table: Optional[str] = None
    scope_sensor_ids: Optional[List[str]] = None
    scope_aggregation_level: Optional[str] = None
    hot_retention_days: int
    cold_retention_days: int
    compliance_retention_years: Optional[int] = None
    archive_cron: Optional[str] = None
    purge_cron: Optional[str] = None
    auto_delete_hot: bool
    lazy_load_enabled: bool
    storage_class: Optional[str] = None
    compression_algo: Optional[str] = None
    encryption_enabled: bool
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    version: int = 1
    change_reason: Optional[str] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


# ==================== 归档管理 - 任务与统计 ====================

class ArchiveJobResponse(BaseModel):
    """归档任务执行记录响应"""
    job_id: str
    tenant_id: int
    job_name: Optional[str] = None
    job_type: Optional[str] = None
    trigger_type: Optional[str] = None
    source_table: Optional[str] = None
    target_storage: Optional[str] = None
    partition_key: Optional[str] = None
    hot_threshold_days: Optional[int] = None
    retention_days: Optional[int] = None
    delete_from_hot: Optional[bool] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_partitions: Optional[int] = None
    processed_partitions: Optional[int] = None
    total_rows: Optional[int] = None
    archived_rows: Optional[int] = None
    failed_rows: Optional[int] = None
    deleted_rows: Optional[int] = None
    archive_size_bytes: Optional[int] = None
    archive_file_count: Optional[int] = None
    error_count: Optional[int] = None
    error_summary: Optional[str] = None
    cron_expression: Optional[str] = None
    operator: Optional[str] = None
    create_time: Optional[datetime] = None


class ArchivePartitionStat(BaseModel):
    """分区状态统计"""
    status: str
    partition_count: int
    total_rows: int
    total_bytes: int


class ArchiveStatisticsResponse(BaseModel):
    """归档统计响应"""
    tenant_id: int
    summary: Dict[str, Any] = Field(default_factory=dict)
    partitions: List[ArchivePartitionStat] = Field(default_factory=list)
    recent_jobs: List[ArchiveJobResponse] = Field(default_factory=list)
    cold_storage_used_bytes: int = 0
    hot_storage_used_bytes: int = 0
    total_archive_files: int = 0
    hot_retention_days: int = 90
    cold_retention_days: int = 365


# ==================== 归档管理 - 手动触发 ====================

class ManualArchiveRequest(BaseModel):
    """手动触发归档请求"""
    table_name: Optional[str] = Field(None, description="指定表名，不指定则所有时序表")
    hot_threshold_days: Optional[int] = Field(
        None, ge=1, description="覆盖策略中的热阈值天数")
    target_partition_keys: Optional[List[str]] = Field(
        None, description="指定归档的分区键列表(YYYY-MM)，不指定则自动计算")
    delete_from_hot: Optional[bool] = Field(
        None, description="归档成功后是否删除热数据，不指定则使用策略")
    verify_after_write: bool = Field(True, description="写入后是否校验校验和")
    operator: Optional[str] = Field(
        "api_user", max_length=100, description="操作人标识")


class ManualArchiveResponse(BaseModel):
    """手动触发归档响应"""
    success: bool
    job_id: Optional[str] = None
    message: str
    tenant_id: int
    processed_partitions: int = 0
    archived_rows: int = 0
    failed_partitions: int = 0
    total_bytes: int = 0
    duration_seconds: Optional[float] = None


class ManualPurgeResponse(BaseModel):
    """手动触发清理响应"""
    success: bool
    message: str
    tenant_id: int
    purged_partitions: int = 0
    purged_files: int = 0
    released_bytes: int = 0
    duration_seconds: Optional[float] = None


# ==================== 冷数据懒加载 ====================

class LazyLoadStatusResponse(BaseModel):
    """冷数据懒加载请求状态响应"""
    request_id: str
    tenant_id: int
    user_id: Optional[str] = None
    user_type: Optional[str] = None
    api_endpoint: Optional[str] = None
    source_table: Optional[str] = None
    sensor_ids: Optional[List[str]] = None
    query_start_time: Optional[datetime] = None
    query_end_time: Optional[datetime] = None
    aggregation_level: Optional[str] = None
    status: str
    priority: Optional[str] = None
    async_mode: bool = True
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    hot_row_count: int = 0
    cold_row_count: int = 0
    total_row_count: int = 0
    cold_file_count: int = 0
    cold_bytes_loaded: int = 0
    restore_to_hot: bool = False
    restore_expire_hours: int = 72
    cache_hit: bool = False
    error_message: Optional[str] = None
    cold_data_ranges: Optional[List[Dict[str, Any]]] = None
    archive_ids: Optional[List[str]] = None
    partition_keys: Optional[List[str]] = None
    create_time: Optional[datetime] = None


# ==================== 透明分层查询 ====================

class TieredQueryRequest(BaseModel):
    """分层时序查询请求（自动路由热/冷数据）"""
    tenant_id: int = Field(..., description="租户ID")
    table_name: str = Field("sc_bolt_data", description="时序表名")
    start_time: datetime = Field(..., description="查询起始时间")
    end_time: datetime = Field(..., description="查询结束时间")
    sensor_ids: Optional[List[str]] = Field(
        None, description="传感器ID列表，不指定则全部")
    scenario: str = Field(
        "custom",
        description="业务场景: training/prediction/analysis/compliance/"
                    "reporting/visualization/data_export/custom")
    read_tier: str = Field(
        "auto",
        description="读取层级: hot_only/hot_warm/all/auto。auto=按场景默认+自动升级")
    aggregation_level: str = Field(
        "raw", description="聚合级别: raw/minute/hour")
    async_load: bool = Field(
        True,
        description="冷数据异步加载模式: True=返回request_id后后台加载; False=同步等待")
    load_priority: str = Field(
        "normal", description="加载优先级: low/normal/high/critical")
    restore_to_hot: bool = Field(
        False, description="是否将冷数据恢复到热存储缓存")
    restore_expire_hours: int = Field(
        72, description="恢复到热存储的过期小时数")
    auto_upgrade_tier: Optional[bool] = Field(
        None, description="是否允许自动升级读取层级，不指定则使用配置默认")
    user_id: Optional[str] = Field(None, max_length=100, description="调用方用户ID")
    api_endpoint: Optional[str] = Field(
        None, max_length=200, description="调用方API标识")
    limit: Optional[int] = Field(None, description="返回数据点上限")
    order: str = Field("asc", description="排序方向: asc/desc")


class TieredQueryResponse(BaseModel):
    """分层时序查询响应"""
    success: bool
    message: Optional[str] = None
    tenant_id: int
    effective_read_tier: str
    tier_upgraded: bool = False
    tier_upgrade_reason: Optional[str] = None
    hot_row_count: int = 0
    cold_row_count: int = 0
    total_row_count: int = 0
    cold_files_read: int = 0
    cold_bytes_read: int = 0
    duration_ms: float = 0
    lazy_load_request_id: Optional[str] = None
    lazy_load_status: Optional[str] = None
    points: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)


# ==================== 时间范围建议 ====================

class SuggestedTimeRangeResponse(BaseModel):
    """时间范围与层级建议响应"""
    tenant_id: int
    scenario: str
    requested_start_time: datetime
    requested_end_time: datetime
    suggested_start_time: datetime
    suggested_end_time: datetime
    suggested_read_tier: str
    required_read_tier: str
    hot_cutoff_time: datetime
    warm_cutoff_time: Optional[datetime] = None
    hot_retention_days: int
    cold_retention_days: int
    warning: Optional[str] = None
    tier_upgrade_will_happen: bool = False


# ==================== Prophet 多周期预测与季节性分解 ====================

class HolidayItemSchema(BaseModel):
    """节假日配置项"""
    ds: datetime = Field(..., description="节假日日期")
    holiday: str = Field(..., max_length=100, description="节假日名称")
    lower_window: int = Field(0, ge=0, le=30, description="节前影响天数")
    upper_window: int = Field(0, ge=0, le=30, description="节后影响天数")


class ProphetDataPointSchema(BaseModel):
    """时序数据点（Prophet专用简化版）"""
    timestamp: datetime = Field(..., description="时间戳")
    value: float = Field(..., description="观测值（如预紧力）")


class SingleHorizonForecastSchema(BaseModel):
    """单 horizon 预测结果"""
    horizon_days: int = Field(..., description="预测horizon天数")
    dates: List[datetime] = Field(..., description="预测日期列表")
    values: List[float] = Field(..., description="预测值列表(yhat)")
    lower_bound: List[float] = Field(..., description="置信区间下界(yhat_lower)")
    upper_bound: List[float] = Field(..., description="置信区间上界(yhat_upper)")
    anomaly_dates: List[Tuple[datetime, datetime]] = Field(
        default_factory=list,
        description="异常时间段列表 [(开始, 结束), ...]"
    )
    anomaly_type: str = Field(
        default="正常",
        description="异常类型: 正常/关注级预警/检查级预警/紧急级预警/松动/过载/断裂"
    )
    confidence: float = Field(..., ge=0, le=1, description="预测置信度")
    confidence_level: float = Field(
        default=0.95, ge=0.5, le=0.99,
        description="置信区间水平（如0.95表示95%CI）"
    )


class SeasonalDecompositionSchema(BaseModel):
    """季节性分解结果"""
    dates: List[datetime] = Field(..., description="日期列表(历史+预测)")
    trend: List[float] = Field(..., description="趋势项分量")
    weekly: Optional[List[float]] = Field(None, description="周周期分量")
    daily: Optional[List[float]] = Field(None, description="日周期分量")
    yearly: Optional[List[float]] = Field(None, description="年周期分量")
    holidays: Optional[List[float]] = Field(None, description="节假日效应分量")
    regressors: Optional[Dict[str, List[float]]] = Field(
        None,
        description="额外regressor效应分量 {regressor_name: values}"
    )
    residuals: Optional[List[float]] = Field(None, description="残差项")


class ProphetMultiHorizonRequest(BaseModel):
    """Prophet 多周期预测请求"""
    sensor_id: str = Field(..., description="传感器/节点ID")
    data_points: List[ProphetDataPointSchema] = Field(
        ...,
        min_length=30,
        description="历史时序数据点（建议至少90天以上效果更好）"
    )
    horizons: List[int] = Field(
        default_factory=lambda: [7, 30, 90],
        description="预测horizon列表，支持7/30/90天等任意正整数"
    )
    holidays: Optional[List[HolidayItemSchema]] = Field(
        None,
        description="节假日列表（可选，作为Prophet regressor）"
    )
    shutdown_dates: Optional[List[datetime]] = Field(
        None,
        description="停产日列表（可选，作为Prophet regressor）"
    )
    include_decomposition: bool = Field(
        True,
        description="是否输出季节性分解结果"
    )
    uncertainty_samples: int = Field(
        1000, ge=100, le=10000,
        description="不确定性采样数，越大置信区间越准确但越慢"
    )


class ProphetMultiHorizonResponse(BaseModel):
    """Prophet 多周期预测响应"""
    sensor_id: str = Field(..., description="传感器/节点ID")
    historical: Dict[str, Any] = Field(
        ...,
        description="历史数据回显 {'dates': [...], 'values': [...]}"
    )
    forecasts: Dict[str, SingleHorizonForecastSchema] = Field(
        ...,
        description="各horizon预测结果字典，key为horizon天数字符串"
    )
    decomposition: Optional[SeasonalDecompositionSchema] = Field(
        None,
        description="季节性分解结果（若include_decomposition=True）"
    )
    model_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="模型参数摘要"
    )
    holidays_used: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="实际使用的节假日信息"
    )
    shutdown_dates_used: Optional[List[str]] = Field(
        None,
        description="实际使用的停产日列表"
    )
    execution_ms: float = Field(0, description="执行耗时(毫秒)")
