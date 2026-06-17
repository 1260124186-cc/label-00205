"""
时序数据库 API 路由

提供时序数据的写入、查询、分析和管理接口。
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from loguru import logger

from app.api.timeseries_schemas import (
    TimeSeriesWriteRequest,
    TimeSeriesBatchWriteRequest,
    TimeSeriesWriteResponse,
    TimeSeriesQueryRequest,
    TimeSeriesQueryResponse,
    TimeSeriesStatisticsRequest,
    TimeSeriesStatisticsResponse,
    TimeSeriesCompareRequest,
    TimeSeriesCompareResponse,
    TimeSeriesSQLRequest,
    TimeSeriesSQLResponse,
    TimeSeriesMigrationRequest,
    TimeSeriesMigrationResponse,
    TimeSeriesMigrationStatusResponse,
    TimeSeriesDownsamplingRequest,
    TimeSeriesDownsamplingResponse,
    TimeSeriesHealthResponse,
    TimeSeriesSensorListResponse,
    TimeSeriesDataPointSchema,
)

from app.timeseries.base import (
    TimeSeriesDataPoint,
    TimeSeriesQuery,
    AggregationLevel,
)
from app.timeseries.factory import (
    get_timeseries_repository,
    is_timeseries_enabled,
    get_timeseries_config,
)
from app.services.timeseries_service import (
    TimeSeriesAnalysisService,
    get_timeseries_analysis_service,
)


router = APIRouter(prefix="/timeseries", tags=["时序数据库"])

_migration_task = None


def _ensure_timeseries_enabled():
    """确保时序数据库已启用，否则抛出异常"""
    if not is_timeseries_enabled():
        raise HTTPException(
            status_code=503,
            detail="时序数据库未启用，请先配置并启用时序数据库",
        )

    repo = get_timeseries_repository()
    if repo is None:
        raise HTTPException(
            status_code=503,
            detail="时序数据库连接失败",
        )
    return repo


# ==================== 健康检查 ====================

@router.get("/health", response_model=TimeSeriesHealthResponse)
async def get_health():
    """获取时序数据库健康状态"""
    enabled = is_timeseries_enabled()
    config = get_timeseries_config()

    if not enabled:
        return TimeSeriesHealthResponse(
            enabled=False,
            backend=None,
            healthy=False,
            message="时序数据库未启用",
        )

    repo = get_timeseries_repository()
    if repo is None:
        return TimeSeriesHealthResponse(
            enabled=True,
            backend=config.get('backend'),
            healthy=False,
            message="时序数据库连接失败",
        )

    healthy = repo.health_check()
    return TimeSeriesHealthResponse(
        enabled=True,
        backend=config.get('backend'),
        healthy=healthy,
        message="正常" if healthy else "连接异常",
    )


# ==================== 数据写入 ====================

@router.post("/write", response_model=TimeSeriesWriteResponse)
async def write_point(request: TimeSeriesWriteRequest):
    """写入单个时序数据点"""
    repo = _ensure_timeseries_enabled()

    point = TimeSeriesDataPoint(
        timestamp=request.point.timestamp,
        sensor_id=request.point.sensor_id,
        value=request.point.value,
        fields=request.point.fields or {},
        tags=request.point.tags or {},
    )

    success = repo.write_point(point)

    return TimeSeriesWriteResponse(
        success=success,
        written_count=1 if success else 0,
        message="写入成功" if success else "写入失败",
    )


@router.post("/write/batch", response_model=TimeSeriesWriteResponse)
async def write_batch(request: TimeSeriesBatchWriteRequest):
    """批量写入时序数据点"""
    repo = _ensure_timeseries_enabled()

    points = [
        TimeSeriesDataPoint(
            timestamp=p.timestamp,
            sensor_id=p.sensor_id,
            value=p.value,
            fields=p.fields or {},
            tags=p.tags or {},
        )
        for p in request.points
    ]

    count = repo.write_batch(points)

    return TimeSeriesWriteResponse(
        success=count == len(points),
        written_count=count,
        message=f"成功写入 {count} 条数据",
    )


# ==================== 数据查询 ====================

@router.post("/query", response_model=TimeSeriesQueryResponse)
async def query_data(request: TimeSeriesQueryRequest):
    """查询时序数据"""
    repo = _ensure_timeseries_enabled()
    service = get_timeseries_analysis_service()

    if request.aggregation == "auto" or request.aggregation in ["raw", "minute", "hour"]:
        result = service.get_trend(
            sensor_id=request.sensor_id,
            start_time=request.start_time,
            end_time=request.end_time,
            aggregation=request.aggregation,
        )

        return TimeSeriesQueryResponse(
            sensor_id=result['sensor_id'],
            aggregation=result.get('aggregation', 'raw'),
            point_count=result.get('point_count', 0),
            points=result.get('points', []),
        )
    else:
        raise HTTPException(status_code=400, detail="无效的聚合级别")


@router.get("/latest", response_model=TimeSeriesQueryResponse)
async def get_latest(
    sensor_id: str = Query(..., description="传感器ID"),
    limit: int = Query(100, description="返回数据点数", ge=1, le=10000),
):
    """查询最近 N 个数据点（预测流水线用）"""
    repo = _ensure_timeseries_enabled()

    points = repo.query_latest(sensor_id, limit=limit)

    return TimeSeriesQueryResponse(
        sensor_id=sensor_id,
        aggregation="raw",
        point_count=len(points),
        points=[
            {
                'timestamp': p.timestamp.isoformat(),
                'value': p.value,
            }
            for p in points
        ],
    )


# ==================== 统计分析 ====================

@router.post("/statistics", response_model=TimeSeriesStatisticsResponse)
async def get_statistics(request: TimeSeriesStatisticsRequest):
    """获取统计分析数据"""
    service = get_timeseries_analysis_service()
    if service is None:
        raise HTTPException(status_code=503, detail="时序数据库未启用")

    result = service.get_statistics(
        sensor_id=request.sensor_id,
        start_time=request.start_time,
        end_time=request.end_time,
    )

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return TimeSeriesStatisticsResponse(**result)


@router.post("/compare", response_model=TimeSeriesCompareResponse)
async def get_period_compare(request: TimeSeriesCompareRequest):
    """获取周期对比分析（同比/环比）"""
    service = get_timeseries_analysis_service()
    if service is None:
        raise HTTPException(status_code=503, detail="时序数据库未启用")

    result = service.get_period_compare(
        sensor_id=request.sensor_id,
        current_start=request.start_time,
        current_end=request.end_time,
        compare_type=request.compare_type,
    )

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return TimeSeriesCompareResponse(**result)


# ==================== SQL 查询 ====================

@router.post("/sql", response_model=TimeSeriesSQLResponse)
async def execute_sql(request: TimeSeriesSQLRequest):
    """
    执行自定义 SQL 查询（历史分析用）

    注意：仅 TimescaleDB 后端支持完整的 SQL 查询。
    InfluxDB 后端可能返回有限的结果。
    """
    service = get_timeseries_analysis_service()
    if service is None:
        raise HTTPException(status_code=503, detail="时序数据库未启用")

    result = service.execute_sql_query(
        sql=request.sql,
        params=request.params,
    )

    return TimeSeriesSQLResponse(**result)


# ==================== 传感器管理 ====================

@router.get("/sensors", response_model=TimeSeriesSensorListResponse)
async def list_sensors():
    """列出所有传感器"""
    repo = _ensure_timeseries_enabled()

    sensors = repo.list_sensors()

    return TimeSeriesSensorListResponse(
        sensors=sensors,
        total=len(sensors),
    )


@router.get("/sensors/{sensor_id}/count")
async def count_points(
    sensor_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """统计指定传感器的数据点数量"""
    repo = _ensure_timeseries_enabled()

    count = repo.count_points(
        TimeSeriesQuery(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time,
        )
    )

    return {
        "sensor_id": sensor_id,
        "count": count,
    }


# ==================== 降采样 ====================

@router.post("/downsampling/run", response_model=TimeSeriesDownsamplingResponse)
async def run_downsampling(request: TimeSeriesDownsamplingRequest):
    """执行降采样聚合"""
    repo = _ensure_timeseries_enabled()

    try:
        level = AggregationLevel(request.level)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的聚合级别")

    try:
        count = repo.run_downsampling(
            level=level,
            start_time=request.start_time,
            end_time=request.end_time,
            sensor_ids=request.sensor_ids,
        )

        return TimeSeriesDownsamplingResponse(
            level=request.level,
            generated_points=count,
            success=True,
            message=f"降采样完成，生成 {count} 个聚合点",
        )
    except Exception as e:
        logger.error(f"降采样执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据迁移 ====================

@router.post("/migration/start", response_model=TimeSeriesMigrationResponse)
async def start_migration(
    request: TimeSeriesMigrationRequest,
    background_tasks: BackgroundTasks,
):
    """启动 MySQL 到时序数据库的数据迁移（后台执行）"""
    _ensure_timeseries_enabled()

    global _migration_task

    if _migration_task and _migration_task.get('status') == 'running':
        raise HTTPException(
            status_code=409,
            detail="迁移任务正在进行中，请等待完成",
        )

    def run_migration():
        try:
            from app.timeseries.migration import MySQLToTimeseriesMigrator

            migrator = MySQLToTimeseriesMigrator()
            result = migrator.migrate_all(
                start_date=request.start_date,
                end_date=request.end_date,
                sensor_ids=request.sensor_ids,
                run_downsampling=request.run_downsampling,
            )
            _migration_task = {
                'status': 'completed',
                'result': result,
            }
            logger.info(f"数据迁移完成: {result.total_records} 条记录")
        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            _migration_task = {
                'status': 'failed',
                'error': str(e),
            }

    _migration_task = {'status': 'running', 'result': None}
    background_tasks.add_task(run_migration)

    return TimeSeriesMigrationResponse(
        status="started",
        total_sensors=len(request.sensor_ids) if request.sensor_ids else 0,
    )


@router.get("/migration/status", response_model=TimeSeriesMigrationStatusResponse)
async def get_migration_status():
    """获取数据迁移进度"""
    _ensure_timeseries_enabled()

    global _migration_task

    if _migration_task is None:
        try:
            from app.timeseries.migration import MySQLToTimeseriesMigrator

            migrator = MySQLToTimeseriesMigrator()
            summary = migrator.get_progress_summary()
            return TimeSeriesMigrationStatusResponse(**summary)
        except Exception as e:
            logger.error(f"获取迁移进度失败: {e}")
            return TimeSeriesMigrationStatusResponse()

    status = _migration_task.get('status', 'unknown')
    result = _migration_task.get('result')

    if result:
        return TimeSeriesMigrationStatusResponse(
            total_sensors=result.total_sensors,
            completed=result.completed_sensors,
            failed=len(result.failed_sensors),
            total_records=result.total_records,
        )

    return TimeSeriesMigrationStatusResponse()


@router.post("/migration/reset")
async def reset_migration(
    sensor_id: Optional[str] = Query(None, description="指定传感器ID，不指定则重置全部"),
):
    """重置迁移进度"""
    _ensure_timeseries_enabled()

    try:
        from app.timeseries.migration import MySQLToTimeseriesMigrator

        migrator = MySQLToTimeseriesMigrator()
        migrator.reset_progress(sensor_id=sensor_id)

        return {"success": True, "message": "迁移进度已重置"}
    except Exception as e:
        logger.error(f"重置迁移进度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
