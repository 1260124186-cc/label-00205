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
    RetentionPolicyCreate,
    RetentionPolicyUpdate,
    RetentionPolicyResponse,
    ArchiveJobResponse,
    ArchiveStatisticsResponse,
    ManualArchiveRequest,
    ManualArchiveResponse,
    ManualPurgeResponse,
    LazyLoadStatusResponse,
    TieredQueryRequest,
    TieredQueryResponse,
    SuggestedTimeRangeResponse,
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


# ============================================================
# 归档管理 API
# ============================================================

def _ensure_archive_enabled():
    """确保归档模块已启用，否则抛出 503 异常"""
    from app.utils.config import config
    archive_cfg = config.get('archive', {}) or {}
    if not archive_cfg.get('enabled', True):
        raise HTTPException(
            status_code=503,
            detail="归档模块已禁用，请在配置中启用 archive.enabled",
        )


def _get_archive_service():
    """获取 ArchiveService 实例（延迟导入避免循环依赖）"""
    _ensure_archive_enabled()
    from app.services.archive_service import ArchiveService
    return ArchiveService()


def _get_tiered_router():
    """获取 TieredTimeSeriesRouter 实例"""
    _ensure_archive_enabled()
    from app.services.tiered_router import TieredTimeSeriesRouter
    return TieredTimeSeriesRouter()


def _orm_to_dict(obj, exclude: Optional[set] = None) -> Dict[str, Any]:
    """ORM 对象转 dict（辅助函数）"""
    from sqlalchemy.orm import class_mapper
    exclude = exclude or set()
    if obj is None:
        return {}
    columns = [c.key for c in class_mapper(obj.__class__).columns]
    return {
        c: getattr(obj, c)
        for c in columns
        if c not in exclude
    }


# -------------------- 手动触发归档 / 清理 --------------------

@router.post("/archive/run/{tenant_id}", response_model=ManualArchiveResponse)
async def run_archive_manually(
    tenant_id: int,
    request: ManualArchiveRequest,
):
    """
    手动触发时序数据冷热归档

    - 指定 table_name 可只归档单表，否则归档全部时序表
    - 指定 target_partition_keys(YYYY-MM) 可归档特定月份
    - hot_threshold_days 可临时覆盖策略中的热数据阈值
    """
    try:
        archive_service = _get_archive_service()
        tables = (
            [request.table_name] if request.table_name
            else ['sc_bolt_data', 'sc_flange_data', 'sc_vibration_data']
        )

        start_ts = datetime.now()
        total_partitions = 0
        total_rows = 0
        total_bytes = 0
        total_failed = 0
        last_job_id = None
        last_message = "ok"

        for table in tables:
            result = archive_service.run_monthly_archive(
                tenant_id=tenant_id,
                table_name=table,
                hot_threshold_days=request.hot_threshold_days,
                trigger_type='manual_api',
                operator=request.operator or 'api_user',
                target_partition_keys=request.target_partition_keys,
                delete_from_hot_override=request.delete_from_hot,
                verify_after_write=request.verify_after_write,
            )
            total_partitions += result.archived_partitions or 0
            total_rows += result.archived_rows or 0
            total_bytes += result.total_bytes or 0
            total_failed += result.failed_partitions or 0
            if result.job_id:
                last_job_id = result.job_id
            if not result.success:
                last_message = result.message or last_message

        duration = (datetime.now() - start_ts).total_seconds()
        success = total_failed == 0 and total_partitions >= 0

        return ManualArchiveResponse(
            success=success,
            job_id=last_job_id,
            message=last_message if not success else f"归档完成，处理 {total_partitions} 个分区",
            tenant_id=tenant_id,
            processed_partitions=total_partitions,
            archived_rows=total_rows,
            failed_partitions=total_failed,
            total_bytes=total_bytes,
            duration_seconds=duration,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"手动归档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archive/purge/{tenant_id}", response_model=ManualPurgeResponse)
async def run_purge_manually(
    tenant_id: int,
    permanent_delete: bool = Query(False, description="是否永久删除冷存储文件"),
):
    """
    手动触发冷数据过期清理

    根据租户保留策略清理 retention_expire_time <= now 的归档分区。
    """
    try:
        archive_service = _get_archive_service()
        start_ts = datetime.now()

        result = archive_service.purge_expired_cold_data(
            tenant_id=tenant_id,
            permanent_delete=permanent_delete,
        )

        duration = (datetime.now() - start_ts).total_seconds()

        return ManualPurgeResponse(
            success=result.success,
            message=result.message or ("清理完成" if result.success else "清理失败"),
            tenant_id=tenant_id,
            purged_partitions=result.archived_partitions or 0,
            purged_files=result.failed_partitions or 0,
            released_bytes=result.total_bytes or 0,
            duration_seconds=duration,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"手动清理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- 归档统计与任务历史 --------------------

@router.get("/archive/statistics/{tenant_id}", response_model=ArchiveStatisticsResponse)
async def get_archive_statistics(tenant_id: int):
    """获取指定租户的归档统计（分区状态、冷存储用量、最近任务）"""
    try:
        archive_service = _get_archive_service()

        stats = archive_service.get_archive_statistics(tenant_id)

        recent_jobs = [
            ArchiveJobResponse(**_orm_to_dict(j))
            for j in stats.get('recent_jobs', [])
        ]
        partitions = [
            ArchiveJobResponse.__config__  # noop
            for _ in []
        ]
        partition_list = []
        for status, info in stats.get('by_status', {}).items():
            partition_list.append({
                'status': status,
                'partition_count': info.get('partitions', 0),
                'total_rows': info.get('rows', 0),
                'total_bytes': info.get('bytes', 0),
            })

        policy = stats.get('policy', {}) or {}

        return ArchiveStatisticsResponse(
            tenant_id=tenant_id,
            summary={
                'total_partitions': stats.get('total_partitions', 0),
                'hot_rows': stats.get('hot_rows', 0),
                'cold_rows': stats.get('cold_rows', 0),
            },
            partitions=partition_list,
            recent_jobs=recent_jobs,
            cold_storage_used_bytes=stats.get('cold_bytes', 0),
            hot_storage_used_bytes=stats.get('hot_bytes', 0),
            total_archive_files=stats.get('archive_files', 0),
            hot_retention_days=policy.get('hot_retention_days', 90),
            cold_retention_days=policy.get('cold_retention_days', 365),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取归档统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archive/jobs/{tenant_id}", response_model=List[ArchiveJobResponse])
async def list_archive_jobs(
    tenant_id: int,
    job_type: Optional[str] = Query(None, description="任务类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(50, ge=1, le=500, description="返回条数上限"),
):
    """查询归档任务执行历史列表"""
    try:
        from app.utils.database import get_db, ArchiveJob
        from sqlalchemy import desc

        with get_db() as db:
            query = db.query(ArchiveJob).filter(ArchiveJob.tenant_id == tenant_id)
            if job_type:
                query = query.filter(ArchiveJob.job_type == job_type)
            if status:
                query = query.filter(ArchiveJob.status == status)
            jobs = (
                query.order_by(desc(ArchiveJob.create_time))
                .limit(limit)
                .all()
            )

            return [
                ArchiveJobResponse(**_orm_to_dict(j))
                for j in jobs
            ]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取归档任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- 保留策略 --------------------

@router.get("/archive/retention-policy/{tenant_id}", response_model=RetentionPolicyResponse)
async def get_retention_policy(tenant_id: int):
    """查询指定租户的保留策略（不存在则自动创建默认策略）"""
    try:
        archive_service = _get_archive_service()
        policy = archive_service.get_retention_policy(tenant_id)
        return RetentionPolicyResponse(**_orm_to_dict(policy))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"查询保留策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/archive/retention-policy/{tenant_id}", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    tenant_id: int,
    request: RetentionPolicyUpdate,
):
    """
    更新指定租户的保留策略

    - 版本号自动 +1，旧版本 is_active 置为 False
    - policy_type=compliance 时强制 cold_retention_days >= 7*365
    - policy_type=operations 时建议 cold_retention_days >= 365
    """
    try:
        archive_service = _get_archive_service()

        data = {k: v for k, v in request.dict().items() if v is not None}
        operator = data.pop('approved_by', None) or 'api_user'

        policy = archive_service.set_retention_policy(
            tenant_id=tenant_id,
            policy_data=data,
            operator=operator,
        )
        return RetentionPolicyResponse(**_orm_to_dict(policy))

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"更新保留策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/archive/retention-policy/{tenant_id}", response_model=RetentionPolicyResponse)
async def create_retention_policy(
    tenant_id: int,
    request: RetentionPolicyCreate,
):
    """创建保留策略（若已存在则按更新逻辑处理，版本+1）"""
    try:
        archive_service = _get_archive_service()

        data = request.dict()
        operator = data.pop('created_by', None) or 'api_user'

        policy = archive_service.set_retention_policy(
            tenant_id=tenant_id,
            policy_data=data,
            operator=operator,
        )
        return RetentionPolicyResponse(**_orm_to_dict(policy))

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"创建保留策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- 冷数据懒加载状态 --------------------

@router.get("/archive/load/{request_id}", response_model=LazyLoadStatusResponse)
async def get_lazy_load_status(request_id: str):
    """
    查询冷数据懒加载请求的状态

    - 状态: pending/loading/completed/failed/partial
    - 异步模式下前端可轮询此接口直到 completed/failed
    """
    try:
        from app.utils.database import get_db, ColdDataLoadRequest

        with get_db() as db:
            req = (
                db.query(ColdDataLoadRequest)
                .filter(ColdDataLoadRequest.request_id == request_id)
                .first()
            )
            if not req:
                raise HTTPException(
                    status_code=404,
                    detail=f"懒加载请求不存在: {request_id}",
                )

            data = _orm_to_dict(req)
            return LazyLoadStatusResponse(**data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"查询懒加载状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- 透明分层查询 --------------------

@router.post("/archive/query/tiered", response_model=TieredQueryResponse)
async def query_tiered_time_series(
    request: TieredQueryRequest,
    background_tasks: BackgroundTasks,
):
    """
    透明分层时序查询（核心接口）

    特性:
    - 按 scenario 自动决定默认读取层级（训练/预测→仅热，分析→热+近冷，合规→全量）
    - 指定时间范围自动路由热/冷数据
    - async_load=True 时冷数据懒加载（返回 request_id 后异步加载）
    - async_load=False 时同步等待冷数据加载（适合合规/导出场景）
    - 自动合并冷热数据并按 create_time 排序
    """
    try:
        router = _get_tiered_router()
        from app.services.tiered_router import (
            TieredQueryRequest as RouterTieredRequest,
            BusinessScenario,
            ReadTier,
        )

        start_ts = datetime.now()

        router_req = RouterTieredRequest(
            tenant_id=request.tenant_id,
            table_name=request.table_name,
            start_time=request.start_time,
            end_time=request.end_time,
            sensor_ids=request.sensor_ids,
            scenario=(
                BusinessScenario(request.scenario.lower())
                if request.scenario else BusinessScenario.CUSTOM
            ),
            read_tier=(
                ReadTier(request.read_tier.lower())
                if request.read_tier else ReadTier.AUTO
            ),
            aggregation_level=request.aggregation_level,
            async_load=request.async_load,
            load_priority=request.load_priority,
            restore_to_hot=request.restore_to_hot,
            auto_upgrade_tier=request.auto_upgrade_tier,
            user_id=request.user_id,
            api_endpoint=request.api_endpoint or '/timeseries/archive/query/tiered',
            restore_expire_hours=request.restore_expire_hours,
        )

        response = router.query(router_req)

        duration_ms = (datetime.now() - start_ts).total_seconds() * 1000

        points = []
        columns = []
        if response.dataframe is not None and not response.dataframe.empty:
            columns = list(response.dataframe.columns)
            df = response.dataframe
            if request.limit:
                if request.order.lower() == 'desc':
                    df = df.tail(request.limit)
                else:
                    df = df.head(request.limit)
            if request.order.lower() == 'desc':
                df = df.iloc[::-1]
            points = df.to_dict(orient='records')

        return TieredQueryResponse(
            success=response.success,
            message=response.warnings[0] if response.warnings else None,
            tenant_id=request.tenant_id,
            effective_read_tier=response.effective_tier.value
            if hasattr(response.effective_tier, 'value')
            else str(response.effective_tier),
            tier_upgraded=response.tier_upgraded,
            tier_upgrade_reason=response.tier_upgrade_reason,
            hot_row_count=response.hot_rows,
            cold_row_count=response.cold_rows,
            total_row_count=response.total_rows,
            cold_files_read=response.cold_files_read,
            cold_bytes_read=response.cold_bytes_loaded,
            duration_ms=round(duration_ms, 2),
            lazy_load_request_id=response.lazy_load_request_id,
            lazy_load_status=response.lazy_load_status,
            points=points,
            columns=columns,
            warnings=response.warnings,
            statistics=response.statistics or {},
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"分层时序查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- 时间范围与层级建议 --------------------

@router.get("/archive/suggest-range", response_model=SuggestedTimeRangeResponse)
async def suggest_time_range(
    tenant_id: int = Query(..., description="租户ID"),
    scenario: str = Query("analysis", description="业务场景: training/prediction/analysis/compliance/..."),
    requested_start: datetime = Query(..., description="用户期望的起始时间"),
    requested_end: datetime = Query(..., description="用户期望的结束时间"),
):
    """
    辅助前端：根据场景与保留策略建议合理时间范围

    - 返回 suggested_start/end（裁剪到可用范围）
    - 返回 hot_cutoff / warm_cutoff，前端可据此高亮冷热分界
    - tier_upgrade_will_happen 提示前端是否将触发冷数据加载
    """
    try:
        router = _get_tiered_router()
        from app.services.tiered_router import BusinessScenario

        scenario_enum = (
            BusinessScenario(scenario.lower())
            if scenario else BusinessScenario.ANALYSIS
        )

        suggestion = router.suggest_time_range(
            tenant_id=tenant_id,
            scenario=scenario_enum,
            requested_start=requested_start,
            requested_end=requested_end,
        )

        return SuggestedTimeRangeResponse(
            tenant_id=tenant_id,
            scenario=scenario,
            requested_start_time=requested_start,
            requested_end_time=requested_end,
            suggested_start_time=suggestion.suggested_start,
            suggested_end_time=suggestion.suggested_end,
            suggested_read_tier=suggestion.suggested_tier.value
            if hasattr(suggestion.suggested_tier, 'value')
            else str(suggestion.suggested_tier),
            required_read_tier=suggestion.required_tier.value
            if hasattr(suggestion.required_tier, 'value')
            else str(suggestion.required_tier),
            hot_cutoff_time=suggestion.hot_cutoff,
            warm_cutoff_time=suggestion.warm_cutoff,
            hot_retention_days=suggestion.hot_retention_days,
            cold_retention_days=suggestion.cold_retention_days,
            warning=suggestion.warning,
            tier_upgrade_will_happen=suggestion.tier_upgrade_will_happen,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"时间范围建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
