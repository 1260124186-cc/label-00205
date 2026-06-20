"""
模型漂移检测 API 路由

提供漂移检测配置管理、基线管理、事件查询、手动触发检测/重训、趋势分析等接口。
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from loguru import logger

from app.api.auth import get_tenant_context, verify_api_key, require_permission
from app.api.model_drift_schemas import (
    DriftConfigCreateRequest,
    DriftConfigUpdateRequest,
    DriftConfigResponse,
    DriftConfigListResponse,
    DriftBaselineResponse,
    DriftBaselineListResponse,
    DriftBaselineCreateRequest,
    DriftEventResponse,
    DriftEventListResponse,
    DriftEventQueryRequest,
    DriftManualDetectionRequest,
    DriftManualDetectionResponse,
    DriftManualRetrainRequest,
    DriftManualRetrainResponse,
    DriftProcessPendingResponse,
    DriftEventAckRequest,
    DriftTrendResponse,
)
from app.services.model_drift import (
    ModelDriftService,
    DriftOrchestrator,
    ModelDriftConfig,
    ModelDriftBaseline,
    ModelDriftEvent,
)
from app.utils.database import db_manager
from app.utils.config import config


router = APIRouter(
    prefix="/model-drift",
    tags=["模型漂移检测"],
    dependencies=[Depends(verify_api_key)],
)


def _ensure_enabled() -> None:
    """确保模型漂移检测已启用"""
    enabled = config.get("model_drift", {}).get("enabled", True)
    if not enabled:
        raise HTTPException(
            status_code=503,
            detail="模型漂移检测功能已禁用，请在配置中启用 model_drift.enabled",
        )


def _orm_to_config_response(cfg: ModelDriftConfig) -> DriftConfigResponse:
    """将 ORM 对象转为响应 Schema"""
    weights_dict = cfg.weights or {}
    thresholds_dict = cfg.thresholds or {}

    return DriftConfigResponse(
        id=cfg.id,
        model_id=cfg.model_id,
        model_type=cfg.model_type,
        version=cfg.version,
        enabled=cfg.enabled,
        response_strategy=cfg.response_strategy,
        thresholds=thresholds_dict if thresholds_dict else None,
        weights=weights_dict if weights_dict else None,
        consecutive_days_alert=cfg.consecutive_days_alert,
        auto_retrain_min_days=cfg.auto_retrain_min_days,
        notify_channels=cfg.notify_channels_list,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


def _orm_to_baseline_response(baseline: ModelDriftBaseline) -> DriftBaselineResponse:
    """将 ORM 对象转为响应 Schema"""
    return DriftBaselineResponse(
        id=baseline.id,
        model_id=baseline.model_id,
        model_type=baseline.model_type,
        version=baseline.version,
        baseline_type=baseline.baseline_type,
        data_window_start=baseline.data_window_start,
        data_window_end=baseline.data_window_end,
        sample_count=baseline.sample_count,
        stats=baseline.stats,
        created_at=baseline.created_at,
    )


def _orm_to_event_response(event: ModelDriftEvent) -> DriftEventResponse:
    """将 ORM 对象转为响应 Schema"""
    return DriftEventResponse(
        id=event.id,
        event_no=event.event_no,
        model_id=event.model_id,
        model_type=event.model_type,
        version=event.version,
        detection_date=event.detection_date,
        drift_level=event.drift_level,
        composite_score=event.composite_score,
        is_alert=event.is_alert,
        triggered_dimensions=event.triggered_dimensions,
        dimension_details=event.dimension_scores,
        feature_drift=event.feature_drift,
        response_strategy=event.response_strategy,
        response_status=event.response_status,
        response_detail=event.response_detail_dict,
        consecutive_days=event.consecutive_days,
        tenant_id=event.tenant_id,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


# ============================================================
# 1. 漂移检测配置管理
# ============================================================

@router.get("/configs", response_model=DriftConfigListResponse, summary="查询漂移检测配置列表")
async def list_drift_configs(
    model_type: Optional[str] = Query(None, description="模型类型过滤：bolt / flange"),
    enabled_only: Optional[bool] = Query(False, description="仅返回已启用的配置"),
    tenant_id: str = Depends(get_tenant_context),
):
    """查询所有漂移检测配置"""
    _ensure_enabled()
    try:
        configs = ModelDriftService.get_drift_configs(
            model_type=model_type,
            enabled_only=enabled_only,
            tenant_id=tenant_id,
        )
        items = [_orm_to_config_response(c) for c in configs]
        return DriftConfigListResponse(total=len(items), items=items)
    except Exception as e:
        logger.exception(f"查询漂移配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/configs/{config_id}", response_model=DriftConfigResponse, summary="查询单个漂移配置")
async def get_drift_config(
    config_id: int,
    tenant_id: str = Depends(get_tenant_context),
):
    """根据ID查询单个漂移配置"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        cfg = session.query(ModelDriftConfig).filter(
            ModelDriftConfig.id == config_id,
            ModelDriftConfig.tenant_id == tenant_id,
        ).first()
        if not cfg:
            raise HTTPException(status_code=404, detail="漂移配置不存在")
        return _orm_to_config_response(cfg)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"查询漂移配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/configs", response_model=DriftConfigResponse, summary="创建漂移检测配置")
async def create_drift_config(
    req: DriftConfigCreateRequest,
    tenant_id: str = Depends(get_tenant_context),
):
    """为指定模型创建漂移检测配置"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        existing = session.query(ModelDriftConfig).filter(
            ModelDriftConfig.model_id == req.model_id,
            ModelDriftConfig.model_type == req.model_type,
            ModelDriftConfig.tenant_id == tenant_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"模型 {req.model_id} ({req.model_type}) 已存在配置，请使用PUT更新"
            )

        import json as _json
        thresholds_dict = req.thresholds.dict() if req.thresholds else {}
        cfg = ModelDriftConfig(
            model_id=req.model_id,
            model_type=req.model_type,
            enabled=req.enabled,
            response_strategy=req.response_strategy,
            psi_threshold=thresholds_dict.get("psi", 0.2),
            ks_threshold=thresholds_dict.get("ks_p_value", 0.05),
            confidence_drift_threshold=thresholds_dict.get("confidence_drift", 0.15),
            false_positive_rate_threshold=thresholds_dict.get("false_positive_rate", 0.10),
            false_positive_window_days=thresholds_dict.get("false_positive_window_days", 7),
            feature_mean_shift_threshold=thresholds_dict.get("feature_mean_shift", 2.0),
            composite_score_threshold=thresholds_dict.get("composite_score", 0.6),
            weights_json=_json.dumps(req.weights.dict()) if req.weights else None,
            consecutive_days_alert=req.consecutive_days_alert,
            auto_retrain_min_days=req.auto_retrain_min_days,
            notify_channels=_json.dumps(req.notify_channels) if req.notify_channels else None,
            notify_targets=_json.dumps(req.notify_targets or {}),
            tenant_id=tenant_id,
        )
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
        logger.info(f"创建漂移配置成功: model_id={cfg.model_id}, model_type={cfg.model_type}")
        return _orm_to_config_response(cfg)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"创建漂移配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/configs/{config_id}", response_model=DriftConfigResponse, summary="更新漂移检测配置")
async def update_drift_config(
    config_id: int,
    req: DriftConfigUpdateRequest,
    tenant_id: str = Depends(get_tenant_context),
):
    """更新漂移检测配置"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        cfg = session.query(ModelDriftConfig).filter(
            ModelDriftConfig.id == config_id,
            ModelDriftConfig.tenant_id == tenant_id,
        ).first()
        if not cfg:
            raise HTTPException(status_code=404, detail="漂移配置不存在")

        import json as _json
        update_data = req.dict(exclude_unset=True)
        if "thresholds" in update_data and update_data["thresholds"]:
            th = update_data["thresholds"]
            if "psi" in th:
                cfg.psi_threshold = th["psi"]
            if "ks_p_value" in th:
                cfg.ks_threshold = th["ks_p_value"]
            if "confidence_drift" in th:
                cfg.confidence_drift_threshold = th["confidence_drift"]
            if "false_positive_rate" in th:
                cfg.false_positive_rate_threshold = th["false_positive_rate"]
            if "false_positive_window_days" in th:
                cfg.false_positive_window_days = th["false_positive_window_days"]
            if "feature_mean_shift" in th:
                cfg.feature_mean_shift_threshold = th["feature_mean_shift"]
            if "composite_score" in th:
                cfg.composite_score_threshold = th["composite_score"]
        if "weights" in update_data and update_data["weights"]:
            cfg.weights_json = _json.dumps(update_data["weights"])
        if "enabled" in update_data:
            cfg.enabled = update_data["enabled"]
        if "response_strategy" in update_data:
            cfg.response_strategy = update_data["response_strategy"]
        if "consecutive_days_alert" in update_data:
            cfg.consecutive_days_alert = update_data["consecutive_days_alert"]
        if "auto_retrain_min_days" in update_data:
            cfg.auto_retrain_min_days = update_data["auto_retrain_min_days"]
        if "notify_channels" in update_data:
            cfg.notify_channels = _json.dumps(update_data["notify_channels"])
        if "notify_targets" in update_data:
            cfg.notify_targets = _json.dumps(update_data["notify_targets"] or {})

        cfg.update_time = datetime.utcnow()
        session.commit()
        session.refresh(cfg)
        logger.info(f"更新漂移配置成功: id={cfg.id}")
        return _orm_to_config_response(cfg)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"更新漂移配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/configs/{config_id}", summary="删除漂移检测配置")
async def delete_drift_config(
    config_id: int,
    tenant_id: str = Depends(get_tenant_context),
):
    """删除指定的漂移检测配置"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        cfg = session.query(ModelDriftConfig).filter(
            ModelDriftConfig.id == config_id,
            ModelDriftConfig.tenant_id == tenant_id,
        ).first()
        if not cfg:
            raise HTTPException(status_code=404, detail="漂移配置不存在")
        session.delete(cfg)
        session.commit()
        logger.info(f"删除漂移配置成功: id={config_id}")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除漂移配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ============================================================
# 2. 漂移基线管理
# ============================================================

@router.get("/baselines", response_model=DriftBaselineListResponse, summary="查询漂移基线列表")
async def list_drift_baselines(
    model_id: Optional[str] = Query(None, description="模型ID过滤"),
    model_type: Optional[str] = Query(None, description="模型类型过滤"),
    baseline_type: Optional[str] = Query(None, description="基线类型过滤"),
    tenant_id: str = Depends(get_tenant_context),
):
    """查询漂移基线列表"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        query = session.query(ModelDriftBaseline).filter(
            ModelDriftBaseline.tenant_id == tenant_id
        )
        if model_id:
            query = query.filter(ModelDriftBaseline.model_id == model_id)
        if model_type:
            query = query.filter(ModelDriftBaseline.model_type == model_type)
        if baseline_type:
            query = query.filter(ModelDriftBaseline.baseline_type == baseline_type)

        baselines = query.order_by(ModelDriftBaseline.created_at.desc()).all()
        items = [_orm_to_baseline_response(b) for b in baselines]
        return DriftBaselineListResponse(total=len(items), items=items)
    except Exception as e:
        logger.exception(f"查询漂移基线失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/baselines", response_model=DriftManualDetectionResponse, summary="创建/刷新漂移基线")
async def create_drift_baseline(
    req: DriftBaselineCreateRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_context),
):
    """
    异步创建/刷新模型漂移基线。
    对于大量数据，基线计算可能需要较长时间，因此在后台任务中执行。
    """
    _ensure_enabled()
    try:
        background_tasks.add_task(
            ModelDriftService.save_baseline,
            model_id=req.model_id,
            model_type=req.model_type,
            version=req.version,
            data_window_start=req.data_window_start,
            data_window_end=req.data_window_end,
            force=req.force,
            tenant_id=tenant_id,
        )
        logger.info(f"已提交基线计算任务: model_id={req.model_id}, model_type={req.model_type}")
        return DriftManualDetectionResponse(
            success=True,
            message="基线计算任务已提交，将在后台执行",
        )
    except Exception as e:
        logger.exception(f"提交基线任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.delete("/baselines/{baseline_id}", summary="删除漂移基线")
async def delete_drift_baseline(
    baseline_id: int,
    tenant_id: str = Depends(get_tenant_context),
):
    """删除指定的漂移基线"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        baseline = session.query(ModelDriftBaseline).filter(
            ModelDriftBaseline.id == baseline_id,
            ModelDriftBaseline.tenant_id == tenant_id,
        ).first()
        if not baseline:
            raise HTTPException(status_code=404, detail="漂移基线不存在")
        session.delete(baseline)
        session.commit()
        logger.info(f"删除漂移基线成功: id={baseline_id}")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除漂移基线失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ============================================================
# 3. 漂移事件查询
# ============================================================

@router.post("/events/query", response_model=DriftEventListResponse, summary="查询漂移事件列表")
async def query_drift_events(
    req: DriftEventQueryRequest,
    tenant_id: str = Depends(get_tenant_context),
):
    """按条件分页查询漂移事件"""
    _ensure_enabled()
    try:
        events, total = ModelDriftService.query_drift_events(
            model_id=req.model_id,
            model_type=req.model_type,
            start_date=req.start_date,
            end_date=req.end_date,
            drift_level=req.drift_level,
            is_alert=req.is_alert,
            response_status=req.response_status,
            page=req.page,
            page_size=req.page_size,
            tenant_id=tenant_id,
        )
        items = [_orm_to_event_response(e) for e in events]
        return DriftEventListResponse(total=total, items=items)
    except Exception as e:
        logger.exception(f"查询漂移事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/events/{event_id}", response_model=DriftEventResponse, summary="查询单个漂移事件详情")
async def get_drift_event(
    event_id: int,
    tenant_id: str = Depends(get_tenant_context),
):
    """查询单个漂移事件的详细信息"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        event = session.query(ModelDriftEvent).filter(
            ModelDriftEvent.id == event_id,
            ModelDriftEvent.tenant_id == tenant_id,
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="漂移事件不存在")
        return _orm_to_event_response(event)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"查询漂移事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/events/{event_id}/ack", summary="确认/忽略漂移事件")
async def acknowledge_drift_event(
    event_id: int,
    req: DriftEventAckRequest,
    tenant_id: str = Depends(get_tenant_context),
):
    """人工确认漂移事件，将响应状态标记为已确认"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        event = session.query(ModelDriftEvent).filter(
            ModelDriftEvent.id == event_id,
            ModelDriftEvent.tenant_id == tenant_id,
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="漂移事件不存在")

        detail = event.response_detail_dict or {}
        detail["acknowledged"] = True
        detail["ack_note"] = req.ack_note
        detail["ack_at"] = datetime.utcnow().isoformat()
        event.response_detail = detail
        if event.response_status in (None, "pending"):
            event.response_status = "skipped"
        event.update_time = datetime.utcnow()
        session.commit()
        logger.info(f"确认漂移事件: id={event_id}, note={req.ack_note}")
        return {"success": True, "message": "已确认"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"确认漂移事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


# ============================================================
# 4. 手动触发检测/重训
# ============================================================

@router.post("/detect", response_model=DriftManualDetectionResponse, summary="手动触发漂移检测")
async def manual_trigger_detection(
    req: DriftManualDetectionRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_context),
):
    """
    手动触发一次漂移检测。
    对于大量模型，检测可能耗时较长，支持后台异步执行。
    """
    _ensure_enabled()
    try:
        detection_date = req.detection_date or date.today()
        model_types = req.model_types or ["bolt", "flange"]

        result = await ModelDriftService.run_daily_drift_detection(
            detection_date=detection_date,
            model_types=model_types,
            tenant_id=tenant_id,
        )

        alert_count = 0
        for item in result:
            if item.get("is_alert"):
                alert_count += 1

        logger.info(
            f"手动漂移检测完成: date={detection_date}, "
            f"models={len(result)}, alerts={alert_count}"
        )
        return DriftManualDetectionResponse(
            success=True,
            detection_date=detection_date,
            processed_models=len(result),
            alert_count=alert_count,
            message=f"检测完成，处理{len(result)}个模型，产生{alert_count}个告警",
        )
    except Exception as e:
        logger.exception(f"手动漂移检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/retrain", response_model=DriftManualRetrainResponse, summary="手动触发模型重训")
async def manual_trigger_retrain(
    req: DriftManualRetrainRequest,
    tenant_id: str = Depends(get_tenant_context),
):
    """
    手动触发模型重训，支持 shadow_retrain 或 auto_retrain 策略。
    """
    _ensure_enabled()
    try:
        if req.strategy not in ("shadow_retrain", "auto_retrain"):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的策略: {req.strategy}，仅支持 shadow_retrain / auto_retrain"
            )

        session = db_manager.get_session()
        config = session.query(ModelDriftConfig).filter(
            ModelDriftConfig.model_id == req.model_id,
            ModelDriftConfig.model_type == req.model_type,
            ModelDriftConfig.tenant_id == tenant_id,
        ).first()
        if not config:
            config = ModelDriftConfig(
                model_id=req.model_id,
                model_type=req.model_type,
                tenant_id=tenant_id,
            )

        event_data = {
            "model_id": req.model_id,
            "model_type": req.model_type,
            "version": None,
            "event_no": f"MANUAL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "detection_date": date.today().isoformat(),
            "composite_score": 0.8,
            "drift_level": "high",
            "triggered_dimensions": ["manual_trigger"],
            "consecutive_days": 1,
            "tenant_id": tenant_id,
        }

        if req.strategy == "shadow_retrain":
            result = DriftOrchestrator._execute_shadow_retrain(event_data, config)
        else:
            result = DriftOrchestrator._execute_auto_retrain(event_data, config, force=req.force)

        success = result.get("success", False)
        training_task_id = result.get("training_task_id") if success else None
        msg = result.get("message", "操作完成")

        logger.info(
            f"手动重训触发: model_id={req.model_id}, strategy={req.strategy}, "
            f"success={success}, task_id={training_task_id}"
        )
        return DriftManualRetrainResponse(
            success=success,
            model_id=req.model_id,
            model_type=req.model_type,
            strategy=req.strategy,
            training_task_id=training_task_id,
            message=msg,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"手动触发重训失败: {e}")
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


# ============================================================
# 5. 响应处理
# ============================================================

@router.post("/process-pending", response_model=DriftProcessPendingResponse, summary="处理待响应的漂移事件")
async def process_pending_events(
    limit: int = Query(50, ge=1, le=500, description="最多处理的事件数"),
    tenant_id: str = Depends(get_tenant_context),
):
    """
    立即处理所有 pending 状态的漂移事件（按响应策略执行通知/重训等）。
    """
    _ensure_enabled()
    try:
        result = DriftOrchestrator.process_pending_events(limit=limit, tenant_id=tenant_id)
        logger.info(
            f"处理待响应漂移事件完成: total={result.get('total_pending')}, "
            f"processed={result.get('processed_count')}, "
            f"success={result.get('success_count')}, failed={result.get('failed_count')}"
        )
        return DriftProcessPendingResponse(
            success=True,
            total_pending=result.get("total_pending"),
            processed_count=result.get("processed_count"),
            success_count=result.get("success_count"),
            failed_count=result.get("failed_count"),
        )
    except Exception as e:
        logger.exception(f"处理待响应事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


# ============================================================
# 6. 漂移趋势分析
# ============================================================

@router.get("/trend", response_model=DriftTrendResponse, summary="查询指定模型的漂移趋势")
async def get_drift_trend(
    model_id: str = Query(..., description="模型ID"),
    model_type: str = Query(..., description="模型类型：bolt / flange"),
    days: int = Query(30, ge=7, le=180, description="查询最近N天数据"),
    tenant_id: str = Depends(get_tenant_context),
):
    """查询指定模型在过去一段时间内的漂移分数变化趋势"""
    _ensure_enabled()
    try:
        session = db_manager.get_session()
        start_date = date.today() - timedelta(days=days)

        events = session.query(ModelDriftEvent).filter(
            ModelDriftEvent.model_id == model_id,
            ModelDriftEvent.model_type == model_type,
            ModelDriftEvent.detection_date >= start_date,
            ModelDriftEvent.tenant_id == tenant_id,
        ).order_by(ModelDriftEvent.detection_date.asc()).all()

        points = []
        for evt in events:
            points.append({
                "detection_date": evt.detection_date,
                "composite_score": evt.composite_score,
                "drift_level": evt.drift_level,
                "is_alert": evt.is_alert,
            })

        return DriftTrendResponse(
            model_id=model_id,
            model_type=model_type,
            points=points,
        )
    except Exception as e:
        logger.exception(f"查询漂移趋势失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
