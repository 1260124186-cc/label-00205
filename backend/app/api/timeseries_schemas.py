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
