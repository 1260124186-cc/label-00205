from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger

from app.api.auth import verify_api_key
from app.api.threshold_schemas import (
    NodeThresholdCreateRequest,
    NodeThresholdUpdateRequest,
    NodeThresholdResponse,
    EffectiveThresholdResponse,
    NodeThresholdListResponse,
    ThresholdAuditLogResponse,
    ThresholdAuditLogListResponse,
    ThresholdBatchImportRequest,
    ThresholdBatchImportResponse,
    ThresholdBatchImportResultSchema,
)
from app.services.prediction.threshold_service import (
    get_threshold_service,
    get_effective_threshold,
    get_resolution_chain,
    ThresholdService,
)


router = APIRouter(
    prefix="/thresholds",
    tags=["动态阈值"],
    dependencies=[Depends(verify_api_key)],
)


@router.get(
    "/{node_type}/{node_id}",
    response_model=NodeThresholdListResponse,
    summary="获取节点阈值配置",
)
async def get_node_thresholds(
    node_type: str,
    node_id: str,
    threshold_type: Optional[str] = Query(None, description="阈值类型过滤"),
    scope: Optional[str] = Query(None, description="作用域过滤"),
    source: Optional[str] = Query(None, description="来源过滤"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
    limit: int = Query(100, ge=1, le=500),
):
    service = get_threshold_service()
    rows = service.list_thresholds(
        node_type=node_type,
        node_id=node_id,
        scope=scope,
        source=source,
        threshold_type=threshold_type,
        is_active=is_active,
        limit=limit,
    )
    items = [NodeThresholdResponse(**r) for r in rows]
    return NodeThresholdListResponse(total=len(items), items=items)


@router.get(
    "/{node_type}/{node_id}/effective",
    response_model=EffectiveThresholdResponse,
    summary="获取生效阈值（含优先级解析）",
)
async def get_effective(
    node_type: str,
    node_id: str,
    threshold_type: str = Query(..., description="阈值类型: preload/risk/health_index/confidence"),
    flange_id: Optional[str] = Query(None, description="法兰面ID（用于法兰默认级解析）"),
):
    effective = get_effective_threshold(node_type, node_id, threshold_type, flange_id)
    chain = get_resolution_chain(node_type, node_id, threshold_type, flange_id)
    return EffectiveThresholdResponse(
        node_type=node_type,
        node_id=node_id,
        threshold_type=threshold_type,
        effective=NodeThresholdResponse(**effective),
        resolution_chain=chain,
    )


@router.put(
    "/{node_type}/{node_id}",
    response_model=NodeThresholdResponse,
    summary="创建或更新节点阈值",
)
async def upsert_threshold(
    node_type: str,
    node_id: str,
    request: NodeThresholdCreateRequest,
):
    if node_type not in ('bolt', 'flange'):
        raise HTTPException(status_code=400, detail="node_type must be bolt or flange")
    if request.source not in ('design', 'statistical', 'manual'):
        raise HTTPException(status_code=400, detail="source must be design, statistical, or manual")

    service = get_threshold_service()
    result = service.upsert_threshold(
        node_type=node_type,
        node_id=node_id,
        scope=request.scope,
        source=request.source,
        threshold_type=request.threshold_type,
        parameters=request.parameters,
        description=request.description,
        design_value=request.design_value,
        deviation_ratio=request.deviation_ratio,
        statistical_mean=request.statistical_mean,
        statistical_std=request.statistical_std,
        statistical_sample_count=request.statistical_sample_count,
        statistical_window_days=request.statistical_window_days,
        operator_id=request.operator_id,
        operator_name=request.operator_name,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to upsert threshold")
    return NodeThresholdResponse(**result)


@router.delete(
    "/{node_type}/{node_id}",
    summary="删除节点阈值",
)
async def delete_threshold(
    node_type: str,
    node_id: str,
    threshold_type: str = Query(..., description="阈值类型"),
    scope: str = Query('node', description="作用域"),
    operator_id: Optional[str] = Query(None, description="操作人ID"),
    operator_name: Optional[str] = Query(None, description="操作人姓名"),
):
    service = get_threshold_service()
    ok = service.delete_threshold(
        node_type=node_type,
        node_id=node_id,
        threshold_type=threshold_type,
        scope=scope,
        operator_id=operator_id,
        operator_name=operator_name,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Threshold not found")
    return {"status": "deleted", "node_type": node_type, "node_id": node_id, "threshold_type": threshold_type}


@router.post(
    "/batch-import",
    response_model=ThresholdBatchImportResponse,
    summary="批量导入阈值配置",
)
async def batch_import(request: ThresholdBatchImportRequest):
    service = get_threshold_service()
    result = service.batch_import(
        items=[item.model_dump() for item in request.items],
        operator_id=request.operator_id,
        operator_name=request.operator_name,
    )
    return ThresholdBatchImportResponse(
        status="success" if result['errors'] == 0 else "partial",
        message=f"Imported {result['created'] + result['updated']}/{result['total']}, "
                f"errors={result['errors']}",
        result=ThresholdBatchImportResultSchema(**result),
    )


@router.get(
    "/audit/logs",
    response_model=ThresholdAuditLogListResponse,
    summary="查询阈值变更审计日志",
)
async def get_audit_logs(
    node_type: Optional[str] = Query(None, description="节点类型"),
    node_id: Optional[str] = Query(None, description="节点ID"),
    threshold_type: Optional[str] = Query(None, description="阈值类型"),
    action: Optional[str] = Query(None, description="操作类型"),
    operator_id: Optional[str] = Query(None, description="操作人ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    service = get_threshold_service()
    rows = service.get_audit_logs(
        node_type=node_type,
        node_id=node_id,
        threshold_type=threshold_type,
        action=action,
        operator_id=operator_id,
        limit=limit,
        offset=offset,
    )
    items = [ThresholdAuditLogResponse(**r) for r in rows]
    return ThresholdAuditLogListResponse(total=len(items), items=items)
