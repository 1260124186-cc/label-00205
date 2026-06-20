"""
下游增量同步 API 路由

提供基于游标的增量数据拉取接口：
1. GET /sync/predictions - 预测结果增量同步
2. GET /sync/bolt-data - 原始螺栓数据增量同步
3. GET /sync/status - 同步游标状态查询

核心特性：
- 基于单调递增 id 的游标（since_id）或基于时间的游标（since_time）
- 租户级数据隔离（通过 X-Tenant-API-Key / X-Tenant-Token）
- ETag / If-None-Match 缓存机制减少带宽
- SLA 监控：增量延迟 < 1 分钟（批处理场景）
- API Key 权限：sync:read 或 read
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response
from loguru import logger

from app.api.auth import (
    verify_api_key,
    require_permission,
    get_tenant_context,
)
from app.api.schemas import (
    SyncPredictionsResponse,
    SyncPredictionItemSchema,
    SyncBoltDataResponse,
    SyncBoltDataItemSchema,
    SyncStatusResponse,
    SyncCursorStatusSchema,
)
from app.services.sync_service import get_sync_service, SyncService


router = APIRouter(prefix="/sync", tags=["下游增量同步"])


def _resolve_tenant_id(tenant_context: dict) -> Optional[int]:
    """从租户上下文解析租户ID"""
    tid = tenant_context.get("tenant_id")
    if tid is not None:
        return int(tid)
    return None


# ==================== 预测结果增量同步 ====================

@router.get(
    "/predictions",
    response_model=SyncPredictionsResponse,
    summary="预测结果增量同步（基于游标）",
    description="""
## 预测结果增量同步

基于单调递增 id 或 update_time 游标拉取增量预测结果。

### 使用方式
1. 首次调用不传 since_id（或传 0），获取初始数据
2. 使用返回的 next_since_id 作为下次请求的 since_id
3. 循环直到 has_more=false

### SLA
- 增量延迟 < 1 分钟（批处理场景）
- 返回头包含 X-SLA-Latency 延迟指标

### 缓存优化
- 响应包含 ETag 头
- 下次请求可带 If-None-Match 头，若数据未变化返回 304
""",
    dependencies=[Depends(require_permission("sync:read"))],
)
async def sync_predictions(
    request: Request,
    response: Response,
    since_id: int = Query(
        0,
        description="起始记录ID（单调递增游标），> 0 时生效，0 表示从头开始",
        ge=0,
    ),
    since_time: Optional[datetime] = Query(
        None,
        description="基于时间的游标（可选），返回该时间之后的新增记录",
    ),
    limit: int = Query(
        500,
        description="单次返回记录数上限",
        ge=1,
        le=10000,
    ),
    node_type: Optional[str] = Query(
        None,
        description="按节点类型过滤：bolt / flange，不填返回全部",
        pattern="^(bolt|flange)$",
    ),
    tenant_context: dict = Depends(get_tenant_context),
):
    """
    GET /sync/predictions
    """
    try:
        tenant_id = _resolve_tenant_id(tenant_context)
        service: SyncService = get_sync_service()

        result = service.sync_predictions(
            tenant_id=tenant_id,
            since_id=since_id,
            since_time=since_time,
            limit=limit,
            node_type=node_type,
        )

        # 生成 ETag
        etag = service.generate_etag(
            resource="predictions",
            tenant_id=tenant_id,
            next_since_id=result.next_since_id,
            returned_count=result.returned_count,
        )
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "no-cache"

        # 检查 If-None-Match
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match == etag:
            response.status_code = 304
            return Response(status_code=304)

        # SLA 延迟指标
        sla_latency = service.calculate_sla_latency(result.latest_create_time)
        if sla_latency is not None:
            response.headers["X-SLA-Latency"] = f"{sla_latency:.2f}"
        response.headers["X-SLA-Target"] = "60"

        # 组装响应
        items = [SyncPredictionItemSchema(**item) for item in result.items]

        return SyncPredictionsResponse(
            items=items,
            next_since_id=result.next_since_id,
            has_more=result.has_more,
            limit=limit,
            returned_count=result.returned_count,
            server_time=datetime.now(),
            data_source=result.data_source,
            sla_latency_seconds=sla_latency,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"预测结果增量同步异常: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "InternalServerError", "message": str(e)},
        )


# ==================== 螺栓原始数据增量同步 ====================

@router.get(
    "/bolt-data",
    response_model=SyncBoltDataResponse,
    summary="螺栓原始数据增量同步（支持脱敏）",
    description="""
## 螺栓原始数据增量同步

基于单调递增 id 或 update_time 游标拉取螺栓原始采集数据。

### 数据脱敏
- desensitize=true 时，collector_id、splitter_num、position 会被哈希处理
- 预紧力值（ptf）及传感器测量值始终保留（用于分析）

### SLA
- 增量延迟 < 1 分钟（批处理场景）
- 返回头包含 X-SLA-Latency 延迟指标

### 缓存优化
- 响应包含 ETag 头
- 下次请求可带 If-None-Match 头，若数据未变化返回 304
""",
    dependencies=[Depends(require_permission("sync:read"))],
)
async def sync_bolt_data(
    request: Request,
    response: Response,
    since_id: int = Query(
        0,
        description="起始记录ID（单调递增游标），> 0 时生效",
        ge=0,
    ),
    since_time: Optional[datetime] = Query(
        None,
        description="基于时间的游标（可选），返回该时间之后的新增记录",
    ),
    limit: int = Query(
        500,
        description="单次返回记录数上限",
        ge=1,
        le=10000,
    ),
    desensitize: bool = Query(
        False,
        description="是否脱敏：哈希 collector_id、splitter_num、position 字段",
    ),
    sensor_ids: Optional[str] = Query(
        None,
        description="按传感器ID过滤，逗号分隔，如 1001,1002,1003",
    ),
    tenant_context: dict = Depends(get_tenant_context),
):
    """
    GET /sync/bolt-data
    """
    try:
        tenant_id = _resolve_tenant_id(tenant_context)
        service: SyncService = get_sync_service()

        # 解析 sensor_ids
        parsed_sensor_ids: Optional[List[int]] = None
        if sensor_ids:
            try:
                parsed_sensor_ids = [
                    int(s.strip()) for s in sensor_ids.split(",") if s.strip()
                ]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "InvalidParameter",
                        "message": "sensor_ids 格式错误，应为逗号分隔的整数",
                    },
                )

        result = service.sync_bolt_data(
            tenant_id=tenant_id,
            since_id=since_id,
            since_time=since_time,
            limit=limit,
            desensitize=desensitize,
            sensor_ids=parsed_sensor_ids,
        )

        # 生成 ETag
        etag = service.generate_etag(
            resource=f"bolt-data:desensitize={desensitize}",
            tenant_id=tenant_id,
            next_since_id=result.next_since_id,
            returned_count=result.returned_count,
        )
        response.headers["ETag"] = etag
        response.headers["Cache-Control"] = "no-cache"

        # 检查 If-None-Match
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match == etag:
            response.status_code = 304
            return Response(status_code=304)

        # SLA 延迟指标
        sla_latency = service.calculate_sla_latency(result.latest_create_time)
        if sla_latency is not None:
            response.headers["X-SLA-Latency"] = f"{sla_latency:.2f}"
        response.headers["X-SLA-Target"] = "60"
        response.headers["X-Data-Desensitized"] = "true" if desensitize else "false"

        # 组装响应
        items = [SyncBoltDataItemSchema(**item) for item in result.items]

        return SyncBoltDataResponse(
            items=items,
            next_since_id=result.next_since_id,
            next_since_time=result.next_since_time,
            has_more=result.has_more,
            limit=limit,
            returned_count=result.returned_count,
            server_time=datetime.now(),
            data_source=result.data_source,
            desensitized=desensitize,
            sla_latency_seconds=sla_latency,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"螺栓原始数据增量同步异常: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "InternalServerError", "message": str(e)},
        )


# ==================== 同步状态查询 ====================

@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="同步游标状态查询",
    description="""
## 同步状态查询

查看当前租户在各资源上的最新游标位置和同步状态，
用于监控和 SLA 验证。
""",
    dependencies=[Depends(require_permission("sync:read"))],
)
async def sync_status(
    response: Response,
    tenant_context: dict = Depends(get_tenant_context),
):
    """
    GET /sync/status
    """
    try:
        tenant_id = _resolve_tenant_id(tenant_context)
        service: SyncService = get_sync_service()

        status = service.get_sync_status(tenant_id=tenant_id)

        pred_cursor = None
        if status.get("predictions_cursor"):
            pred_cursor = SyncCursorStatusSchema(**status["predictions_cursor"])

        bolt_cursor = None
        if status.get("bolt_data_cursor"):
            bolt_cursor = SyncCursorStatusSchema(**status["bolt_data_cursor"])

        response.headers["X-SLA-Target"] = "60"

        return SyncStatusResponse(
            tenant_id=status.get("tenant_id") or 0,
            predictions_cursor=pred_cursor,
            bolt_data_cursor=bolt_cursor,
            server_time=status["server_time"],
            sla_target_seconds=status["sla_target_seconds"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"同步状态查询异常: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "InternalServerError", "message": str(e)},
        )
