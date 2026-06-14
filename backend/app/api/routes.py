"""
API路由定义

定义所有REST API端点和处理逻辑。

端点:
- GET /health: 健康检查
- POST /predict/bolt: 螺栓状态预测
- POST /predict/flange: 法兰面状态预测
- POST /risk/assess: 风险评估
- POST /forecast/monthly: 月度预测
- POST /model/train: 模型训练
- GET /model/info: 模型信息
- POST /strategy/config: 策略配置
"""

import numpy as np
import pandas as pd
import json
import os
import torch
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from loguru import logger

from app.api.schemas import (
    HealthResponse, ErrorResponse,
    BoltPredictionRequest, BoltPredictionResponse,
    FlangePredictionRequest, FlangePredictionResponse,
    RiskAssessmentRequest, RiskAssessmentResponse,
    MonthlyForecastRequest, MonthlyForecastResponse,
    TrainingRequest, TrainingResponse,
    ModelInfoResponse,
    StrategyConfigRequest, StrategyConfigResponse,
    FederatedClientRegisterRequest, FederatedClientRegisterResponse,
    FederatedGlobalModelRequest, FederatedGlobalModelResponse,
    FederatedUpdateUploadRequest, FederatedUpdateUploadResponse,
    FederatedRoundStartRequest, FederatedRoundStartResponse,
    FederatedRoundAggregateRequest, FederatedRoundAggregateResponse,
    FederatedServerStatusResponse,
    FederatedModelHistoryRequest, FederatedModelHistoryResponse,
    FederatedClientStatusResponse,
    FederatedLocalTrainRequest, FederatedLocalTrainResponse,
    FederatedPrivacyConfig, FederatedAggregatorConfig,
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AlertEventResponse, AlertHandleRequest, AlertListResponse,
    AlertSubscriptionCreate, AlertSubscriptionUpdate, AlertSubscriptionResponse,
    NotificationChannelCreate, NotificationChannelUpdate, NotificationChannelResponse,
    NotificationLogResponse,
    WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse,
    WorkOrderAssignRequest, WorkOrderResolveRequest,
    WorkOrderStatusUpdateRequest, WorkOrderListResponse,
    DisposalRecordCreate, DisposalRecordUpdate, DisposalRecordResponse,
    DisposalRecordListResponse,
    RetestRecordCreate, RetestRecordUpdate, RetestRecordResponse,
    RetestRecordListResponse,
    PredictionCompareResponse, PredictionCompareListResponse,
    WorkOrderStatsRequest, WorkOrderStatsResponse,
    MttrTrendResponse,
    CmmsConfigCreate, CmmsConfigUpdate, CmmsConfigResponse,
    CmmsConfigListResponse,
    CmmsSyncRequest, CmmsSyncResponse,
    CmmsSyncLogResponse, CmmsSyncLogListResponse,
    CmmsWebhookResponse,
    AlertUpgradeTriggerResponse,
    AuditRecordResponse, AuditListResponse,
    AuditRetentionUpdateRequest, AuditCleanupResponse,
    AuditExportRequest, ExplainabilityReportResponse,
    DataQualityCheckRequest, DataQualityCheckBatchRequest,
    QualityReportRequest, DataQualityHistoryRequest,
    ConfidenceAdjustmentRequest, ConfidenceAdjustmentResponse,
    QualityEvaluationResponse, DailyQualityReportSchema,
    SensorQualityScoreSchema,
    EdgeModelLatestRequest, EdgeModelLatestResponse,
    EdgeModelDownloadResponse, EdgePredictionUploadRequest,
    EdgePredictionUploadResponse, EdgeModelExportRequest,
    EdgeModelExportResponse, EdgeDeviceRegisterRequest,
    EdgeDeviceRegisterResponse, EdgeDeviceHeartbeatRequest,
    EdgeDeviceHeartbeatResponse,
    TenantCreateRequest, TenantUpdateRequest, TenantResponse, TenantListResponse,
    OrgNodeCreateRequest, OrgNodeUpdateRequest, OrgNodeResponse, OrgTreeResponse,
    QuotaUpdateRequest, QuotaResponse,
    TenantUserCreateRequest, TenantUserUpdateRequest, TenantUserPasswordRequest,
    TenantUserResponse, TenantUserListResponse,
    TenantAPIKeyCreateRequest, TenantAPIKeyUpdateRequest,
    TenantAPIKeyResponse, TenantAPIKeyCreateResponse,
    TenantLoginRequest, TenantLoginResponse,
    KnowledgeCaseCreateRequest, KnowledgeCaseUpdateRequest,
    KnowledgeCaseResponse, KnowledgeCaseListResponse,
    CaseReviewRequest, CaseReviewResponse,
    CaseVersionResponse, CaseVersionCompareResponse,
    CaseSimilaritySearchRequest, CaseSimilaritySearchResponse,
    CaseRecommendationResponse,
    HealthIndexFactorSchema, HealthIndexDetailSchema,
    BoltHealthIndexSchema, FlangeHealthIndexSchema,
    ProductionLineHealthRollupSchema,
    RULPredictionPointSchema, RULPredictionSchema,
    DegradationCurvePointSchema, DegradationCurveSchema,
    HealthIndexCalculateRequest, HealthIndexBatchCalculateRequest,
    HealthIndexHistoryRequest, RULPredictionRequest,
    HealthRollupRequest,
    HealthIndexResponse, HealthIndexBatchResponse,
    HealthIndexHistoryResponse,
    RULPredictionResponse, HealthRollupResponse,
    StreamDataIngestRequest, StreamBatchIngestRequest,
    StreamModeSwitchRequest, StreamConfigUpdateRequest,
    StreamDataIngestResponse, StreamBatchIngestResponse,
    StreamWindowStatusResponse, StreamEngineStatusResponse,
    StreamModeSwitchResponse, StreamConfigResponse,
    StreamEventSchema,
)
from app.services.prediction_service import PredictionService
from app.services.training_service import TrainingService
from app.utils.config import config
from app import __version__


# 创建路由器
router = APIRouter()

# 服务实例
prediction_service = None
training_service = None
federated_server = None
federated_clients: Dict[str, Any] = {}


def get_prediction_service() -> PredictionService:
    """获取预测服务实例"""
    global prediction_service
    if prediction_service is None:
        prediction_service = PredictionService()
    return prediction_service


def get_training_service() -> TrainingService:
    """获取训练服务实例"""
    global training_service
    if training_service is None:
        training_service = TrainingService()
    return training_service


def get_federated_server():
    """获取联邦学习服务器实例"""
    global federated_server
    if federated_server is None:
        from app.federated import FederatedServer, ServerConfig, AggregationStrategy

        # 从配置获取参数
        fed_config = config.get('federated', {})

        server_config = ServerConfig(
            aggregation_strategy=AggregationStrategy(
                fed_config.get('aggregation_strategy', 'weighted_avg')
            ),
            aggregation_config=fed_config.get('aggregation_config'),
            privacy_config=fed_config.get('privacy_config'),
            min_clients_per_round=fed_config.get('min_clients_per_round', 2),
            enable_two_level_arch=fed_config.get('enable_two_level_arch', True),
            save_path=fed_config.get('save_path', './trained_models/federated')
        )

        federated_server = FederatedServer(server_config)
    return federated_server


def get_federated_client(client_id: str):
    """获取或创建联邦学习客户端实例"""
    global federated_clients

    if client_id not in federated_clients:
        from app.federated import FederatedClient, ClientConfig, UpdateType

        # 从配置获取参数
        fed_config = config.get('federated', {})
        client_config_dict = fed_config.get('client_config', {})

        client_config = ClientConfig(
            factory_id=client_id,
            update_type=UpdateType(client_config_dict.get('update_type', 'difference')),
            local_epochs=client_config_dict.get('local_epochs', 5),
            enable_two_level_arch=client_config_dict.get('enable_two_level_arch', True),
            privacy_config=client_config_dict.get('privacy_config')
        )

        federated_clients[client_id] = FederatedClient(client_id, client_config)

    return federated_clients[client_id]


# ==================== 健康检查 ====================

@router.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """
    健康检查接口

    返回服务状态和版本信息。
    """
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now()
    )


# ==================== 螺栓预测 ====================

@router.post(
    "/predict/bolt",
    response_model=BoltPredictionResponse,
    tags=["预测"],
    summary="螺栓状态预测"
)
async def predict_bolt(request: BoltPredictionRequest):
    """
    预测单个螺栓的状态

    基于最近100条预紧力数据，预测螺栓当前状态。

    状态类别:
    - 0: 正常
    - 1: 关注级预警
    - 2: 检查级预警
    - 3: 紧急级预警
    - 4: 故障
    """
    try:
        service = get_prediction_service()

        # 获取螺栓ID（支持中文字段名）
        bolt_id = getattr(request, '螺栓id', None) or request.bolt_id

        # 解析输入数据
        timestamps = []
        values = []

        for item in request.data:
            if len(item) >= 2:
                timestamps.append(item[0])
                values.append(float(item[1]))

        if len(values) == 0:
            raise HTTPException(status_code=400, detail="数据为空")

        # 执行预测
        result = service.predict_bolt(
            bolt_id=bolt_id,
            data=np.array(values),
            timestamps=timestamps
        )

        return BoltPredictionResponse(
            bolt_id=bolt_id,
            status=result['status'],
            status_code=result['status_code'],
            confidence=result['confidence'],
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            diagnosis=result['diagnosis'],
            recommendations=result['recommendations'],
            prediction_time=datetime.now()
        )

    except Exception as e:
        logger.error(f"螺栓预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 法兰面预测 ====================

@router.post(
    "/predict/flange",
    response_model=FlangePredictionResponse,
    tags=["预测"],
    summary="法兰面状态预测"
)
async def predict_flange(request: FlangePredictionRequest):
    """
    预测法兰面的整体状态

    基于法兰面上所有螺栓的预紧力数据，预测法兰面状态。
    """
    try:
        service = get_prediction_service()

        # 获取法兰面ID
        flange_id = getattr(request, '法兰面id', None) or request.flange_id

        # 解析多螺栓数据
        multi_bolt_data = []

        for bolt_data in request.data:
            values = []
            for item in bolt_data:
                if len(item) >= 2:
                    values.append(float(item[1]))
            if values:
                multi_bolt_data.append(np.array(values))

        if len(multi_bolt_data) == 0:
            raise HTTPException(status_code=400, detail="数据为空")

        # 执行预测
        result = service.predict_flange(
            flange_id=flange_id,
            multi_bolt_data=multi_bolt_data
        )

        return FlangePredictionResponse(
            flange_id=flange_id,
            status=result['status'],
            status_code=result['status_code'],
            confidence=result['confidence'],
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            bolt_count=len(multi_bolt_data),
            attention_weights=result.get('attention_weights'),
            diagnosis=result['diagnosis'],
            recommendations=result['recommendations'],
            prediction_time=datetime.now()
        )

    except Exception as e:
        logger.error(f"法兰面预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 风险评估 ====================

@router.post(
    "/risk/assess",
    response_model=RiskAssessmentResponse,
    tags=["风险评估"],
    summary="风险评估"
)
async def assess_risk(request: RiskAssessmentRequest):
    """
    评估节点（螺栓或法兰面）的风险

    返回风险评分(1-10)和风险等级(低/中/高)。
    """
    try:
        service = get_prediction_service()

        # 解析数据
        values = []
        for item in request.data:
            if len(item) >= 2:
                values.append(float(item[1]))

        if len(values) == 0:
            raise HTTPException(status_code=400, detail="数据为空")

        # 执行评估
        result = service.assess_risk(
            node_id=request.node_id,
            node_type=request.node_type,
            data=np.array(values)
        )

        return RiskAssessmentResponse(
            node_id=request.node_id,
            node_type=request.node_type,
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            factors=result['factors'],
            diagnosis=result['diagnosis'],
            recommendations=result['recommendations'],
            confidence=result['confidence']
        )

    except Exception as e:
        logger.error(f"风险评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 月度预测 ====================

@router.post(
    "/forecast/monthly",
    response_model=MonthlyForecastResponse,
    tags=["预测"],
    summary="月度趋势预测"
)
async def forecast_monthly(request: MonthlyForecastRequest):
    """
    预测未来30天的状态趋势

    使用Prophet时间序列模型进行趋势预测。
    """
    try:
        service = get_prediction_service()

        result = service.forecast_monthly(
            node_id=request.node_id,
            node_type=request.node_type,
            days=request.forecast_days
        )

        return MonthlyForecastResponse(
            node_id=request.node_id,
            node_type=request.node_type,
            pw_type=result['pw_type'],
            fault_type=result.get('fault_type'),
            begin_time=result.get('begin_time'),
            end_time=result.get('end_time'),
            confidence=result['confidence'],
            rec_measures=result['rec_measures'],
            forecast_dates=result['forecast_dates'],
            forecast_values=result['forecast_values'].tolist() if hasattr(result['forecast_values'], 'tolist') else result['forecast_values']
        )

    except Exception as e:
        logger.error(f"月度预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 模型训练 ====================

@router.post(
    "/model/train",
    response_model=TrainingResponse,
    tags=["模型管理"],
    summary="训练模型"
)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks
):
    """
    训练或重新训练模型

    可以选择训练特定节点的模型或所有模型。
    训练任务在后台执行。
    """
    try:
        service = get_training_service()

        # 在后台执行训练
        background_tasks.add_task(
            service.train_model,
            model_type=request.model_type,
            node_id=request.node_id,
            force_retrain=request.force_retrain
        )

        return TrainingResponse(
            model_type=request.model_type,
            node_id=request.node_id,
            status="started",
            message="训练任务已启动，将在后台执行",
            training_time=0,
            metrics=None
        )

    except Exception as e:
        logger.error(f"启动训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/info/{model_type}/{node_id}",
    response_model=ModelInfoResponse,
    tags=["模型管理"],
    summary="获取模型信息"
)
async def get_model_info(model_type: str, node_id: str):
    """
    获取指定模型的信息

    包括训练状态、最后训练时间、验证准确率等。
    """
    try:
        service = get_training_service()

        info = service.get_model_info(model_type, node_id)

        return ModelInfoResponse(
            model_type=model_type,
            node_id=node_id,
            is_trained=info['is_trained'],
            last_training_time=info.get('last_training_time'),
            training_samples=info.get('training_samples'),
            validation_accuracy=info.get('validation_accuracy')
        )

    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 策略配置 ====================

@router.post(
    "/strategy/config",
    response_model=StrategyConfigResponse,
    tags=["配置"],
    summary="配置预警策略"
)
async def config_strategy(request: StrategyConfigRequest):
    """
    配置预警策略

    策略1: 应报尽报，可能误报
    策略2: 精准报警，可能漏报
    """
    try:
        # 更新配置（这里简化处理，实际应该持久化）
        strategy_config = config.get('warning_strategy', {})

        strategy_type = request.strategy_type

        if strategy_type == 1:
            confidence_threshold = request.confidence_threshold or 0.7
            false_positive_threshold = request.false_positive_threshold or 0.05
            false_negative_threshold = None
        else:
            confidence_threshold = request.confidence_threshold or 0.95
            false_positive_threshold = None
            false_negative_threshold = request.false_negative_threshold or 0.10

        return StrategyConfigResponse(
            strategy_type=strategy_type,
            confidence_threshold=confidence_threshold,
            false_positive_threshold=false_positive_threshold,
            false_negative_threshold=false_negative_threshold,
            updated_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"策略配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量预测 ====================

@router.post(
    "/predict/batch",
    tags=["预测"],
    summary="批量预测"
)
async def batch_predict(
    node_type: str,
    background_tasks: BackgroundTasks
):
    """
    从数据库读取数据并批量预测

    自动读取所有需要预测的节点数据并执行预测。
    """
    try:
        service = get_prediction_service()

        # 在后台执行批量预测
        background_tasks.add_task(
            service.batch_predict_from_db,
            node_type=node_type
        )

        return {
            "status": "started",
            "message": f"批量{node_type}预测任务已启动",
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"批量预测启动失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 联邦学习 - 服务器端 ====================

@router.post(
    "/federated/client/register",
    response_model=FederatedClientRegisterResponse,
    tags=["联邦学习"],
    summary="注册联邦学习客户端"
)
async def register_federated_client(request: FederatedClientRegisterRequest):
    """
    注册联邦学习客户端（厂区）

    各厂区在参与联邦学习前需要先注册。
    """
    try:
        server = get_federated_server()

        client_info = {
            'factory_name': request.factory_name,
            'location': request.location,
            **(request.client_info or {})
        }

        server.register_client(request.client_id, client_info)

        return FederatedClientRegisterResponse(
            client_id=request.client_id,
            status="success",
            message=f"客户端 {request.client_id} 注册成功",
            registered_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"客户端注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/federated/server/status",
    response_model=FederatedServerStatusResponse,
    tags=["联邦学习"],
    summary="获取联邦学习服务器状态"
)
async def get_federated_server_status():
    """获取联邦学习服务器的整体状态"""
    try:
        server = get_federated_server()
        status = server.get_server_status()

        return FederatedServerStatusResponse(**status)

    except Exception as e:
        logger.error(f"获取服务器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/round/start",
    response_model=FederatedRoundStartResponse,
    tags=["联邦学习"],
    summary="开始联邦学习轮次"
)
async def start_federated_round(request: FederatedRoundStartRequest):
    """
    开始新的联邦学习轮次

    由中心服务器启动，指定要训练的模型和参与的客户端。
    """
    try:
        server = get_federated_server()

        round_info = server.start_round(
            model_type=request.model_type,
            node_id=request.node_id,
            expected_clients=request.expected_clients
        )

        return FederatedRoundStartResponse(
            round_id=round_info.round_id,
            model_type=round_info.model_type,
            node_id=round_info.node_id,
            status=round_info.status.value,
            expected_clients=round_info.expected_clients,
            started_at=datetime.fromtimestamp(round_info.start_time)
        )

    except Exception as e:
        logger.error(f"开始联邦学习轮次失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/federated/round/status",
    tags=["联邦学习"],
    summary="获取当前轮次状态"
)
async def get_federated_round_status():
    """获取当前进行中的联邦学习轮次状态"""
    try:
        server = get_federated_server()
        status = server.get_current_round_status()

        if status is None:
            return {"status": "no_active_round", "message": "没有进行中的轮次"}

        return status

    except Exception as e:
        logger.error(f"获取轮次状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/round/aggregate",
    response_model=FederatedRoundAggregateResponse,
    tags=["联邦学习"],
    summary="聚合并更新全局模型"
)
async def aggregate_federated_updates(request: FederatedRoundAggregateRequest):
    """
    聚合各客户端的模型更新，生成新的全局模型

    在收集到足够的客户端更新后调用此接口。
    """
    try:
        server = get_federated_server()

        aggregated = server.aggregate_updates()

        if aggregated is None:
            raise HTTPException(status_code=400, detail="聚合条件不满足或聚合失败")

        current_round = server.round_manager.round_history[-1]

        return FederatedRoundAggregateResponse(
            round_id=current_round.round_id,
            model_type=request.model_type,
            node_id=request.node_id,
            status="success",
            message=f"成功聚合 {current_round.metrics.get('num_clients', 0)} 个客户端的更新",
            num_clients_aggregated=current_round.metrics.get('num_clients', 0),
            version=server.model_manager.get_latest_version(
                request.model_type, request.node_id
            ).version,
            metrics=current_round.metrics,
            aggregated_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聚合更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/federated/model/history/{model_type}/{node_id}",
    response_model=FederatedModelHistoryResponse,
    tags=["联邦学习"],
    summary="获取全局模型历史"
)
async def get_federated_model_history(model_type: str, node_id: str):
    """
    获取全局模型的版本历史和性能指标
    """
    try:
        server = get_federated_server()
        history = server.get_model_history(model_type, node_id)

        return FederatedModelHistoryResponse(
            model_type=model_type,
            node_id=node_id,
            history=history
        )

    except Exception as e:
        logger.error(f"获取模型历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 联邦学习 - 客户端端 ====================

@router.post(
    "/federated/client/model/download",
    response_model=FederatedGlobalModelResponse,
    tags=["联邦学习"],
    summary="下载全局模型"
)
async def download_global_model(request: FederatedGlobalModelRequest):
    """
    客户端下载全局模型

    各厂区在本地训练前下载最新的全局模型。
    """
    try:
        server = get_federated_server()

        model_data = server.get_global_model_for_client(
            client_id=request.client_id,
            model_type=request.model_type,
            node_id=request.node_id
        )

        # 获取最新版本号
        latest_version = server.model_manager.get_latest_version(
            request.model_type, request.node_id
        )

        return FederatedGlobalModelResponse(
            model_type=model_data['model_type'],
            node_id=model_data['node_id'],
            round_id=model_data['round_id'],
            version=latest_version.version if latest_version else None,
            weights=model_data['weights'],
            server_time=datetime.fromtimestamp(model_data['server_time']),
            enable_two_level_arch=model_data['enable_two_level_arch'],
            metrics=latest_version.metrics if latest_version else None
        )

    except Exception as e:
        logger.error(f"下载全局模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/client/update/upload",
    response_model=FederatedUpdateUploadResponse,
    tags=["联邦学习"],
    summary="上传模型更新"
)
async def upload_model_update(request: FederatedUpdateUploadRequest):
    """
    客户端上传本地训练后的模型更新

    可以上传完整权重、梯度或权重差异。
    """
    try:
        server = get_federated_server()

        update_data = {
            'client_id': request.client_id,
            'model_type': request.model_type,
            'node_id': request.node_id,
            'round_id': request.round_id,
            'weights': request.weights,
            'num_samples': request.num_samples,
            'metrics': request.metrics or {},
            'encrypted': request.encrypted,
            'encrypted_update': request.encrypted_update
        }

        success = server.receive_client_update(update_data)

        if not success:
            raise HTTPException(status_code=400, detail="无法接收更新，请检查轮次状态")

        return FederatedUpdateUploadResponse(
            client_id=request.client_id,
            round_id=request.round_id,
            status="success",
            message="模型更新已成功接收",
            received_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传模型更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/client/model/distribute/{model_type}/{node_id}",
    tags=["联邦学习"],
    summary="分发最新全局模型"
)
async def distribute_global_model(model_type: str, node_id: str):
    """
    分发最新聚合后的全局模型给所有客户端
    """
    try:
        server = get_federated_server()

        model_data = server.distribute_model(model_type, node_id)

        return {
            "status": "success",
            "message": f"模型已准备好分发，version={model_data['version']}",
            "model_type": model_type,
            "node_id": node_id,
            "version": model_data['version'],
            "round_id": model_data['round_id'],
            "num_clients_included": model_data['num_clients'],
            "metrics": model_data['metrics'],
            "enable_two_level_arch": model_data['enable_two_level_arch'],
            "distributed_at": datetime.now()
        }

    except Exception as e:
        logger.error(f"分发模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 联邦学习 - 本地训练 ====================

@router.get(
    "/federated/client/status/{client_id}",
    response_model=FederatedClientStatusResponse,
    tags=["联邦学习"],
    summary="获取客户端状态"
)
async def get_federated_client_status(client_id: str):
    """获取指定客户端的状态"""
    try:
        client = get_federated_client(client_id)
        status = client.get_status()

        last_update = None
        if status.get('last_update_time'):
            last_update = datetime.fromtimestamp(status['last_update_time'])

        return FederatedClientStatusResponse(
            client_id=client_id,
            factory_id=status['factory_id'],
            model_type=status.get('model_type'),
            node_id=status.get('node_id'),
            current_round=status.get('current_round', 0),
            has_global_model=status.get('has_global_model', False),
            has_local_model=status.get('has_local_model', False),
            training_count=status.get('training_count', 0),
            privacy_mechanism=status.get('privacy_mechanism', 'none'),
            update_type=status.get('update_type', 'difference'),
            two_level_arch_enabled=status.get('two_level_arch_enabled', True),
            last_update_time=last_update
        )

    except Exception as e:
        logger.error(f"获取客户端状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/client/train/local",
    response_model=FederatedLocalTrainResponse,
    tags=["联邦学习"],
    summary="执行本地训练"
)
async def local_train_federated(
    request: FederatedLocalTrainRequest,
    background_tasks: BackgroundTasks
):
    """
    在客户端执行本地训练

    支持全量训练和本地微调（两层架构的第二层）。
    """
    try:
        client = get_federated_client(request.client_id)

        # 准备数据
        train_data = None
        train_labels = None
        if request.train_data:
            train_data = np.array(request.train_data)
        if request.train_labels:
            train_labels = np.array(request.train_labels)

        # 如果有自定义的本地训练轮数
        if request.local_epochs:
            client.config.local_epochs = request.local_epochs

        # 执行训练
        if request.fine_tune:
            # 本地微调（第二层）
            result = client.fine_tune(
                model_type=request.model_type,
                node_id=request.node_id,
                fine_tune_data=train_data,
                fine_tune_labels=train_labels
            )
        else:
            # 全量本地训练（第一层）
            result = client.local_train(
                model_type=request.model_type,
                node_id=request.node_id,
                train_data=train_data,
                train_labels=train_labels
            )

        return FederatedLocalTrainResponse(
            client_id=request.client_id,
            model_type=request.model_type,
            node_id=request.node_id,
            status="success",
            message=f"本地训练完成，样本数: {result.num_samples}",
            num_samples=result.num_samples,
            training_time=result.training_time,
            metrics=result.metrics
        )

    except Exception as e:
        logger.error(f"本地训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/client/update/get/{client_id}",
    tags=["联邦学习"],
    summary="获取客户端模型更新（用于上传）"
)
async def get_client_model_update(client_id: str, apply_privacy: bool = True):
    """
    获取客户端的模型更新，准备上传到服务器
    """
    try:
        client = get_federated_client(client_id)

        update = client.get_model_update(apply_privacy=apply_privacy)

        # 转换为可序列化格式
        weights_np = {k: v.cpu().numpy().tolist() for k, v in update.weights.items()}

        response = {
            "client_id": update.client_id,
            "round_id": update.round_id,
            "weights": weights_np,
            "num_samples": update.num_samples,
            "metrics": update.metrics,
            "timestamp": datetime.fromtimestamp(update.timestamp),
            "update_type": client.config.update_type.value,
            "privacy_applied": apply_privacy and client.privacy_engine is not None
        }

        if update.encrypted_update:
            import base64
            response["encrypted"] = True
            response["encrypted_update"] = base64.b64encode(update.encrypted_update).decode()

        return response

    except Exception as e:
        logger.error(f"获取模型更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 联邦学习 - 配置管理 ====================

@router.post(
    "/federated/config/privacy",
    tags=["联邦学习"],
    summary="配置隐私保护参数"
)
async def configure_privacy(
    client_id: str,
    privacy_config: FederatedPrivacyConfig
):
    """
    配置客户端的隐私保护参数

    支持差分隐私、安全聚合等机制。
    """
    try:
        client = get_federated_client(client_id)

        from app.federated.privacy import create_privacy_engine

        privacy_config_dict = {
            'mechanism': privacy_config.mechanism,
            'epsilon': privacy_config.epsilon,
            'delta': privacy_config.delta,
            'noise_scale': privacy_config.noise_scale,
            'clip_norm': privacy_config.clip_norm,
            'num_parties': privacy_config.num_parties,
            'secret_share_threshold': privacy_config.secret_share_threshold
        }

        client.privacy_engine = create_privacy_engine(privacy_config_dict)
        client.config.privacy_config = privacy_config_dict

        return {
            "status": "success",
            "message": f"隐私配置已更新，机制: {privacy_config.mechanism}",
            "client_id": client_id,
            "privacy_mechanism": privacy_config.mechanism,
            "configured_at": datetime.now()
        }

    except Exception as e:
        logger.error(f"配置隐私参数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/federated/config/aggregator",
    tags=["联邦学习"],
    summary="配置聚合器参数"
)
async def configure_aggregator(aggregator_config: FederatedAggregatorConfig):
    """
    配置服务器端的聚合器参数

    支持FedAvg、加权平均、中位数、修剪均值等聚合策略。
    """
    try:
        server = get_federated_server()

        from app.federated.aggregator import create_aggregator, AggregationStrategy

        agg_config_dict = {
            'trim_ratio': aggregator_config.trim_ratio,
            'mu': aggregator_config.mu,
            'server_learning_rate': aggregator_config.server_learning_rate,
            'min_clients_ratio': aggregator_config.min_clients_per_round / max(1, len(server.registered_clients)),
            'enable_outlier_detection': aggregator_config.enable_outlier_detection
        }

        server.aggregator = create_aggregator(
            strategy=AggregationStrategy(aggregator_config.strategy),
            config=agg_config_dict
        )

        server.config.aggregation_strategy = AggregationStrategy(aggregator_config.strategy)
        server.config.aggregation_config = agg_config_dict
        server.config.min_clients_per_round = aggregator_config.min_clients_per_round

        return {
            "status": "success",
            "message": f"聚合器配置已更新，策略: {aggregator_config.strategy}",
            "strategy": aggregator_config.strategy,
            "configured_at": datetime.now()
        }

    except Exception as e:
        logger.error(f"配置聚合器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 辅助函数 ====================

def _alert_to_dict(alert) -> Dict[str, Any]:
    """将告警 ORM 对象转为响应字典"""
    data = {
        'id': alert.id,
        'alert_no': alert.alert_no,
        'rule_id': alert.rule_id,
        'alert_level': alert.alert_level,
        'original_level': alert.original_level,
        'node_type': alert.node_type,
        'node_id': alert.node_id,
        'title': alert.title,
        'content': alert.content,
        'confidence': alert.confidence,
        'risk_score': alert.risk_score,
        'status': alert.status,
        'handler_id': alert.handler_id,
        'handler_name': alert.handler_name,
        'handle_time': alert.handle_time,
        'handle_note': alert.handle_note,
        'is_upgraded': bool(alert.is_upgraded),
        'upgrade_count': alert.upgrade_count or 0,
        'last_upgrade_time': alert.last_upgrade_time,
        'work_order_id': alert.work_order_id,
        'source_prediction_id': alert.source_prediction_id,
        'silence_until': alert.silence_until,
        'create_time': alert.create_time,
        'update_time': alert.update_time,
    }
    if alert.recommendations:
        try:
            data['recommendations'] = json.loads(alert.recommendations)
        except Exception:
            data['recommendations'] = []
    else:
        data['recommendations'] = []
    return data


def _rule_to_dict(rule) -> Dict[str, Any]:
    """将告警规则 ORM 对象转为响应字典"""
    data = {
        'id': rule.id,
        'rule_name': rule.rule_name,
        'alert_level': rule.alert_level,
        'node_type': rule.node_type,
        'min_confidence': rule.min_confidence,
        'silence_period': rule.silence_period,
        'enable_upgrade': bool(rule.enable_upgrade),
        'upgrade_minutes': rule.upgrade_minutes,
        'upgrade_to_level': rule.upgrade_to_level,
        'enabled': bool(rule.enabled),
        'description': rule.description,
        'create_time': rule.create_time,
        'update_time': rule.update_time,
    }
    if rule.node_ids:
        try:
            data['node_ids'] = json.loads(rule.node_ids)
        except Exception:
            data['node_ids'] = []
    else:
        data['node_ids'] = []
    return data


def _subscription_to_dict(sub) -> Dict[str, Any]:
    """将订阅 ORM 对象转为响应字典"""
    data = {
        'id': sub.id,
        'subscriber_type': sub.subscriber_type,
        'subscriber_id': sub.subscriber_id,
        'subscriber_name': sub.subscriber_name,
        'min_alert_level': sub.min_alert_level,
        'node_type': sub.node_type,
        'enabled': bool(sub.enabled),
        'create_time': sub.create_time,
        'update_time': sub.update_time,
    }
    for field, attr in [
        ('alert_levels', sub.alert_levels),
        ('node_ids', sub.node_ids),
        ('notify_channels', sub.notify_channels),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except Exception:
                data[field] = []
        else:
            data[field] = []
    if sub.notify_targets:
        try:
            data['notify_targets'] = json.loads(sub.notify_targets)
        except Exception:
            data['notify_targets'] = {}
    else:
        data['notify_targets'] = {}
    return data


def _channel_to_dict(ch) -> Dict[str, Any]:
    """将通知渠道 ORM 对象转为响应字典"""
    data = {
        'id': ch.id,
        'channel_type': ch.channel_type,
        'channel_name': ch.channel_name,
        'enabled': bool(ch.enabled),
        'is_default': bool(ch.is_default),
        'create_time': ch.create_time,
        'update_time': ch.update_time,
    }
    if ch.config:
        try:
            data['config'] = json.loads(ch.config)
        except Exception:
            data['config'] = {}
    else:
        data['config'] = {}
    return data


def _work_order_to_dict(wo) -> Dict[str, Any]:
    """将工单 ORM 对象转为响应字典"""
    data = {
        'id': wo.id,
        'order_no': wo.order_no,
        'alert_id': wo.alert_id,
        'title': wo.title,
        'description': wo.description,
        'priority': wo.priority,
        'status': wo.status,
        'node_type': wo.node_type,
        'node_id': wo.node_id,
        'alert_level': wo.alert_level,
        'risk_score': wo.risk_score,
        'assignee_id': wo.assignee_id,
        'assignee_name': wo.assignee_name,
        'creator_id': wo.creator_id,
        'creator_name': wo.creator_name,
        'due_time': wo.due_time,
        'resolve_time': wo.resolve_time,
        'resolve_note': wo.resolve_note,
        'create_time': wo.create_time,
        'update_time': wo.update_time,
    }
    if wo.recommendations:
        try:
            data['recommendations'] = json.loads(wo.recommendations)
        except Exception:
            data['recommendations'] = []
    else:
        data['recommendations'] = []
    if wo.extra_info:
        try:
            data['extra_info'] = json.loads(wo.extra_info)
        except Exception:
            data['extra_info'] = {}
    else:
        data['extra_info'] = {}
    return data


# ==================== 告警规则管理 ====================

@router.get(
    "/alert/rules",
    response_model=List[AlertRuleResponse],
    tags=["告警管理"],
    summary="查询告警规则列表"
)
async def list_alert_rules(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    alert_level: Optional[int] = Query(None, ge=1, le=4, description="告警级别"),
):
    """查询告警规则列表"""
    try:
        from app.services.alert import AlertService
        service = AlertService()
        rules = service.list_rules(enabled=enabled, alert_level=alert_level)
        return [_rule_to_dict(r) for r in rules]
    except Exception as e:
        logger.error(f"查询告警规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alert/rules",
    response_model=AlertRuleResponse,
    tags=["告警管理"],
    summary="创建告警规则"
)
async def create_alert_rule(request: AlertRuleCreate):
    """创建告警规则"""
    try:
        from app.services.alert import AlertService
        service = AlertService()
        data = request.model_dump()
        if 'node_ids' in data and data['node_ids']:
            data['node_ids'] = json.dumps(data['node_ids'], ensure_ascii=False)
        rule = service.create_rule(**data)
        if not rule:
            raise HTTPException(status_code=500, detail="创建规则失败")
        return _rule_to_dict(rule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建告警规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/alert/rules/{rule_id}",
    response_model=AlertRuleResponse,
    tags=["告警管理"],
    summary="更新告警规则"
)
async def update_alert_rule(rule_id: int, request: AlertRuleUpdate):
    """更新告警规则"""
    try:
        from app.services.alert import AlertService
        service = AlertService()
        data = request.model_dump(exclude_unset=True)
        if 'node_ids' in data and data['node_ids']:
            data['node_ids'] = json.dumps(data['node_ids'], ensure_ascii=False)
        rule = service.update_rule(rule_id, **data)
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        return _rule_to_dict(rule)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/alert/rules/{rule_id}",
    tags=["告警管理"],
    summary="删除告警规则"
)
async def delete_alert_rule(rule_id: int):
    """删除告警规则"""
    try:
        from app.services.alert import AlertService
        service = AlertService()
        ok = service.delete_rule(rule_id)
        if not ok:
            raise HTTPException(status_code=404, detail="规则不存在")
        return {"status": "success", "message": "规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 告警事件管理 ====================

@router.get(
    "/alert/events",
    response_model=AlertListResponse,
    tags=["告警管理"],
    summary="查询告警事件列表"
)
async def list_alert_events(
    status: Optional[str] = Query(None, description="状态 pending/processing/resolved/ignored"),
    alert_level: Optional[int] = Query(None, ge=1, le=4, description="告警级别"),
    node_type: Optional[str] = Query(None, description="节点类型 bolt/flange"),
    node_id: Optional[str] = Query(None, description="节点ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询告警事件列表"""
    try:
        from app.services.alert import AlertService
        service = AlertService()
        alerts = service.list_alerts(
            status=status, alert_level=alert_level,
            node_type=node_type, node_id=node_id,
            limit=limit, offset=offset,
        )
        items = [_alert_to_dict(a) for a in alerts]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询告警事件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/alert/events/{alert_id}",
    response_model=AlertEventResponse,
    tags=["告警管理"],
    summary="获取告警详情"
)
async def get_alert_event(alert_id: int):
    """获取单条告警详情"""
    try:
        from app.services.alert import AlertService
        service = AlertService()
        alert = service.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="告警不存在")
        return _alert_to_dict(alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取告警详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alert/events/{alert_id}/handle",
    response_model=AlertEventResponse,
    tags=["告警管理"],
    summary="处理告警"
)
async def handle_alert_event(alert_id: int, request: AlertHandleRequest):
    """
    处理告警

    action:
    - acknowledge: 确认（状态变为 processing）
    - resolve: 解决（状态变为 resolved）
    - ignore: 忽略（状态变为 ignored，可选静默期）
    """
    try:
        from app.services.alert import AlertService
        service = AlertService()
        alert = service.handle_alert(
            alert_id=alert_id,
            action=request.action,
            handler_id=request.handler_id,
            handler_name=request.handler_name,
            handle_note=request.handle_note,
            silence_minutes=request.silence_minutes,
        )
        if not alert:
            raise HTTPException(status_code=404, detail="告警不存在")
        return _alert_to_dict(alert)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alert/upgrade/trigger",
    response_model=AlertUpgradeTriggerResponse,
    tags=["告警管理"],
    summary="手动触发告警升级检查"
)
async def trigger_alert_upgrade():
    """
    手动触发告警升级检查

    扫描所有待处理告警，对超时未处理的告警执行自动升级。
    调度器默认每5分钟执行一次。
    """
    try:
        from app.services.alert import AlertService
        service = AlertService()
        count = service.process_pending_upgrades()
        return {
            "upgraded_count": count,
            "message": f"已处理 {count} 条告警升级",
        }
    except Exception as e:
        logger.error(f"手动触发告警升级失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 告警订阅管理 ====================

@router.get(
    "/alert/subscriptions",
    response_model=List[AlertSubscriptionResponse],
    tags=["告警订阅"],
    summary="查询订阅列表"
)
async def list_alert_subscriptions(
    subscriber_type: Optional[str] = Query(None, description="订阅者类型 role/user/device"),
    subscriber_id: Optional[str] = Query(None, description="订阅者ID"),
    enabled: Optional[bool] = Query(None, description="是否启用"),
):
    """查询告警订阅列表"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        subs = service.list_subscriptions(
            subscriber_type=subscriber_type,
            subscriber_id=subscriber_id,
            enabled=enabled,
        )
        return [_subscription_to_dict(s) for s in subs]
    except Exception as e:
        logger.error(f"查询订阅列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/alert/subscriptions/{sub_id}",
    response_model=AlertSubscriptionResponse,
    tags=["告警订阅"],
    summary="获取订阅详情"
)
async def get_alert_subscription(sub_id: int):
    """获取单个订阅详情"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        sub = service.get_subscription(sub_id)
        if not sub:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return _subscription_to_dict(sub)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订阅详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alert/subscriptions",
    response_model=AlertSubscriptionResponse,
    tags=["告警订阅"],
    summary="创建订阅"
)
async def create_alert_subscription(request: AlertSubscriptionCreate):
    """创建告警订阅"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        data = request.model_dump()
        sub = service.create_subscription(**data)
        if not sub:
            raise HTTPException(status_code=500, detail="创建订阅失败")
        return _subscription_to_dict(sub)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/alert/subscriptions/{sub_id}",
    response_model=AlertSubscriptionResponse,
    tags=["告警订阅"],
    summary="更新订阅"
)
async def update_alert_subscription(sub_id: int, request: AlertSubscriptionUpdate):
    """更新告警订阅"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        data = request.model_dump(exclude_unset=True)
        sub = service.update_subscription(sub_id, **data)
        if not sub:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return _subscription_to_dict(sub)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/alert/subscriptions/{sub_id}",
    tags=["告警订阅"],
    summary="删除订阅"
)
async def delete_alert_subscription(sub_id: int):
    """删除告警订阅"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        ok = service.delete_subscription(sub_id)
        if not ok:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return {"status": "success", "message": "订阅已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 通知渠道管理 ====================

@router.get(
    "/notification/channels",
    response_model=List[NotificationChannelResponse],
    tags=["通知渠道"],
    summary="查询通知渠道列表"
)
async def list_notification_channels():
    """查询所有通知渠道"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        channels = service.list_channels()
        return [_channel_to_dict(c) for c in channels]
    except Exception as e:
        logger.error(f"查询通知渠道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notification/channels",
    response_model=NotificationChannelResponse,
    tags=["通知渠道"],
    summary="创建通知渠道"
)
async def create_notification_channel(request: NotificationChannelCreate):
    """创建通知渠道"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        data = request.model_dump()
        ch = service.create_channel(**data)
        if not ch:
            raise HTTPException(status_code=500, detail="创建渠道失败")
        return _channel_to_dict(ch)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建通知渠道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/notification/channels/{channel_id}",
    response_model=NotificationChannelResponse,
    tags=["通知渠道"],
    summary="更新通知渠道"
)
async def update_notification_channel(
    channel_id: int,
    request: NotificationChannelUpdate,
):
    """更新通知渠道"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        data = request.model_dump(exclude_unset=True)
        ch = service.update_channel(channel_id, **data)
        if not ch:
            raise HTTPException(status_code=404, detail="渠道不存在")
        return _channel_to_dict(ch)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新通知渠道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/notification/channels/{channel_id}",
    tags=["通知渠道"],
    summary="删除通知渠道"
)
async def delete_notification_channel(channel_id: int):
    """删除通知渠道"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        ok = service.delete_channel(channel_id)
        if not ok:
            raise HTTPException(status_code=404, detail="渠道不存在")
        return {"status": "success", "message": "渠道已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除通知渠道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/notification/logs",
    response_model=List[NotificationLogResponse],
    tags=["通知渠道"],
    summary="查询通知发送日志"
)
async def list_notification_logs(
    alert_id: Optional[int] = Query(None, description="关联告警ID"),
    status: Optional[str] = Query(None, description="发送状态 success/failed/pending"),
    limit: int = Query(100, ge=1, le=1000),
):
    """查询通知发送日志"""
    try:
        from app.services.alert import NotificationService
        service = NotificationService()
        logs = service.list_notification_logs(
            alert_id=alert_id, status=status, limit=limit,
        )
        return [
            {
                'id': log.id,
                'alert_id': log.alert_id,
                'channel_type': log.channel_type,
                'subscriber_id': log.subscriber_id,
                'subscriber_name': log.subscriber_name,
                'target': log.target,
                'title': log.title,
                'content': log.content,
                'status': log.status,
                'error_message': log.error_message,
                'retry_count': log.retry_count or 0,
                'send_time': log.send_time,
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"查询通知日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 工单管理 ====================

@router.get(
    "/work-orders",
    response_model=WorkOrderListResponse,
    tags=["工单管理"],
    summary="查询工单列表"
)
async def list_work_orders(
    status: Optional[str] = Query(None, description="状态 open/assigned/in_progress/resolved/closed"),
    priority: Optional[str] = Query(None, description="优先级 low/medium/high/urgent"),
    assignee_id: Optional[str] = Query(None, description="处理人ID"),
    alert_id: Optional[int] = Query(None, description="关联告警ID"),
    node_type: Optional[str] = Query(None, description="节点类型"),
    node_id: Optional[str] = Query(None, description="节点ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询工单列表"""
    try:
        from app.services.alert import WorkOrderService
        service = WorkOrderService()
        wos = service.list_work_orders(
            status=status, priority=priority, assignee_id=assignee_id,
            alert_id=alert_id, node_type=node_type, node_id=node_id,
            limit=limit, offset=offset,
        )
        items = [_work_order_to_dict(w) for w in wos]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询工单列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/work-orders/{work_order_id}",
    response_model=WorkOrderResponse,
    tags=["工单管理"],
    summary="获取工单详情"
)
async def get_work_order(work_order_id: int):
    """获取工单详情"""
    try:
        from app.services.alert import WorkOrderService
        service = WorkOrderService()
        wo = service.get_work_order(work_order_id)
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return _work_order_to_dict(wo)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工单详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders",
    response_model=WorkOrderResponse,
    tags=["工单管理"],
    summary="手动创建工单"
)
async def create_work_order(request: WorkOrderCreate):
    """手动创建工单"""
    try:
        from app.services.alert import WorkOrderService
        service = WorkOrderService()
        data = request.model_dump()
        due_hours = data.pop('due_hours', 48)
        wo = service.create_manual_work_order(
            due_hours=due_hours, **data
        )
        if not wo:
            raise HTTPException(status_code=500, detail="创建工单失败")
        return _work_order_to_dict(wo)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建工单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/work-orders/{work_order_id}",
    response_model=WorkOrderResponse,
    tags=["工单管理"],
    summary="更新工单信息"
)
async def update_work_order(work_order_id: int, request: WorkOrderUpdate):
    """更新工单信息"""
    try:
        from app.services.alert import WorkOrderService
        from app.utils.database import get_db, WorkOrder
        data = request.model_dump(exclude_unset=True)
        if 'recommendations' in data and data['recommendations']:
            data['recommendations'] = json.dumps(
                data['recommendations'], ensure_ascii=False
            )
        if 'extra_info' in data and data['extra_info']:
            data['extra_info'] = json.dumps(
                data['extra_info'], ensure_ascii=False
            )

        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=500, detail="数据库不可用")
            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
            if not wo:
                raise HTTPException(status_code=404, detail="工单不存在")
            for k, v in data.items():
                if hasattr(wo, k):
                    setattr(wo, k, v)
            db.commit()
            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
        return _work_order_to_dict(wo)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders/{work_order_id}/assign",
    response_model=WorkOrderResponse,
    tags=["工单管理"],
    summary="指派工单"
)
async def assign_work_order(work_order_id: int, request: WorkOrderAssignRequest):
    """指派工单处理人"""
    try:
        from app.services.alert import WorkOrderService
        service = WorkOrderService()
        wo = service.assign_work_order(
            work_order_id=work_order_id,
            assignee_id=request.assignee_id,
            assignee_name=request.assignee_name,
            assigner_id=request.assigner_id,
            assigner_name=request.assigner_name,
        )
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return _work_order_to_dict(wo)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"指派工单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders/{work_order_id}/status",
    response_model=WorkOrderResponse,
    tags=["工单管理"],
    summary="更新工单状态"
)
async def update_work_order_status(
    work_order_id: int,
    request: WorkOrderStatusUpdateRequest,
):
    """更新工单状态"""
    try:
        from app.services.alert import WorkOrderService
        service = WorkOrderService()
        wo = service.update_work_order_status(
            work_order_id=work_order_id,
            status=request.status,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
            note=request.note,
        )
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return _work_order_to_dict(wo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新工单状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders/{work_order_id}/resolve",
    response_model=WorkOrderResponse,
    tags=["工单管理"],
    summary="解决工单"
)
async def resolve_work_order(work_order_id: int, request: WorkOrderResolveRequest):
    """解决工单（便捷接口）"""
    try:
        from app.services.alert import WorkOrderService
        service = WorkOrderService()
        wo = service.resolve_work_order(
            work_order_id=work_order_id,
            resolve_note=request.resolve_note,
            resolver_id=request.resolver_id,
            resolver_name=request.resolver_name,
        )
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return _work_order_to_dict(wo)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决工单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 工单处置记录 ====================

@router.get(
    "/work-orders/{work_order_id}/disposals",
    response_model=DisposalRecordListResponse,
    tags=["工单管理"],
    summary="查询工单处置记录列表"
)
async def list_work_order_disposals(
    work_order_id: int,
    disposal_type: Optional[str] = Query(None, description="处置类型"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询工单处置记录列表"""
    try:
        from app.services.alert.disposal_service import DisposalService
        service = DisposalService()
        records, total = service.list_disposal_records(
            work_order_id=work_order_id,
            disposal_type=disposal_type,
            limit=limit,
            offset=offset,
        )
        return {
            'total': total,
            'items': [_disposal_to_dict(r) for r in records],
        }
    except Exception as e:
        logger.error(f"查询处置记录列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders/disposals",
    response_model=DisposalRecordResponse,
    tags=["工单管理"],
    summary="创建处置记录"
)
async def create_disposal_record(request: DisposalRecordCreate):
    """创建工单处置记录"""
    try:
        from app.services.alert.disposal_service import DisposalService
        service = DisposalService()
        record = service.create_disposal_record(
            work_order_id=request.work_order_id,
            disposal_type=request.disposal_type,
            disposal_content=request.disposal_content,
            disposal_time=request.disposal_time,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
            before_value=request.before_value,
            after_value=request.after_value,
            materials_used=request.materials_used,
            photos=request.photos,
            notes=request.notes,
            extra_info=request.extra_info,
        )
        if not record:
            raise HTTPException(status_code=404, detail="工单不存在或创建失败")
        return _disposal_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建处置记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/work-orders/disposals/{record_id}",
    response_model=DisposalRecordResponse,
    tags=["工单管理"],
    summary="获取处置记录详情"
)
async def get_disposal_record(record_id: int):
    """获取处置记录详情"""
    try:
        from app.services.alert.disposal_service import DisposalService
        service = DisposalService()
        record = service.get_disposal_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="处置记录不存在")
        return _disposal_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取处置记录详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/work-orders/disposals/{record_id}",
    response_model=DisposalRecordResponse,
    tags=["工单管理"],
    summary="更新处置记录"
)
async def update_disposal_record(record_id: int, request: DisposalRecordUpdate):
    """更新处置记录"""
    try:
        from app.services.alert.disposal_service import DisposalService
        service = DisposalService()
        update_data = request.model_dump(exclude_unset=True)
        record = service.update_disposal_record(record_id, **update_data)
        if not record:
            raise HTTPException(status_code=404, detail="处置记录不存在")
        return _disposal_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新处置记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/work-orders/disposals/{record_id}",
    tags=["工单管理"],
    summary="删除处置记录"
)
async def delete_disposal_record(record_id: int):
    """删除处置记录"""
    try:
        from app.services.alert.disposal_service import DisposalService
        service = DisposalService()
        success = service.delete_disposal_record(record_id)
        if not success:
            raise HTTPException(status_code=404, detail="处置记录不存在")
        return {'success': True, 'message': '删除成功'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除处置记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 工单复测数据 ====================

@router.get(
    "/work-orders/{work_order_id}/retests",
    response_model=RetestRecordListResponse,
    tags=["工单管理"],
    summary="查询工单复测记录列表"
)
async def list_work_order_retests(
    work_order_id: int,
    retest_result: Optional[str] = Query(None, description="复测结果 pass/fail/pending"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询工单复测记录列表"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        records, total = service.list_retest_records(
            work_order_id=work_order_id,
            retest_result=retest_result,
            limit=limit,
            offset=offset,
        )
        return {
            'total': total,
            'items': [_retest_to_dict(r) for r in records],
        }
    except Exception as e:
        logger.error(f"查询复测记录列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders/retests",
    response_model=RetestRecordResponse,
    tags=["工单管理"],
    summary="创建复测记录"
)
async def create_retest_record(request: RetestRecordCreate):
    """创建工单复测记录，支持自动再预测"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        record = service.create_retest_record(
            work_order_id=request.work_order_id,
            retest_time=request.retest_time,
            retester_id=request.retester_id,
            retester_name=request.retester_name,
            retest_result=request.retest_result,
            measured_value=request.measured_value,
            data_points=request.data_points,
            before_risk_score=request.before_risk_score,
            after_risk_score=request.after_risk_score,
            status_after_retest=request.status_after_retest,
            confidence=request.confidence,
            retest_notes=request.retest_notes,
            photos=request.photos,
            extra_info=request.extra_info,
            auto_repredict=request.auto_repredict,
        )
        if not record:
            raise HTTPException(status_code=404, detail="工单不存在或创建失败")
        return _retest_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建复测记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/work-orders/retests/{record_id}",
    response_model=RetestRecordResponse,
    tags=["工单管理"],
    summary="获取复测记录详情"
)
async def get_retest_record(record_id: int):
    """获取复测记录详情"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        record = service.get_retest_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="复测记录不存在")
        return _retest_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取复测记录详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/work-orders/retests/{record_id}",
    response_model=RetestRecordResponse,
    tags=["工单管理"],
    summary="更新复测记录"
)
async def update_retest_record(record_id: int, request: RetestRecordUpdate):
    """更新复测记录"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        update_data = request.model_dump(exclude_unset=True)
        record = service.update_retest_record(record_id, **update_data)
        if not record:
            raise HTTPException(status_code=404, detail="复测记录不存在")
        return _retest_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新复测记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/work-orders/retests/{record_id}/repredict",
    response_model=PredictionCompareResponse,
    tags=["工单管理"],
    summary="触发复测后再预测"
)
async def trigger_retest_repredict(record_id: int):
    """手动触发复测后再预测及对比"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        compare = service.repredict_and_compare(record_id)
        if not compare:
            raise HTTPException(status_code=404, detail="复测记录不存在或再预测失败")
        return _prediction_compare_to_dict(compare)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发复测再预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/work-orders/{work_order_id}/prediction-compares",
    response_model=PredictionCompareListResponse,
    tags=["工单管理"],
    summary="查询工单预测对比列表"
)
async def list_work_order_prediction_compares(
    work_order_id: int,
    is_false_positive: Optional[bool] = Query(None, description="是否误报"),
    is_recurring: Optional[bool] = Query(None, description="是否重复故障"),
    risk_change: Optional[str] = Query(None, description="风险变化 improved/stable/worsened"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询工单预测对比列表"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        records, total = service.list_prediction_compares(
            work_order_id=work_order_id,
            is_false_positive=is_false_positive,
            is_recurring=is_recurring,
            risk_change=risk_change,
            limit=limit,
            offset=offset,
        )
        return {
            'total': total,
            'items': [_prediction_compare_to_dict(r) for r in records],
        }
    except Exception as e:
        logger.error(f"查询预测对比列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/work-orders/prediction-compares/{compare_id}",
    response_model=PredictionCompareResponse,
    tags=["工单管理"],
    summary="获取预测对比详情"
)
async def get_prediction_compare(compare_id: int):
    """获取预测对比详情"""
    try:
        from app.services.alert.retest_service import RetestService
        service = RetestService()
        record = service.get_prediction_compare(compare_id)
        if not record:
            raise HTTPException(status_code=404, detail="预测对比不存在")
        return _prediction_compare_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取预测对比详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 工单统计指标 ====================

@router.get(
    "/work-orders/stats/summary",
    response_model=WorkOrderStatsResponse,
    tags=["工单统计"],
    summary="工单统计指标概览"
)
async def get_work_order_stats(
    start_time: Optional[datetime] = Query(None, description="统计开始时间"),
    end_time: Optional[datetime] = Query(None, description="统计结束时间"),
    node_type: Optional[str] = Query(None, description="节点类型 bolt/flange"),
    priority: Optional[str] = Query(None, description="优先级"),
):
    """获取工单统计指标：MTTR、误报率、重复故障率等"""
    try:
        from app.services.alert.work_order_stats_service import WorkOrderStatsService
        service = WorkOrderStatsService()
        stats = service.calculate_stats(
            start_time=start_time,
            end_time=end_time,
            node_type=node_type,
            priority=priority,
        )
        return stats
    except Exception as e:
        logger.error(f"获取工单统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/work-orders/stats/mttr-trend",
    response_model=MttrTrendResponse,
    tags=["工单统计"],
    summary="MTTR趋势"
)
async def get_mttr_trend(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    node_type: Optional[str] = Query(None, description="节点类型 bolt/flange"),
    priority: Optional[str] = Query(None, description="优先级"),
):
    """获取 MTTR 趋势数据"""
    try:
        from app.services.alert.work_order_stats_service import WorkOrderStatsService
        service = WorkOrderStatsService()
        trend_data = service.get_mttr_trend(
            days=days,
            node_type=node_type,
            priority=priority,
        )
        return trend_data
    except Exception as e:
        logger.error(f"获取MTTR趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CMMS/EAM 集成 ====================

@router.get(
    "/cmms/configs",
    response_model=CmmsConfigListResponse,
    tags=["CMMS集成"],
    summary="查询CMMS配置列表"
)
async def list_cmms_configs(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    system_type: Optional[str] = Query(None, description="系统类型"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询 CMMS/EAM 集成配置列表"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        configs, total = service.list_configs(
            enabled=enabled,
            system_type=system_type,
            limit=limit,
            offset=offset,
        )
        return {
            'total': total,
            'items': [_cmms_config_to_dict(c) for c in configs],
        }
    except Exception as e:
        logger.error(f"查询CMMS配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cmms/configs",
    response_model=CmmsConfigResponse,
    tags=["CMMS集成"],
    summary="创建CMMS配置"
)
async def create_cmms_config(request: CmmsConfigCreate):
    """创建 CMMS/EAM 集成配置"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        config = service.create_config(
            system_name=request.system_name,
            system_type=request.system_type,
            base_url=request.base_url,
            auth_type=request.auth_type,
            auth_config=request.auth_config,
            work_order_sync=request.work_order_sync,
            work_order_webhook_url=request.work_order_webhook_url,
            work_order_push_url=request.work_order_push_url,
            status_mapping=request.status_mapping,
            priority_mapping=request.priority_mapping,
            field_mapping=request.field_mapping,
            enabled=request.enabled,
            sync_direction=request.sync_direction,
            sync_interval=request.sync_interval,
            tenant_id=request.tenant_id,
            extra_info=request.extra_info,
        )
        if not config:
            raise HTTPException(status_code=500, detail="创建CMMS配置失败")
        return _cmms_config_to_dict(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建CMMS配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cmms/configs/{config_id}",
    response_model=CmmsConfigResponse,
    tags=["CMMS集成"],
    summary="获取CMMS配置详情"
)
async def get_cmms_config(config_id: int):
    """获取 CMMS 配置详情"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        config = service.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="CMMS配置不存在")
        return _cmms_config_to_dict(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取CMMS配置详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/cmms/configs/{config_id}",
    response_model=CmmsConfigResponse,
    tags=["CMMS集成"],
    summary="更新CMMS配置"
)
async def update_cmms_config(config_id: int, request: CmmsConfigUpdate):
    """更新 CMMS 配置"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        update_data = request.model_dump(exclude_unset=True)
        config = service.update_config(config_id, **update_data)
        if not config:
            raise HTTPException(status_code=404, detail="CMMS配置不存在")
        return _cmms_config_to_dict(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新CMMS配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/cmms/configs/{config_id}",
    tags=["CMMS集成"],
    summary="删除CMMS配置"
)
async def delete_cmms_config(config_id: int):
    """删除 CMMS 配置"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        success = service.delete_config(config_id)
        if not success:
            raise HTTPException(status_code=404, detail="CMMS配置不存在")
        return {'success': True, 'message': '删除成功'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除CMMS配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cmms/sync/work-order",
    response_model=CmmsSyncResponse,
    tags=["CMMS集成"],
    summary="同步工单到CMMS"
)
async def sync_work_order_to_cmms(request: CmmsSyncRequest):
    """手动同步工单到 CMMS/EAM 系统"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        success, log_id, external_id, error = service.sync_work_order(
            work_order_id=request.work_order_id,
            config_id=request.config_id,
            sync_type=request.sync_type,
        )
        return {
            'success': success,
            'sync_log_id': log_id,
            'external_id': external_id,
            'message': error or ('同步成功' if success else '同步失败'),
        }
    except Exception as e:
        logger.error(f"同步工单到CMMS失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cmms/webhook/{config_id}",
    response_model=CmmsWebhookResponse,
    tags=["CMMS集成"],
    summary="CMMS Webhook回调"
)
async def cmms_webhook_callback(
    config_id: int,
    request: Dict[str, Any],
    x_signature: Optional[str] = Query(None, alias="X-Signature", description="Webhook签名"),
):
    """接收 CMMS 系统的 Webhook 回调"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        success, processed_count, message = service.handle_webhook(
            config_id=config_id,
            payload=request,
            signature=x_signature,
        )
        return {
            'success': success,
            'message': message,
            'processed_count': processed_count,
        }
    except Exception as e:
        logger.error(f"处理CMMS Webhook失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cmms/sync-logs",
    response_model=CmmsSyncLogListResponse,
    tags=["CMMS集成"],
    summary="查询CMMS同步日志"
)
async def list_cmms_sync_logs(
    config_id: Optional[int] = Query(None, description="CMMS配置ID"),
    work_order_id: Optional[int] = Query(None, description="工单ID"),
    status: Optional[str] = Query(None, description="同步状态 success/failed/pending"),
    sync_direction: Optional[str] = Query(None, description="同步方向 push/pull"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询 CMMS 同步日志"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        logs, total = service.list_sync_logs(
            config_id=config_id,
            work_order_id=work_order_id,
            status=status,
            sync_direction=sync_direction,
            limit=limit,
            offset=offset,
        )
        return {
            'total': total,
            'items': [_cmms_sync_log_to_dict(l) for l in logs],
        }
    except Exception as e:
        logger.error(f"查询CMMS同步日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cmms/sync-logs/{log_id}/retry",
    response_model=CmmsSyncResponse,
    tags=["CMMS集成"],
    summary="重试CMMS同步"
)
async def retry_cmms_sync(log_id: int):
    """重试失败的 CMMS 同步"""
    try:
        from app.services.alert.cmms_service import CmmsService
        service = CmmsService()
        success, external_id, error = service.retry_sync(log_id)
        return {
            'success': success,
            'external_id': external_id,
            'message': error or ('重试成功' if success else '重试失败'),
        }
    except Exception as e:
        logger.error(f"重试CMMS同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 辅助函数: 工单闭环 ====================

def _disposal_to_dict(record) -> Dict[str, Any]:
    """将处置记录ORM对象转为响应字典"""
    data = {
        'id': record.id,
        'work_order_id': record.work_order_id,
        'disposal_type': record.disposal_type,
        'disposal_content': record.disposal_content,
        'disposal_time': record.disposal_time,
        'operator_id': record.operator_id,
        'operator_name': record.operator_name,
        'before_value': record.before_value,
        'after_value': record.after_value,
        'notes': record.notes,
        'create_time': record.create_time,
    }
    for field, attr in [
        ('materials_used', record.materials_used),
        ('photos', record.photos),
        ('extra_info', record.extra_info),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except (json.JSONDecodeError, TypeError):
                data[field] = attr
        else:
            data[field] = None
    return data


def _retest_to_dict(record) -> Dict[str, Any]:
    """将复测记录ORM对象转为响应字典"""
    data = {
        'id': record.id,
        'work_order_id': record.work_order_id,
        'retest_time': record.retest_time,
        'retester_id': record.retester_id,
        'retester_name': record.retester_name,
        'retest_result': record.retest_result,
        'measured_value': record.measured_value,
        'before_risk_score': record.before_risk_score,
        'after_risk_score': record.after_risk_score,
        'status_after_retest': record.status_after_retest,
        'confidence': record.confidence,
        'retest_notes': record.retest_notes,
        'create_time': record.create_time,
    }
    for field, attr in [
        ('data_points', record.data_points),
        ('photos', record.photos),
        ('extra_info', record.extra_info),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except (json.JSONDecodeError, TypeError):
                data[field] = attr
        else:
            data[field] = None
    return data


def _prediction_compare_to_dict(record) -> Dict[str, Any]:
    """将预测对比ORM对象转为响应字典"""
    data = {
        'id': record.id,
        'work_order_id': record.work_order_id,
        'retest_id': record.retest_id,
        'original_prediction_id': record.original_prediction_id,
        'retest_prediction_id': record.retest_prediction_id,
        'original_status': record.original_status,
        'retest_status': record.retest_status,
        'original_risk_score': record.original_risk_score,
        'retest_risk_score': record.retest_risk_score,
        'original_confidence': record.original_confidence,
        'retest_confidence': record.retest_confidence,
        'risk_change': record.risk_change,
        'risk_delta': record.risk_delta,
        'status_match': record.status_match,
        'is_false_positive': record.is_false_positive,
        'is_recurring': record.is_recurring,
        'create_time': record.create_time,
    }
    if record.comparison_detail:
        try:
            data['comparison_detail'] = json.loads(record.comparison_detail)
        except (json.JSONDecodeError, TypeError):
            data['comparison_detail'] = record.comparison_detail
    else:
        data['comparison_detail'] = None
    return data


def _cmms_config_to_dict(config) -> Dict[str, Any]:
    """将CMMS配置ORM对象转为响应字典"""
    data = {
        'id': config.id,
        'system_name': config.system_name,
        'system_type': config.system_type,
        'base_url': config.base_url,
        'auth_type': config.auth_type,
        'work_order_sync': config.work_order_sync,
        'work_order_webhook_url': config.work_order_webhook_url,
        'work_order_push_url': config.work_order_push_url,
        'enabled': config.enabled,
        'sync_direction': config.sync_direction,
        'last_sync_time': config.last_sync_time,
        'sync_interval': config.sync_interval,
        'tenant_id': config.tenant_id,
        'create_time': config.create_time,
        'update_time': config.update_time,
    }
    for field, attr in [
        ('status_mapping', config.status_mapping),
        ('priority_mapping', config.priority_mapping),
        ('field_mapping', config.field_mapping),
        ('extra_info', config.extra_info),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except (json.JSONDecodeError, TypeError):
                data[field] = attr
        else:
            data[field] = None
    return data


def _cmms_sync_log_to_dict(log) -> Dict[str, Any]:
    """将CMMS同步日志ORM对象转为响应字典"""
    return {
        'id': log.id,
        'config_id': log.config_id,
        'sync_type': log.sync_type,
        'sync_direction': log.sync_direction,
        'work_order_id': log.work_order_id,
        'external_id': log.external_id,
        'status': log.status,
        'error_message': log.error_message,
        'retry_count': log.retry_count,
        'sync_time': log.sync_time,
        'create_time': log.create_time,
    }


# ==================== 辅助函数: 审计 ====================

def _audit_to_dict(record) -> Dict[str, Any]:
    """将审计 ORM 对象转为响应字典"""
    data = {
        'id': record.id,
        'prediction_id': record.prediction_id,
        'node_type': record.node_type,
        'node_id': record.node_id,
        'input_hash': record.input_hash,
        'model_version': record.model_version,
        'model_type': record.model_type,
        'retention_years': record.retention_years,
        'expire_time': record.expire_time,
        'create_time': record.create_time,
        'strategy_version': record.strategy_version,
        'strategy_type': record.strategy_type,
    }
    for field, attr in [
        ('feature_summary', record.feature_summary),
        ('intermediate_results', record.intermediate_results),
        ('final_decision', record.final_decision),
        ('explainability', record.explainability),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except Exception:
                data[field] = None
        else:
            data[field] = None
    return data


# ==================== 合规审计管理 ====================

@router.get(
    "/audit/records",
    response_model=AuditListResponse,
    tags=["合规审计"],
    summary="查询审计记录列表"
)
async def list_audit_records(
    node_type: Optional[str] = Query(None, description="节点类型 bolt/flange"),
    node_id: Optional[str] = Query(None, description="节点ID"),
    model_version: Optional[str] = Query(None, description="模型版本"),
    start_time: Optional[datetime] = Query(None, description="起始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询预测审计记录列表"""
    try:
        from app.services.audit import AuditService
        service = AuditService()
        records = service.query_audits(
            node_type=node_type, node_id=node_id,
            model_version=model_version,
            start_time=start_time, end_time=end_time,
            limit=limit, offset=offset,
        )
        items = [_audit_to_dict(r) for r in records]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询审计记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/audit/records/{audit_id}",
    response_model=AuditRecordResponse,
    tags=["合规审计"],
    summary="获取审计记录详情"
)
async def get_audit_record(audit_id: int):
    """获取单条审计记录详情"""
    try:
        from app.services.audit import AuditService
        service = AuditService()
        record = service.get_audit(audit_id)
        if not record:
            raise HTTPException(status_code=404, detail="审计记录不存在")
        return _audit_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取审计记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/audit/records/{audit_id}/retention",
    response_model=AuditRecordResponse,
    tags=["合规审计"],
    summary="更新审计记录保留年限"
)
async def update_audit_retention(audit_id: int, request: AuditRetentionUpdateRequest):
    """更新审计记录的保留年限（可配置 N 年保留）"""
    try:
        from app.services.audit import AuditService
        service = AuditService()
        record = service.update_retention(audit_id, request.retention_years)
        if not record:
            raise HTTPException(status_code=404, detail="审计记录不存在")
        return _audit_to_dict(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新保留年限失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/audit/cleanup",
    response_model=AuditCleanupResponse,
    tags=["合规审计"],
    summary="清理过期审计记录"
)
async def cleanup_expired_audits():
    """
    清理已过期的审计记录

    根据每条记录的 expire_time 判断是否过期，自动删除。
    """
    try:
        from app.services.audit import AuditService
        service = AuditService()
        count = service.cleanup_expired()
        return {
            "cleaned_count": count,
            "message": f"已清理 {count} 条过期审计记录",
        }
    except Exception as e:
        logger.error(f"清理过期审计记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/audit/export",
    tags=["合规审计"],
    summary="导出审计包"
)
async def export_audit_package(request: AuditExportRequest):
    """
    按时间范围导出审计包

    支持 CSV 和 PDF 格式:
    - CSV: 返回纯文本 CSV 数据
    - PDF: 返回 HTML 格式（可转 PDF）
    """
    try:
        from app.services.audit import ExportService
        service = ExportService()

        if request.start_time >= request.end_time:
            raise HTTPException(
                status_code=400, detail="起始时间必须早于结束时间"
            )

        if request.format == 'csv':
            csv_content = service.export_csv(
                start_time=request.start_time,
                end_time=request.end_time,
                node_type=request.node_type,
                node_id=request.node_id,
            )
            from fastapi.responses import PlainTextResponse
            filename = (
                f"audit_{request.start_time.strftime('%Y%m%d')}_"
                f"{request.end_time.strftime('%Y%m%d')}.csv"
            )
            return PlainTextResponse(
                content=csv_content,
                media_type='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                },
            )
        elif request.format == 'pdf':
            html_content = service.generate_pdf_html(
                start_time=request.start_time,
                end_time=request.end_time,
                node_type=request.node_type,
                node_id=request.node_id,
            )
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {request.format}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出审计包失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 可解释性报告 ====================

@router.get(
    "/audit/records/{audit_id}/explainability",
    response_model=ExplainabilityReportResponse,
    tags=["合规审计"],
    summary="获取可解释性报告"
)
async def get_explainability_report(audit_id: int):
    """
    获取指定审计记录的可解释性报告

    包含:
    - LSTM 注意力权重
    - 关键时间步
    - 风险因子分解
    - 规则命中项
    """
    try:
        from app.services.audit import AuditService, ExplainabilityService
        audit_service = AuditService()
        explain_service = ExplainabilityService()

        record = audit_service.get_audit(audit_id)
        if not record:
            raise HTTPException(status_code=404, detail="审计记录不存在")

        report = explain_service.get_explainability_for_audit(record)
        if not report:
            raise HTTPException(
                status_code=404, detail="该记录无可解释性报告"
            )

        return {
            'prediction_id': record.prediction_id,
            'attention_weights': report.get('attention_weights'),
            'key_timesteps': report.get('key_timesteps'),
            'risk_factor_decomposition': report.get(
                'risk_factor_decomposition'
            ),
            'rule_hits': report.get('rule_hits'),
            'strategy_adjustment': report.get('strategy_adjustment'),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可解释性报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据质量治理 ====================

_data_quality_engine = None


def get_data_quality_engine():
    """获取数据质量引擎实例"""
    global _data_quality_engine
    if _data_quality_engine is None:
        from app.services.data_quality import DataQualityEngine
        _data_quality_engine = DataQualityEngine()
    return _data_quality_engine


def _parse_time_series_data(data: List[List[Any]]):
    """解析时序数据"""
    timestamps = []
    values = []
    for item in data:
        if len(item) >= 2:
            t = item[0]
            v = item[1]
            if isinstance(t, str):
                try:
                    t = datetime.fromisoformat(t.replace('Z', '+00:00'))
                except Exception:
                    t = None
            timestamps.append(t)
            try:
                values.append(float(v) if v is not None else float('nan'))
            except (ValueError, TypeError):
                values.append(float('nan'))
    return np.array(values), np.array(timestamps) if timestamps else None


def _save_quality_check_to_db(
    sensor_id: str,
    check_result: Any,
    quality_score: Any,
):
    """保存质量检查结果到数据库"""
    try:
        from app.utils.database import get_db, DataQualityCheck
        with get_db() as db:
            if db is None:
                return
            check = DataQualityCheck(
                sensor_id=sensor_id,
                total_points=check_result.total_points,
                valid_points=check_result.valid_points,
                overall_score=quality_score.overall_score,
                completeness_score=quality_score.dimensions.get(
                    'completeness'
                ).score if 'completeness' in quality_score.dimensions else 100.0,
                consistency_score=quality_score.dimensions.get(
                    'consistency'
                ).score if 'consistency' in quality_score.dimensions else 100.0,
                validity_score=quality_score.dimensions.get(
                    'validity'
                ).score if 'validity' in quality_score.dimensions else 100.0,
                stability_score=quality_score.dimensions.get(
                    'stability'
                ).score if 'stability' in quality_score.dimensions else 100.0,
                rule_scores=str({k: v for k, v in check_result.rule_scores.items()}),
                violations=str([v.to_dict() for v in check_result.violations]),
                quality_level=quality_score.overall_level.value,
                valid_for_training=quality_score.valid_for_training,
                confidence_adjustment=quality_score.confidence_adjustment,
                check_time=datetime.now(),
            )
            db.add(check)
            db.commit()
    except Exception as e:
        logger.warning(f"保存质量检查结果失败: {e}")


@router.post(
    "/data-quality/check",
    response_model=QualityEvaluationResponse,
    tags=["数据质量"],
    summary="评估传感器数据质量"
)
async def check_data_quality(request: DataQualityCheckRequest):
    """
    评估传感器数据质量（完整流程）

    包含:
    - 5项质量规则检查（缺失率、重复、时间倒挂、越界、漂移）
    - 多维度质量评分
    - 数据过滤建议
    - 异常分类（可选）
    """
    try:
        engine = get_data_quality_engine()
        values, timestamps = _parse_time_series_data(request.data)

        if len(values) == 0:
            raise HTTPException(status_code=400, detail="无效的输入数据")

        result = engine.evaluate_sensor_data(
            sensor_id=request.sensor_id,
            values=values,
            timestamps=timestamps,
            include_anomaly_classification=request.include_anomaly_classification,
        )

        _save_quality_check_to_db(
            sensor_id=request.sensor_id,
            check_result=engine.rules_engine.check(
                request.sensor_id, values, timestamps
            ),
            quality_score=engine.quality_scorer.score(
                engine.rules_engine.check(request.sensor_id, values, timestamps)
            ),
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"数据质量检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/data-quality/batch-check",
    tags=["数据质量"],
    summary="批量评估传感器数据质量"
)
async def batch_check_data_quality(request: DataQualityCheckBatchRequest):
    """批量评估多个传感器的数据质量"""
    try:
        engine = get_data_quality_engine()
        results = {}

        for sensor_id, data in request.sensors_data.items():
            try:
                values, timestamps = _parse_time_series_data(data)
                if len(values) == 0:
                    results[sensor_id] = {'error': '无效数据'}
                    continue

                result = engine.evaluate_sensor_data(
                    sensor_id=sensor_id,
                    values=values,
                    timestamps=timestamps,
                    include_anomaly_classification=False,
                )
                results[sensor_id] = result

                check_result = engine.rules_engine.check(sensor_id, values, timestamps)
                quality_score = engine.quality_scorer.score(check_result)
                _save_quality_check_to_db(sensor_id, check_result, quality_score)
            except Exception as e:
                logger.error(f"评估传感器 {sensor_id} 失败: {e}")
                results[sensor_id] = {'error': str(e)}

        return {
            'total_sensors': len(request.sensors_data),
            'successful': len([r for r in results.values() if 'error' not in r]),
            'failed': len([r for r in results.values() if 'error' in r]),
            'results': results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量质量检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-quality/score/{sensor_id}",
    response_model=SensorQualityScoreSchema,
    tags=["数据质量"],
    summary="获取传感器质量评分"
)
async def get_sensor_quality_score(
    sensor_id: str,
    recent_data_limit: int = Query(100, ge=10, le=1000, description="使用最近N条数据"),
):
    """
    获取传感器的质量评分

    从数据库读取最近数据进行评估。
    """
    try:
        from app.utils.database import get_bolt_recent_data

        engine = get_data_quality_engine()

        recent_data = get_bolt_recent_data(
            sensor_id=int(sensor_id) if sensor_id.isdigit() else sensor_id,
            limit=recent_data_limit,
        )

        if not recent_data:
            raise HTTPException(
                status_code=404,
                detail=f"传感器 {sensor_id} 没有可用数据"
            )

        data_list = [
            [str(d.create_time), d.ptf] for d in recent_data
        ]
        values, timestamps = _parse_time_series_data(data_list)

        check_result, quality_score = engine.evaluate_quality_only(
            sensor_id=sensor_id,
            values=values,
            timestamps=timestamps,
        )

        _save_quality_check_to_db(sensor_id, check_result, quality_score)

        return {
            'sensor_id': quality_score.sensor_id,
            'overall_score': quality_score.overall_score,
            'overall_level': quality_score.overall_level.value,
            'dimensions': {
                k.value: {
                    'dimension': k.value,
                    'score': v.score,
                    'weight': v.weight,
                    'contributing_rules': v.contributing_rules,
                }
                for k, v in quality_score.dimensions.items()
            },
            'valid_for_training': quality_score.valid_for_training,
            'confidence_adjustment': quality_score.confidence_adjustment,
            'rule_violations_count': {
                k.value: v for k, v in quality_score.rule_violations_count.items()
            },
            'calculate_time': quality_score.calculate_time,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取传感器质量评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/data-quality/adjust-confidence",
    response_model=ConfidenceAdjustmentResponse,
    tags=["数据质量"],
    summary="调整预测置信度"
)
async def adjust_prediction_confidence(request: ConfidenceAdjustmentRequest):
    """根据数据质量调整预测置信度"""
    try:
        engine = get_data_quality_engine()
        values, timestamps = _parse_time_series_data(request.data)

        if len(values) == 0:
            raise HTTPException(status_code=400, detail="无效的输入数据")

        adjusted_confidence = engine.adjust_prediction_confidence(
            sensor_id=request.sensor_id,
            original_confidence=request.original_confidence,
            values=values,
            timestamps=timestamps,
        )

        check_result, quality_score = engine.evaluate_quality_only(
            sensor_id=request.sensor_id,
            values=values,
            timestamps=timestamps,
        )

        reasons = []
        if quality_score.overall_score < 60:
            reasons.append("整体数据质量较低")
        for dim, dim_score in quality_score.dimensions.items():
            if dim_score.score < 70:
                reasons.append(f"{dim.value}维度质量差: {dim_score.score:.1f}分")
        if quality_score.confidence_adjustment < 0.8:
            reasons.append(f"置信度调整系数: {quality_score.confidence_adjustment:.2f}")

        if not reasons:
            reasons.append("数据质量良好，置信度无需大幅调整")

        return {
            'sensor_id': request.sensor_id,
            'original_confidence': request.original_confidence,
            'adjusted_confidence': adjusted_confidence,
            'quality_score': quality_score.overall_score,
            'quality_level': quality_score.overall_level.value,
            'adjustment_factor': adjusted_confidence / max(request.original_confidence, 0.0001),
            'reasons': reasons,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调整置信度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/data-quality/report/generate",
    response_model=DailyQualityReportSchema,
    tags=["数据质量"],
    summary="生成每日质量报告"
)
async def generate_quality_report(request: QualityReportRequest):
    """
    生成每日数据质量报告

    包含:
    - 整体质量统计
    - 问题传感器排行
    - 修复建议列表
    - 异常分类统计
    - 质量趋势分析
    """
    try:
        engine = get_data_quality_engine()

        if request.sensor_ids is None:
            from app.utils.database import get_db
            with get_db() as db:
                if db is not None:
                    from sqlalchemy import text
                    result = db.execute(text(
                        "SELECT DISTINCT sensor_id FROM sc_data_quality_checks "
                        "ORDER BY check_time DESC LIMIT 50"
                    ))
                    request.sensor_ids = [row[0] for row in result.fetchall()]

        report = engine.generate_daily_report(
            report_date=request.report_date,
            sensor_ids=request.sensor_ids,
            save_to_db=request.save_to_db,
        )

        return report.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成质量报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-quality/report/latest",
    response_model=DailyQualityReportSchema,
    tags=["数据质量"],
    summary="获取最新质量报告"
)
async def get_latest_quality_report():
    """从数据库获取最新的质量报告"""
    try:
        from app.utils.database import get_db, QualityReport
        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=503, detail="数据库不可用")

            report = db.query(QualityReport).order_by(
                QualityReport.report_date.desc()
            ).first()

            if not report:
                raise HTTPException(status_code=404, detail="暂无质量报告")

            import ast
            return {
                'report_date': report.report_date,
                'total_sensors': report.total_sensors,
                'average_quality_score': report.average_score,
                'quality_distribution': ast.literal_eval(
                    report.quality_distribution
                ) if report.quality_distribution else {},
                'problem_sensors': ast.literal_eval(
                    report.problem_sensors
                ) if report.problem_sensors else [],
                'recommendations': ast.literal_eval(
                    report.recommendations
                ) if report.recommendations else [],
                'anomaly_statistics': ast.literal_eval(
                    report.anomaly_statistics
                ) if report.anomaly_statistics else {},
                'quality_trend': ast.literal_eval(
                    report.quality_trend
                ) if report.quality_trend else [],
                'summary': report.summary,
                'generated_at': report.create_time,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新质量报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-quality/history/{sensor_id}",
    tags=["数据质量"],
    summary="获取传感器质量历史记录"
)
async def get_sensor_quality_history(request: DataQualityHistoryRequest = None):
    """获取传感器的质量检查历史记录"""
    try:
        from app.utils.database import get_db, DataQualityCheck
        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=503, detail="数据库不可用")

            query = db.query(DataQualityCheck).filter(
                DataQualityCheck.sensor_id == request.sensor_id
            )

            if request.start_time:
                query = query.filter(
                    DataQualityCheck.check_time >= request.start_time
                )
            if request.end_time:
                query = query.filter(
                    DataQualityCheck.check_time <= request.end_time
                )

            records = query.order_by(
                DataQualityCheck.check_time.desc()
            ).limit(request.limit).all()

            import ast
            result = []
            for record in records:
                result.append({
                    'id': record.id,
                    'sensor_id': record.sensor_id,
                    'total_points': record.total_points,
                    'valid_points': record.valid_points,
                    'overall_score': record.overall_score,
                    'completeness_score': record.completeness_score,
                    'consistency_score': record.consistency_score,
                    'validity_score': record.validity_score,
                    'stability_score': record.stability_score,
                    'quality_level': record.quality_level,
                    'valid_for_training': record.valid_for_training,
                    'confidence_adjustment': record.confidence_adjustment,
                    'violations': ast.literal_eval(
                        record.violations
                    ) if record.violations else [],
                    'check_time': record.check_time,
                })

            return {
                'sensor_id': request.sensor_id,
                'total_records': len(records),
                'records': result,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取质量历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-quality/problem-sensors",
    tags=["数据质量"],
    summary="获取问题传感器列表"
)
async def get_problem_sensors(
    min_score: float = Query(60.0, ge=0.0, le=100.0, description="最低评分阈值"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
):
    """
    获取问题传感器列表（按问题严重程度排序）

    Args:
        min_score: 低于此分数的传感器被视为问题传感器
        limit: 返回数量限制
    """
    try:
        from app.utils.database import get_db, DataQualityCheck
        from sqlalchemy import text

        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=503, detail="数据库不可用")

            query = text("""
                SELECT
                    dqc.sensor_id,
                    dqc.overall_score,
                    dqc.quality_level,
                    dqc.valid_for_training,
                    dqc.confidence_adjustment,
                    dqc.check_time
                FROM sc_data_quality_checks dqc
                INNER JOIN (
                    SELECT sensor_id, MAX(check_time) as max_time
                    FROM sc_data_quality_checks
                    GROUP BY sensor_id
                ) latest ON dqc.sensor_id = latest.sensor_id
                    AND dqc.check_time = latest.max_time
                WHERE dqc.overall_score < :min_score
                ORDER BY dqc.overall_score ASC
                LIMIT :limit
            """)

            result = db.execute(query, {
                'min_score': min_score,
                'limit': limit,
            })

            problem_sensors = []
            for row in result.fetchall():
                problem_sensors.append({
                    'sensor_id': row[0],
                    'overall_score': row[1],
                    'quality_level': row[2],
                    'valid_for_training': bool(row[3]),
                    'confidence_adjustment': row[4],
                    'check_time': row[5],
                })

            return {
                'min_score_threshold': min_score,
                'total_problems': len(problem_sensors),
                'problem_sensors': problem_sensors,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取问题传感器列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-quality/anomalies/{sensor_id}/classify",
    tags=["数据质量"],
    summary="分类传感器异常"
)
async def classify_sensor_anomalies(
    sensor_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    recent_data_limit: int = Query(200, ge=50, le=2000, description="使用最近N条数据"),
):
    """
    分类传感器异常，区分真异常与采集异常

    从数据库获取异常数据和原始数据进行分析。
    """
    try:
        from app.utils.database import get_bolt_recent_data

        engine = get_data_quality_engine()

        recent_data = get_bolt_recent_data(
            sensor_id=int(sensor_id) if sensor_id.isdigit() else sensor_id,
            limit=recent_data_limit,
        )

        if not recent_data:
            raise HTTPException(
                status_code=404,
                detail=f"传感器 {sensor_id} 没有可用数据"
            )

        data_list = [
            [str(d.create_time), d.ptf] for d in recent_data
        ]
        values, timestamps = _parse_time_series_data(data_list)

        result = engine.classify_sensor_anomalies(
            sensor_id=sensor_id,
            data=values,
            timestamps=timestamps,
            start_time=start_time,
            end_time=end_time,
        )

        if result is None:
            return {
                'sensor_id': sensor_id,
                'message': '未找到需要分类的异常数据',
                'total_anomalies': 0,
                'classified_anomalies': [],
            }

        return result.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分类异常失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-quality/summary",
    tags=["数据质量"],
    summary="获取数据质量总览"
)
async def get_data_quality_summary(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
):
    """
    获取数据质量总览

    包含:
    - 整体质量分布
    - 质量趋势
    - 问题统计
    """
    try:
        from app.utils.database import get_db
        from sqlalchemy import text

        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=503, detail="数据库不可用")

            # 质量分布
            dist_query = text(f"""
                SELECT
                    quality_level,
                    COUNT(DISTINCT sensor_id) as sensor_count
                FROM (
                    SELECT
                        sensor_id,
                        quality_level,
                        ROW_NUMBER() OVER (
                            PARTITION BY sensor_id ORDER BY check_time DESC
                        ) as rn
                    FROM sc_data_quality_checks
                    WHERE check_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                ) t
                WHERE rn = 1
                GROUP BY quality_level
            """)
            dist_result = db.execute(dist_query)
            quality_distribution = {}
            for row in dist_result.fetchall():
                quality_distribution[row[0]] = row[1]

            # 平均评分趋势
            trend_query = text(f"""
                SELECT
                    DATE(check_time) as date,
                    AVG(overall_score) as avg_score,
                    COUNT(DISTINCT sensor_id) as sensor_count
                FROM sc_data_quality_checks
                WHERE check_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                GROUP BY DATE(check_time)
                ORDER BY date ASC
            """)
            trend_result = db.execute(trend_query)
            quality_trend = []
            for row in trend_result.fetchall():
                quality_trend.append({
                    'date': str(row[0]),
                    'average_score': float(row[1]) if row[1] else None,
                    'sensor_count': row[2],
                })

            # 问题统计
            problem_query = text(f"""
                SELECT
                    COUNT(DISTINCT sensor_id) as problem_sensor_count
                FROM (
                    SELECT
                        sensor_id,
                        overall_score,
                        ROW_NUMBER() OVER (
                            PARTITION BY sensor_id ORDER BY check_time DESC
                        ) as rn
                    FROM sc_data_quality_checks
                    WHERE check_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                ) t
                WHERE rn = 1 AND overall_score < 60
            """)
            problem_result = db.execute(problem_query).fetchone()
            problem_sensor_count = problem_result[0] if problem_result else 0

            # 异常统计
            anomaly_query = text(f"""
                SELECT
                    classification,
                    COUNT(*) as count
                FROM sc_anomaly_data
                WHERE create_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                    AND classification IS NOT NULL
                GROUP BY classification
            """)
            anomaly_result = db.execute(anomaly_query)
            anomaly_distribution = {}
            for row in anomaly_result.fetchall():
                anomaly_distribution[row[0]] = row[1]

            total_sensors_query = text(f"""
                SELECT COUNT(DISTINCT sensor_id)
                FROM sc_data_quality_checks
                WHERE check_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
            """)
            total_sensors_result = db.execute(total_sensors_query).fetchone()
            total_sensors = total_sensors_result[0] if total_sensors_result else 0

            # 计算平均评分
            avg_query = text(f"""
                SELECT AVG(t.overall_score)
                FROM (
                    SELECT
                        sensor_id,
                        overall_score,
                        ROW_NUMBER() OVER (
                            PARTITION BY sensor_id ORDER BY check_time DESC
                        ) as rn
                    FROM sc_data_quality_checks
                    WHERE check_time >= DATE_SUB(NOW(), INTERVAL {days} DAY)
                ) t
                WHERE rn = 1
            """)
            avg_result = db.execute(avg_query).fetchone()
            average_score = float(avg_result[0]) if avg_result[0] else 0.0

            return {
                'statistics_days': days,
                'total_sensors': total_sensors,
                'average_quality_score': average_score,
                'quality_distribution': quality_distribution,
                'problem_sensor_count': problem_sensor_count,
                'anomaly_distribution': anomaly_distribution,
                'quality_trend': quality_trend,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取质量总览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 边缘计算 SDK ====================

_edge_devices: Dict[str, Dict[str, Any]] = {}


@router.post(
    "/edge/device/register",
    response_model=EdgeDeviceRegisterResponse,
    tags=["边缘计算"],
    summary="注册边缘设备"
)
async def register_edge_device(request: EdgeDeviceRegisterRequest):
    try:
        device_info = {
            'device_id': request.device_id,
            'device_name': request.device_name,
            'device_type': request.device_type,
            'location': request.location,
            'capabilities': request.capabilities,
            'registered_at': datetime.now().isoformat(),
            'last_heartbeat': None,
            'model_version': None,
        }
        _edge_devices[request.device_id] = device_info
        logger.info(f"边缘设备注册: {request.device_id}")
        return EdgeDeviceRegisterResponse(
            device_id=request.device_id,
            status="success",
            message=f"设备 {request.device_id} 注册成功",
            registered_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"边缘设备注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/edge/device/heartbeat",
    response_model=EdgeDeviceHeartbeatResponse,
    tags=["边缘计算"],
    summary="边缘设备心跳"
)
async def edge_device_heartbeat(request: EdgeDeviceHeartbeatRequest):
    try:
        if request.device_id in _edge_devices:
            _edge_devices[request.device_id]['last_heartbeat'] = datetime.now().isoformat()
            _edge_devices[request.device_id]['model_version'] = request.model_version
            _edge_devices[request.device_id]['cache_size'] = request.cache_size
            _edge_devices[request.device_id]['unsynced_count'] = request.unsynced_count

        version_manager = _get_version_manager()
        latest_version = None
        force_sync = False
        for model_id, versions in version_manager._versions.items():
            for v in reversed(versions):
                if v.is_active:
                    latest_version = v.version
                    break
            if latest_version:
                break

        if latest_version and request.model_version and latest_version != request.model_version:
            force_sync = True

        return EdgeDeviceHeartbeatResponse(
            device_id=request.device_id,
            latest_model_version=latest_version,
            force_sync=force_sync,
            server_time=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"边缘设备心跳失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/edge/model/latest",
    response_model=EdgeModelLatestResponse,
    tags=["边缘计算"],
    summary="获取最新模型版本信息"
)
async def get_edge_model_latest(request: EdgeModelLatestRequest):
    try:
        version_manager = _get_version_manager()
        model_id = request.node_id or request.model_type
        active_version = version_manager.get_version(model_id)

        if active_version is None:
            raise HTTPException(status_code=404, detail="未找到模型版本")

        download_url = f"/edge/model/download/{active_version.version}"
        if request.model_type:
            download_url += f"?model_type={request.model_type}"
        if request.node_id:
            download_url += f"&node_id={request.node_id}"

        return EdgeModelLatestResponse(
            version=active_version.version,
            model_type=request.model_type,
            node_id=request.node_id,
            download_url=download_url,
            file_hash=active_version.file_hash,
            file_size=0,
            created_at=active_version.created_at,
            metrics=active_version.metrics,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取最新模型版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/edge/model/download/{version}",
    tags=["边缘计算"],
    summary="下载模型包"
)
async def download_edge_model(
    version: str,
    model_type: str = Query("bolt"),
    node_id: Optional[str] = Query(None),
    format: str = Query("onnx"),
):
    try:
        version_manager = _get_version_manager()
        model_id = node_id or model_type
        model_version = version_manager.get_version(model_id, version)

        if model_version is None:
            raise HTTPException(status_code=404, detail="模型版本不存在")

        if not os.path.exists(model_version.file_path):
            raise HTTPException(status_code=404, detail="模型文件不存在")

        from edge_sdk.model_exporter import ModelExporter, ExportFormat
        from edge_sdk.model_package import PackageBundler, PackageSigner
        import tempfile

        export_format = ExportFormat.ONNX if format == "onnx" else ExportFormat.TORCHSCRIPT
        model_file_path = model_version.file_path
        export_dir = tempfile.mkdtemp(prefix="edge_export_")

        try:
            from app.models.bolt_lstm import BoltLSTMModel
            model = BoltLSTMModel(bolt_id=model_id)
            model.load(model_file_path)

            sample_input = torch.randn(1, 100, 2)

            exporter = ModelExporter()
            export_result = exporter.export(
                model=model.model,
                model_type=model_type,
                export_format=export_format,
                output_dir=export_dir,
                preprocessing_params={},
                sample_input=sample_input,
            )

            signer = PackageSigner()
            bundler = PackageBundler()
            package = bundler.create_package(
                model_path=export_result.model_path,
                manifest_path=export_result.manifest_path,
                preprocessing_path=export_result.preprocessing_path,
                output_dir=export_dir,
                model_type=model_type,
                version=version,
                signer=signer,
            )

            package_dir = Path(export_dir) / package.package_id
            if not package_dir.exists():
                for d in Path(export_dir).iterdir():
                    if d.is_dir():
                        package_dir = d
                        break

            import shutil
            zip_path = shutil.make_archive(
                str(Path(export_dir) / f"model_{version}"),
                'zip',
                root_dir=str(package_dir),
            )

            from fastapi.responses import FileResponse
            return FileResponse(
                path=zip_path,
                media_type='application/zip',
                filename=f"model_{model_type}_{version}.zip",
                background=BackgroundTasks(),
            )
        except Exception as export_err:
            logger.error(f"模型导出失败: {export_err}")
            from fastapi.responses import FileResponse
            return FileResponse(
                path=model_file_path,
                media_type='application/octet-stream',
                filename=os.path.basename(model_file_path),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载模型包失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/edge/model/export",
    response_model=EdgeModelExportResponse,
    tags=["边缘计算"],
    summary="导出边缘模型包"
)
async def export_edge_model(
    request: EdgeModelExportRequest,
    background_tasks: BackgroundTasks,
):
    try:
        version_manager = _get_version_manager()
        model_id = request.node_id or request.model_type
        model_version = version_manager.get_version(model_id, request.version)

        if model_version is None:
            raise HTTPException(status_code=404, detail="模型版本不存在")

        return EdgeModelExportResponse(
            model_type=request.model_type,
            node_id=request.node_id,
            version=model_version.version,
            export_format=request.export_format,
            package_url=f"/edge/model/download/{model_version.version}?model_type={request.model_type}&format={request.export_format}",
            file_hash=model_version.file_hash,
            file_size=0,
            includes_preprocessing=True,
            includes_signature=True,
            exported_at=datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出边缘模型包失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/edge/predictions/upload",
    response_model=EdgePredictionUploadResponse,
    tags=["边缘计算"],
    summary="批量上报边缘预测结果"
)
async def upload_edge_predictions(request: EdgePredictionUploadRequest):
    try:
        received_count = len(request.predictions)
        logger.info(f"接收边缘预测结果: device={request.device_id}, count={received_count}")

        for pred in request.predictions:
            logger.debug(f"边缘预测: {pred.get('node_id', 'unknown')} - class={pred.get('predicted_class')}")

        return EdgePredictionUploadResponse(
            device_id=request.device_id,
            received_count=received_count,
            status="success",
            message=f"成功接收 {received_count} 条预测结果",
        )
    except Exception as e:
        logger.error(f"批量上报边缘预测结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/edge/device/status",
    tags=["边缘计算"],
    summary="获取所有边缘设备状态"
)
async def list_edge_devices():
    try:
        devices = []
        for device_id, info in _edge_devices.items():
            devices.append({
                'device_id': device_id,
                'device_name': info.get('device_name'),
                'device_type': info.get('device_type'),
                'location': info.get('location'),
                'registered_at': info.get('registered_at'),
                'last_heartbeat': info.get('last_heartbeat'),
                'model_version': info.get('model_version'),
                'cache_size': info.get('cache_size', 0),
                'unsynced_count': info.get('unsynced_count', 0),
            })
        return {'total': len(devices), 'devices': devices}
    except Exception as e:
        logger.error(f"获取边缘设备状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_version_manager():
    from app.core.model_version import ModelVersionManager
    return ModelVersionManager()


# ============================================================
# 多租户与组织架构
# ============================================================

def _tenant_to_dict(t) -> Dict[str, Any]:
    data = {
        'id': t.id,
        'tenant_code': t.tenant_code,
        'tenant_name': t.tenant_name,
        'contact_email': t.contact_email,
        'contact_phone': t.contact_phone,
        'status': t.status,
        'expire_time': t.expire_time,
        'create_time': t.create_time,
        'update_time': t.update_time,
    }
    if t.settings:
        try:
            data['settings'] = json.loads(t.settings)
        except Exception:
            data['settings'] = None
    else:
        data['settings'] = None
    return data


def _org_node_to_dict(n) -> Dict[str, Any]:
    extra = None
    if n.extra_info:
        try:
            extra = json.loads(n.extra_info)
        except Exception:
            extra = None
    data = {
        'id': n.id,
        'tenant_id': n.tenant_id,
        'parent_id': n.parent_id,
        'node_code': n.node_code,
        'node_name': n.node_name,
        'node_type': n.node_type,
        'path': n.path,
        'level': n.level,
        'sort_order': n.sort_order,
        'extra_info': extra,
        'status': n.status,
        'create_time': n.create_time,
        'update_time': n.update_time,
        'children': [],
    }
    return data


def _quota_to_dict(q) -> Dict[str, Any]:
    return {
        'tenant_id': q.tenant_id,
        'max_models': q.max_models,
        'max_api_calls_per_day': q.max_api_calls_per_day,
        'max_storage_mb': q.max_storage_mb,
        'max_users': q.max_users,
        'max_org_nodes': q.max_org_nodes,
        'current_model_count': q.current_model_count,
        'current_api_calls_today': q.current_api_calls_today,
        'current_storage_mb': q.current_storage_mb,
        'current_user_count': q.current_user_count,
        'current_org_node_count': q.current_org_node_count,
        'create_time': q.create_time,
        'update_time': q.update_time,
    }


def _user_to_dict(u) -> Dict[str, Any]:
    return {
        'id': u.id,
        'tenant_id': u.tenant_id,
        'username': u.username,
        'display_name': u.display_name,
        'email': u.email,
        'phone': u.phone,
        'role': u.role,
        'org_node_id': u.org_node_id,
        'status': u.status,
        'last_login_time': u.last_login_time,
        'create_time': u.create_time,
        'update_time': u.update_time,
    }


def _api_key_to_dict(k) -> Dict[str, Any]:
    perms = None
    if k.permissions:
        try:
            perms = json.loads(k.permissions)
        except Exception:
            perms = None
    return {
        'id': k.id,
        'tenant_id': k.tenant_id,
        'api_key': k.api_key,
        'key_name': k.key_name,
        'permissions': perms,
        'rate_limit': k.rate_limit,
        'user_id': k.user_id,
        'expires_at': k.expires_at,
        'last_used_at': k.last_used_at,
        'status': k.status,
        'create_time': k.create_time,
        'update_time': k.update_time,
    }


# ---------- 租户登录 ----------

@router.post(
    "/tenant/login",
    response_model=TenantLoginResponse,
    tags=["多租户"],
    summary="租户用户登录",
)
async def tenant_login(request: TenantLoginRequest):
    """租户用户登录, 返回令牌"""
    try:
        from app.services.tenant import TenantUserService
        from app.api.auth import generate_tenant_token
        svc = TenantUserService()
        result = svc.authenticate(request.tenant_code, request.username, request.password)
        if not result:
            raise HTTPException(status_code=401, detail="租户编码、用户名或密码错误")
        token = generate_tenant_token(
            tenant_id=result["tenant_id"],
            user_id=result["user_id"],
            username=result["username"],
            role=result["role"],
        )
        return TenantLoginResponse(
            token=token,
            tenant_id=result["tenant_id"],
            user_id=result["user_id"],
            username=result["username"],
            role=result["role"],
            expires_at=datetime.now() + timedelta(hours=24),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"租户登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 租户管理 ----------

@router.post(
    "/tenants",
    response_model=TenantResponse,
    tags=["多租户"],
    summary="创建租户",
)
async def create_tenant(request: TenantCreateRequest):
    """创建新租户, 自动创建默认配额和管理员账号"""
    try:
        from app.services.tenant import TenantService
        svc = TenantService()
        tenant = svc.create_tenant(
            tenant_code=request.tenant_code,
            tenant_name=request.tenant_name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            expire_time=request.expire_time,
        )
        if not tenant:
            raise HTTPException(status_code=500, detail="创建租户失败")
        return _tenant_to_dict(tenant)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建租户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants",
    response_model=TenantListResponse,
    tags=["多租户"],
    summary="查询租户列表",
)
async def list_tenants(
    status: Optional[str] = Query(None, description="状态 active/suspended/deleted"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询租户列表"""
    try:
        from app.services.tenant import TenantService
        svc = TenantService()
        tenants = svc.list_tenants(status=status, limit=limit, offset=offset)
        items = [_tenant_to_dict(t) for t in tenants]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询租户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    tags=["多租户"],
    summary="获取租户详情",
)
async def get_tenant(tenant_id: int):
    """获取租户详情"""
    try:
        from app.services.tenant import TenantService
        svc = TenantService()
        tenant = svc.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")
        return _tenant_to_dict(tenant)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取租户详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    tags=["多租户"],
    summary="更新租户",
)
async def update_tenant(tenant_id: int, request: TenantUpdateRequest):
    """更新租户信息"""
    try:
        from app.services.tenant import TenantService
        svc = TenantService()
        data = request.model_dump(exclude_unset=True)
        tenant = svc.update_tenant(tenant_id, **data)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")
        return _tenant_to_dict(tenant)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新租户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}",
    tags=["多租户"],
    summary="删除租户",
)
async def delete_tenant(tenant_id: int):
    """软删除租户"""
    try:
        from app.services.tenant import TenantService
        svc = TenantService()
        ok = svc.delete_tenant(tenant_id)
        if not ok:
            raise HTTPException(status_code=404, detail="租户不存在")
        return {"status": "success", "message": "租户已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除租户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 组织架构 ----------

@router.post(
    "/tenants/{tenant_id}/org/nodes",
    response_model=OrgNodeResponse,
    tags=["组织架构"],
    summary="创建组织节点",
)
async def create_org_node(tenant_id: int, request: OrgNodeCreateRequest):
    """
    创建组织节点

    层级: 集团(group) → 工厂(factory) → 装置(unit) → 法兰面(flange) → 螺栓(bolt)
    """
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        node = svc.create_node(
            tenant_id=tenant_id,
            node_name=request.node_name,
            node_type=request.node_type,
            parent_id=request.parent_id,
            node_code=request.node_code,
            sort_order=request.sort_order,
            extra_info=request.extra_info,
        )
        if not node:
            raise HTTPException(status_code=500, detail="创建组织节点失败")
        return _org_node_to_dict(node)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建组织节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/org/nodes",
    tags=["组织架构"],
    summary="查询组织节点列表",
)
async def list_org_nodes(
    tenant_id: int,
    parent_id: Optional[int] = Query(None, description="父节点ID"),
    node_type: Optional[str] = Query(None, description="节点类型"),
    status: Optional[str] = Query(None, description="状态"),
):
    """查询组织节点列表"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        nodes = svc.list_nodes(
            tenant_id=tenant_id,
            parent_id=parent_id,
            node_type=node_type,
            status=status,
        )
        return [_org_node_to_dict(n) for n in nodes]
    except Exception as e:
        logger.error(f"查询组织节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/org/tree",
    response_model=OrgTreeResponse,
    tags=["组织架构"],
    summary="获取组织架构树",
)
async def get_org_tree(tenant_id: int):
    """获取租户的完整组织架构树"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        tree = svc.get_tree(tenant_id)
        return {"tenant_id": tenant_id, "nodes": tree}
    except Exception as e:
        logger.error(f"获取组织架构树失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/org/nodes/{node_id}",
    response_model=OrgNodeResponse,
    tags=["组织架构"],
    summary="获取组织节点详情",
)
async def get_org_node(tenant_id: int, node_id: int):
    """获取组织节点详情"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        node = svc.get_node(tenant_id, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        return _org_node_to_dict(node)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取组织节点详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/tenants/{tenant_id}/org/nodes/{node_id}",
    response_model=OrgNodeResponse,
    tags=["组织架构"],
    summary="更新组织节点",
)
async def update_org_node(tenant_id: int, node_id: int, request: OrgNodeUpdateRequest):
    """更新组织节点"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        data = request.model_dump(exclude_unset=True)
        node = svc.update_node(tenant_id, node_id, **data)
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        return _org_node_to_dict(node)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新组织节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}/org/nodes/{node_id}",
    tags=["组织架构"],
    summary="删除组织节点",
)
async def delete_org_node(tenant_id: int, node_id: int):
    """删除组织节点(存在子节点时不可删除)"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        ok = svc.delete_node(tenant_id, node_id)
        if not ok:
            raise HTTPException(status_code=404, detail="节点不存在")
        return {"status": "success", "message": "节点已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除组织节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/org/nodes/{node_id}/ancestors",
    tags=["组织架构"],
    summary="获取祖先节点",
)
async def get_org_ancestors(tenant_id: int, node_id: int):
    """获取指定节点的所有祖先节点(从集团到父节点)"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        ancestors = svc.get_ancestors(tenant_id, node_id)
        return [_org_node_to_dict(a) for a in ancestors]
    except Exception as e:
        logger.error(f"获取祖先节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/org/nodes/{node_id}/descendants",
    tags=["组织架构"],
    summary="获取后代节点",
)
async def get_org_descendants(tenant_id: int, node_id: int):
    """获取指定节点的所有后代节点"""
    try:
        from app.services.tenant import OrganizationService
        svc = OrganizationService()
        descendants = svc.get_descendants(tenant_id, node_id)
        return [_org_node_to_dict(d) for d in descendants]
    except Exception as e:
        logger.error(f"获取后代节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 配额管理 ----------

@router.get(
    "/tenants/{tenant_id}/quota",
    response_model=QuotaResponse,
    tags=["配额管理"],
    summary="获取租户配额",
)
async def get_tenant_quota(tenant_id: int):
    """获取租户的配额和当前用量"""
    try:
        from app.services.tenant import QuotaService
        svc = QuotaService()
        quota = svc.get_quota(tenant_id)
        if not quota:
            raise HTTPException(status_code=404, detail="配额信息不存在")
        return _quota_to_dict(quota)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/tenants/{tenant_id}/quota",
    response_model=QuotaResponse,
    tags=["配额管理"],
    summary="更新租户配额",
)
async def update_tenant_quota(tenant_id: int, request: QuotaUpdateRequest):
    """更新租户配额上限"""
    try:
        from app.services.tenant import QuotaService
        svc = QuotaService()
        data = request.model_dump(exclude_unset=True)
        quota = svc.update_quota(tenant_id, **data)
        if not quota:
            raise HTTPException(status_code=404, detail="配额信息不存在")
        return _quota_to_dict(quota)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 租户用户管理 ----------

@router.post(
    "/tenants/{tenant_id}/users",
    response_model=TenantUserResponse,
    tags=["租户用户"],
    summary="创建租户用户",
)
async def create_tenant_user(tenant_id: int, request: TenantUserCreateRequest):
    """租户管理员自助创建子账号"""
    try:
        from app.services.tenant import TenantUserService, QuotaService
        quota_svc = QuotaService()
        if not quota_svc.check_quota(tenant_id, "user"):
            raise HTTPException(status_code=429, detail="用户数已达配额上限")
        svc = TenantUserService()
        user = svc.create_user(
            tenant_id=tenant_id,
            username=request.username,
            password=request.password,
            display_name=request.display_name,
            email=request.email,
            phone=request.phone,
            role=request.role,
            org_node_id=request.org_node_id,
        )
        if not user:
            raise HTTPException(status_code=500, detail="创建用户失败")
        return _user_to_dict(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建租户用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/users",
    response_model=TenantUserListResponse,
    tags=["租户用户"],
    summary="查询租户用户列表",
)
async def list_tenant_users(
    tenant_id: int,
    role: Optional[str] = Query(None, description="角色"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """查询租户下的用户列表"""
    try:
        from app.services.tenant import TenantUserService
        svc = TenantUserService()
        users = svc.list_users(
            tenant_id=tenant_id, role=role, status=status,
            limit=limit, offset=offset,
        )
        total = svc.count_users(tenant_id)
        items = [_user_to_dict(u) for u in users]
        return {"total": total, "items": items}
    except Exception as e:
        logger.error(f"查询租户用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/users/{user_id}",
    response_model=TenantUserResponse,
    tags=["租户用户"],
    summary="获取租户用户详情",
)
async def get_tenant_user(tenant_id: int, user_id: int):
    """获取租户用户详情"""
    try:
        from app.services.tenant import TenantUserService
        svc = TenantUserService()
        user = svc.get_user(tenant_id, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return _user_to_dict(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取租户用户详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/tenants/{tenant_id}/users/{user_id}",
    response_model=TenantUserResponse,
    tags=["租户用户"],
    summary="更新租户用户",
)
async def update_tenant_user(tenant_id: int, user_id: int, request: TenantUserUpdateRequest):
    """更新租户用户信息(角色、状态等)"""
    try:
        from app.services.tenant import TenantUserService
        svc = TenantUserService()
        data = request.model_dump(exclude_unset=True)
        user = svc.update_user(tenant_id, user_id, **data)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return _user_to_dict(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新租户用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/tenants/{tenant_id}/users/{user_id}/password",
    tags=["租户用户"],
    summary="修改租户用户密码",
)
async def change_tenant_user_password(
    tenant_id: int, user_id: int, request: TenantUserPasswordRequest,
):
    """修改租户用户密码"""
    try:
        from app.services.tenant import TenantUserService
        svc = TenantUserService()
        ok = svc.change_password(tenant_id, user_id, request.new_password)
        if not ok:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"status": "success", "message": "密码已修改"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}/users/{user_id}",
    tags=["租户用户"],
    summary="禁用租户用户",
)
async def delete_tenant_user(tenant_id: int, user_id: int):
    """禁用租户用户(软删除)"""
    try:
        from app.services.tenant import TenantUserService
        svc = TenantUserService()
        ok = svc.delete_user(tenant_id, user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"status": "success", "message": "用户已禁用"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 租户 API Key 管理 ----------

@router.post(
    "/tenants/{tenant_id}/api-keys",
    response_model=TenantAPIKeyCreateResponse,
    tags=["租户API Key"],
    summary="创建租户API Key",
)
async def create_tenant_api_key(tenant_id: int, request: TenantAPIKeyCreateRequest):
    """
    创建租户 API Key

    明文密钥仅在创建时返回一次, 之后无法再查看。
    """
    try:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        result = svc.create_api_key(
            tenant_id=tenant_id,
            key_name=request.key_name,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            user_id=request.user_id,
            expires_at=request.expires_at,
        )
        if not result:
            raise HTTPException(status_code=500, detail="创建API Key失败")
        resp = {k: v for k, v in result.items() if k != "api_key_plain"}
        resp["api_key_plain"] = result["api_key_plain"]
        return resp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建API Key失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/api-keys",
    tags=["租户API Key"],
    summary="查询租户API Key列表",
)
async def list_tenant_api_keys(
    tenant_id: int,
    status: Optional[str] = Query(None, description="状态 active/revoked"),
):
    """查询租户下的API Key列表"""
    try:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        keys = svc.list_api_keys(tenant_id=tenant_id, status=status)
        return [_api_key_to_dict(k) for k in keys]
    except Exception as e:
        logger.error(f"查询API Key失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tenants/{tenant_id}/api-keys/{key_id}",
    response_model=TenantAPIKeyResponse,
    tags=["租户API Key"],
    summary="获取API Key详情",
)
async def get_tenant_api_key(tenant_id: int, key_id: int):
    """获取API Key详情"""
    try:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        key_obj = svc.get_api_key(tenant_id, key_id)
        if not key_obj:
            raise HTTPException(status_code=404, detail="API Key不存在")
        return _api_key_to_dict(key_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取API Key详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/tenants/{tenant_id}/api-keys/{key_id}",
    response_model=TenantAPIKeyResponse,
    tags=["租户API Key"],
    summary="更新API Key",
)
async def update_tenant_api_key(
    tenant_id: int, key_id: int, request: TenantAPIKeyUpdateRequest,
):
    """更新API Key(名称、权限、速率限制等)"""
    try:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        data = request.model_dump(exclude_unset=True)
        key_obj = svc.update_api_key(tenant_id, key_id, **data)
        if not key_obj:
            raise HTTPException(status_code=404, detail="API Key不存在")
        return _api_key_to_dict(key_obj)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新API Key失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/tenants/{tenant_id}/api-keys/{key_id}",
    tags=["租户API Key"],
    summary="吊销API Key",
)
async def revoke_tenant_api_key(tenant_id: int, key_id: int):
    """吊销API Key"""
    try:
        from app.services.tenant import TenantAPIKeyService
        svc = TenantAPIKeyService()
        ok = svc.revoke_api_key(tenant_id, key_id)
        if not ok:
            raise HTTPException(status_code=404, detail="API Key不存在")
        return {"status": "success", "message": "API Key已吊销"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"吊销API Key失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 辅助函数: 知识库案例 ====================

def _case_to_dict(case) -> Dict[str, Any]:
    """将案例 ORM 对象转为响应字典"""
    data = {
        'id': case.id,
        'case_no': case.case_no,
        'case_title': case.case_title,
        'node_type': case.node_type,
        'node_id': case.node_id,
        'fault_type': case.fault_type,
        'fault_level': case.fault_level,
        'diagnosis': case.diagnosis,
        'root_cause': case.root_cause,
        'effectiveness_score': case.effectiveness_score,
        'status': case.status,
        'version': case.version,
        'tenant_id': case.tenant_id,
        'creator_id': case.creator_id,
        'creator_name': case.creator_name,
        'reviewer_id': case.reviewer_id,
        'reviewer_name': case.reviewer_name,
        'review_time': case.review_time,
        'review_comment': case.review_comment,
        'source_alert_id': case.source_alert_id,
        'source_prediction_id': case.source_prediction_id,
        'create_time': case.create_time,
        'update_time': case.update_time,
    }

    for field, attr in [
        ('working_condition', case.working_condition),
        ('sensor_features', case.sensor_features),
        ('treatment_plan', case.treatment_plan),
        ('effect_evaluation', case.effect_evaluation),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except Exception:
                data[field] = None
        else:
            data[field] = None

    if case.tags:
        try:
            data['tags'] = json.loads(case.tags)
        except Exception:
            data['tags'] = []
    else:
        data['tags'] = []

    return data


def _version_to_dict(version) -> Dict[str, Any]:
    """将版本记录 ORM 对象转为响应字典"""
    data = {
        'id': version.id,
        'case_id': version.case_id,
        'version': version.version,
        'case_title': version.case_title,
        'diagnosis': version.diagnosis,
        'effectiveness_score': version.effectiveness_score,
        'change_summary': version.change_summary,
        'operator_id': version.operator_id,
        'operator_name': version.operator_name,
        'create_time': version.create_time,
    }

    for field, attr in [
        ('treatment_plan', version.treatment_plan),
        ('effect_evaluation', version.effect_evaluation),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except Exception:
                data[field] = None
        else:
            data[field] = None

    return data


# ==================== 知识库案例管理 ====================

@router.post(
    "/knowledge/cases",
    tags=["知识库CBR"],
    summary="创建案例"
)
async def create_knowledge_case(request: KnowledgeCaseCreateRequest):
    """创建新的知识库案例"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        # 处理嵌套模型
        working_condition = None
        if request.working_condition:
            working_condition = request.working_condition.model_dump()

        treatment_plan = None
        if request.treatment_plan:
            treatment_plan = request.treatment_plan.model_dump()

        effect_evaluation = None
        if request.effect_evaluation:
            effect_evaluation = request.effect_evaluation.model_dump()

        sensor_data = request.sensor_data
        sensor_features = request.sensor_features

        case = service.create_case(
            case_title=request.case_title,
            node_type=request.node_type,
            node_id=request.node_id,
            fault_type=request.fault_type,
            fault_level=request.fault_level,
            working_condition=working_condition,
            sensor_data=sensor_data,
            sensor_features=sensor_features,
            diagnosis=request.diagnosis,
            root_cause=request.root_cause,
            treatment_plan=treatment_plan,
            effect_evaluation=effect_evaluation,
            source_alert_id=request.source_alert_id,
            source_prediction_id=request.source_prediction_id,
            tags=request.tags,
            creator_id=request.creator_id,
            creator_name=request.creator_name,
            tenant_id=request.tenant_id,
            submit_for_review=request.submit_for_review,
        )

        if not case:
            raise HTTPException(status_code=500, detail="创建案例失败")

        return _case_to_dict(case)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge/cases",
    response_model=KnowledgeCaseListResponse,
    tags=["知识库CBR"],
    summary="查询案例列表"
)
async def list_knowledge_cases(
    status: Optional[str] = Query(None, description="状态 draft/pending_review/approved/rejected"),
    node_type: Optional[str] = Query(None, description="节点类型 bolt/flange"),
    fault_type: Optional[str] = Query(None, description="故障类型"),
    fault_level: Optional[int] = Query(None, ge=1, le=4, description="故障级别 1-4"),
    tenant_id: Optional[int] = Query(None, description="租户ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询知识库案例列表"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        total, cases = service.list_cases(
            status=status,
            node_type=node_type,
            fault_type=fault_type,
            fault_level=fault_level,
            tenant_id=tenant_id,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )

        items = [_case_to_dict(c) for c in cases]
        return {"total": total, "items": items}
    except Exception as e:
        logger.error(f"查询案例列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge/cases/{case_id}",
    tags=["知识库CBR"],
    summary="获取案例详情"
)
async def get_knowledge_case(case_id: int):
    """获取单条案例详情"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        case = service.get_case(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="案例不存在")

        return _case_to_dict(case)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取案例详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/knowledge/cases/{case_id}",
    tags=["知识库CBR"],
    summary="更新案例"
)
async def update_knowledge_case(case_id: int, request: KnowledgeCaseUpdateRequest):
    """更新案例（自动创建新版本）"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        # 处理嵌套模型
        working_condition = None
        if request.working_condition:
            working_condition = request.working_condition.model_dump()

        treatment_plan = None
        if request.treatment_plan:
            treatment_plan = request.treatment_plan.model_dump()

        effect_evaluation = None
        if request.effect_evaluation:
            effect_evaluation = request.effect_evaluation.model_dump()

        case = service.update_case(
            case_id=case_id,
            case_title=request.case_title,
            fault_type=request.fault_type,
            fault_level=request.fault_level,
            working_condition=working_condition,
            sensor_data=request.sensor_data,
            sensor_features=request.sensor_features,
            diagnosis=request.diagnosis,
            root_cause=request.root_cause,
            treatment_plan=treatment_plan,
            effect_evaluation=effect_evaluation,
            tags=request.tags,
            change_summary=request.change_summary,
            submit_for_review=request.submit_for_review,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
        )

        if not case:
            raise HTTPException(status_code=404, detail="案例不存在")

        return _case_to_dict(case)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/knowledge/cases/{case_id}",
    tags=["知识库CBR"],
    summary="删除案例"
)
async def delete_knowledge_case(case_id: int):
    """删除案例及其版本和审核记录"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        ok = service.delete_case(case_id)
        if not ok:
            raise HTTPException(status_code=404, detail="案例不存在")

        return {"status": "success", "message": "案例已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 案例审核 ====================

@router.post(
    "/knowledge/cases/{case_id}/submit-review",
    tags=["知识库CBR"],
    summary="提交审核"
)
async def submit_case_for_review(
    case_id: int,
    operator_id: Optional[str] = Query(None, description="操作人ID"),
    operator_name: Optional[str] = Query(None, description="操作人姓名"),
):
    """将案例提交审核"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        case = service.submit_for_review(case_id, operator_id, operator_name)
        if not case:
            raise HTTPException(status_code=404, detail="案例不存在")

        return _case_to_dict(case)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交审核失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge/cases/{case_id}/review",
    tags=["知识库CBR"],
    summary="审核案例"
)
async def review_knowledge_case(case_id: int, request: CaseReviewRequest):
    """审核案例（通过/驳回/需修改）"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        case = service.review_case(
            case_id=case_id,
            review_result=request.review_result,
            review_comment=request.review_comment,
            reviewer_id=request.reviewer_id,
            reviewer_name=request.reviewer_name,
            review_level=request.review_level,
        )

        if not case:
            raise HTTPException(status_code=404, detail="案例不存在")

        return _case_to_dict(case)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审核案例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge/cases/{case_id}/reviews",
    tags=["知识库CBR"],
    summary="获取审核记录"
)
async def list_case_reviews(case_id: int):
    """获取案例的审核历史记录"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        reviews = service.list_reviews(case_id)
        return reviews
    except Exception as e:
        logger.error(f"获取审核记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 版本管理 ====================

@router.get(
    "/knowledge/cases/{case_id}/versions",
    tags=["知识库CBR"],
    summary="获取版本历史"
)
async def list_case_versions(case_id: int):
    """获取案例的版本历史"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        versions = service.get_case_versions(case_id)
        return [_version_to_dict(v) for v in versions]
    except Exception as e:
        logger.error(f"获取版本历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge/cases/{case_id}/versions/{version}",
    tags=["知识库CBR"],
    summary="获取指定版本"
)
async def get_case_version(case_id: int, version: int):
    """获取案例的指定版本详情"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        v = service.get_case_version(case_id, version)
        if not v:
            raise HTTPException(status_code=404, detail="版本不存在")

        return _version_to_dict(v)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取版本详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/knowledge/cases/{case_id}/versions/compare",
    tags=["知识库CBR"],
    summary="对比版本差异"
)
async def compare_case_versions(
    case_id: int,
    version_from: int = Query(..., description="起始版本"),
    version_to: int = Query(..., description="目标版本"),
):
    """对比两个版本之间的差异"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        result = service.compare_versions(case_id, version_from, version_to)
        return result
    except Exception as e:
        logger.error(f"版本对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/knowledge/cases/{case_id}/versions/{version}/revert",
    tags=["知识库CBR"],
    summary="回退到指定版本"
)
async def revert_case_to_version(
    case_id: int,
    version: int,
    operator_id: Optional[str] = Query(None, description="操作人ID"),
    operator_name: Optional[str] = Query(None, description="操作人姓名"),
):
    """回退案例到指定版本（会创建新版本）"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        case = service.revert_to_version(case_id, version, operator_id, operator_name)
        if not case:
            raise HTTPException(status_code=404, detail="案例或版本不存在")

        return _case_to_dict(case)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"版本回退失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 相似度检索 ====================

@router.post(
    "/knowledge/cases/search/similar",
    tags=["知识库CBR"],
    summary="检索相似案例 (Top-K)"
)
async def search_similar_cases(request: CaseSimilaritySearchRequest):
    """
    基于特征向量检索 Top-K 相似案例

    相似度基于:
    - 58维传感器特征向量（余弦相似度）
    - 故障类型匹配
    - 节点类型匹配
    """
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        results = service.search_similar_cases(
            node_type=request.node_type,
            node_id=request.node_id,
            fault_type=request.fault_type,
            fault_level=request.fault_level,
            sensor_data=request.sensor_data,
            sensor_features=request.sensor_features,
            feature_vector=request.feature_vector,
            tags=request.tags,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            only_approved=request.only_approved,
            tenant_id=request.tenant_id,
        )

        formatted_results = []
        for r in results:
            case_dict = _case_to_dict(r.case)
            case_dict['similarity_score'] = r.similarity_score
            formatted_results.append({
                'case': case_dict,
                'similarity_score': r.similarity_score,
                'matching_features': r.matching_features,
            })

        return {
            'total': len(results),
            'results': formatted_results,
        }
    except Exception as e:
        logger.error(f"相似案例检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 推荐措施与 RAG ====================

@router.post(
    "/knowledge/cases/recommend",
    tags=["知识库CBR"],
    summary="获取案例推荐 (推荐措施 + RAG上下文)"
)
async def get_case_recommendations(request: CaseSimilaritySearchRequest):
    """
    获取案例推荐，包含聚合推荐措施和 RAG 上下文

    返回:
    - Top-K 相似案例
    - 聚合推荐措施列表
    - RAG 上下文字符串（可直接传给LLM）
    - 置信度分数
    """
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        result = service.get_case_recommendations(
            node_type=request.node_type,
            node_id=request.node_id,
            fault_type=request.fault_type,
            fault_level=request.fault_level,
            sensor_data=request.sensor_data,
            sensor_features=request.sensor_features,
            feature_vector=request.feature_vector,
            tags=request.tags,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            only_approved=request.only_approved,
            tenant_id=request.tenant_id,
        )

        cases_dict = [_case_to_dict(c) for c in result['cases']]
        for i, c in enumerate(cases_dict):
            c['similarity_score'] = result['cases'][i].similarity_score if hasattr(result['cases'][i], 'similarity_score') else None

        return {
            'top_k': result['top_k'],
            'total_matched': result['total_matched'],
            'cases': cases_dict,
            'aggregated_recommendations': result['aggregated_recommendations'],
            'rag_context': result['rag_context'],
            'confidence_score': result['confidence_score'],
        }
    except Exception as e:
        logger.error(f"获取案例推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计信息 ====================

@router.get(
    "/knowledge/statistics",
    tags=["知识库CBR"],
    summary="获取知识库统计"
)
async def get_knowledge_statistics(tenant_id: Optional[int] = Query(None, description="租户ID")):
    """获取知识库统计信息"""
    try:
        from app.services.knowledge import KnowledgeService
        service = KnowledgeService()

        stats = service.get_statistics(tenant_id=tenant_id)
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 健康度评分 ====================

health_service = None


def _get_health_service():
    """获取健康度服务实例"""
    global health_service
    if health_service is None:
        from app.services.health_service import HealthService
        health_service = HealthService()
    return health_service


@router.post(
    "/health/calculate",
    tags=["健康度评分"],
    summary="计算螺栓健康度指数 HI",
    response_model=HealthIndexResponse,
)
async def calculate_health_index(request: HealthIndexCalculateRequest):
    """
    计算单个螺栓的健康度指数 HI（0-100）

    综合评估维度：
    - 预紧力稳定性（30%）
    - 预警频率（20%）
    - 故障历史（20%）
    - 环境应力（15%）
    - 使用年限（15%）
    """
    try:
        service = _get_health_service()

        result = service.calculate_bolt_health(
            bolt_id=request.bolt_id,
            data=request.data,
            working_condition=request.working_condition,
            nominal_preload=request.nominal_preload,
            service_age_years=request.service_age_years,
            flange_id=request.flange_id,
            save_to_db=request.save_to_db,
        )

        return {
            'success': True,
            'data': result,
            'message': '健康度计算成功',
        }
    except ValueError as e:
        logger.warning(f"健康度计算参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"健康度计算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/health/calculate/batch",
    tags=["健康度评分"],
    summary="批量计算螺栓健康度",
    response_model=HealthIndexBatchResponse,
)
async def calculate_health_index_batch(request: HealthIndexBatchCalculateRequest):
    """
    批量计算多个螺栓的健康度，或计算整个法兰面的健康度

    支持两种模式：
    1. 批量螺栓计算：传入多个螺栓数据
    2. 法兰面聚合计算：传入法兰面ID和螺栓数据，自动聚合
    """
    try:
        service = _get_health_service()

        if request.calculate_flange and request.flange_id:
            result = service.calculate_flange_health(
                flange_id=request.flange_id,
                bolts_data=request.bolts_data,
                working_condition=request.working_condition,
                save_to_db=request.save_to_db,
            )
            return {
                'success': True,
                'data': result,
                'message': '法兰面健康度计算成功',
            }
        else:
            results = []
            for bolt_data in request.bolts_data:
                bolt_result = service.calculate_bolt_health(
                    bolt_id=bolt_data['bolt_id'],
                    data=bolt_data['data'],
                    working_condition=request.working_condition,
                    nominal_preload=bolt_data.get('nominal_preload'),
                    service_age_years=bolt_data.get('service_age_years', 0),
                    flange_id=request.flange_id,
                    save_to_db=request.save_to_db,
                )
                results.append(bolt_result)

            return {
                'success': True,
                'data': {
                    'total': len(results),
                    'bolts_health': results,
                },
                'message': '批量健康度计算成功',
            }
    except ValueError as e:
        logger.warning(f"批量健康度计算参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"批量健康度计算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health/history",
    tags=["健康度评分"],
    summary="查询健康度历史记录",
    response_model=HealthIndexHistoryResponse,
)
async def get_health_history(
    node_id: str = Query(..., description="节点ID（螺栓ID或法兰面ID）"),
    node_type: str = Query("bolt", description="节点类型：bolt 或 flange"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, description="返回记录数量限制"),
):
    """
    查询螺栓或法兰面的健康度历史记录，包含趋势分析
    """
    try:
        if node_type not in ['bolt', 'flange']:
            raise ValueError("node_type 必须是 'bolt' 或 'flange'")

        service = _get_health_service()

        result = service.get_health_history(
            node_id=node_id,
            node_type=node_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        return {
            'success': True,
            'data': result,
            'message': '历史记录查询成功',
        }
    except ValueError as e:
        logger.warning(f"健康度历史查询参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"健康度历史查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/health/rul/predict",
    tags=["健康度评分"],
    summary="预测剩余使用寿命 RUL",
    response_model=RULPredictionResponse,
)
async def predict_rul(request: RULPredictionRequest):
    """
    基于历史健康度序列预测剩余使用寿命（RUL）

    支持的劣化模型：
    - linear: 线性模型（默认，数据不足时使用）
    - exponential: 指数模型
    - polynomial: 多项式模型
    - auto: 自动选择最优模型（根据R²拟合优度）

    返回结果包含：
    - RUL 预测值及置信区间
    - 劣化曲线预测序列
    - 到达预警阈值的时间
    - 模型拟合优度 R²
    """
    try:
        service = _get_health_service()

        result = service.predict_rul(
            node_id=request.node_id,
            node_type=request.node_type,
            forecast_days=request.forecast_days,
            failure_threshold=request.failure_threshold,
            warning_threshold=request.warning_threshold,
            model_type=request.model_type,
            use_history_days=request.use_history_days,
            save_to_db=request.save_to_db,
        )

        return {
            'success': True,
            'data': result,
            'message': 'RUL预测成功',
        }
    except ValueError as e:
        logger.warning(f"RUL预测参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RUL预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/health/rollup",
    tags=["健康度评分"],
    summary="生成产线/装置级健康度汇总报表",
    response_model=HealthRollupResponse,
)
async def generate_health_rollup(request: HealthRollupRequest):
    """
    生成产线或装置级的健康度汇总报表

    包含：
    - 整体健康度评分和等级
    - 各法兰面健康度统计
    - 风险汇总分析
    - 维护优先级排序
    - 劣化速率统计
    """
    try:
        service = _get_health_service()

        result = service.generate_rollup_report(
            line_id=request.line_id,
            line_name=request.line_name,
            line_type=request.line_type,
            flanges_data=request.flanges_data,
            report_date=request.report_date,
            include_details=request.include_details,
            save_to_db=request.save_to_db,
        )

        return {
            'success': True,
            'data': result,
            'message': '汇总报表生成成功',
        }
    except ValueError as e:
        logger.warning(f"汇总报表生成参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"汇总报表生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 流式预测 ====================

_stream_engine = None


def get_stream_engine():
    """获取流式预测引擎实例"""
    global _stream_engine
    if _stream_engine is None:
        from app.streaming import StreamPredictionEngine, StreamPredictionMode

        stream_config = config.get('stream_prediction', {})
        default_mode = stream_config.get('prediction_mode', 'batch')
        mode = StreamPredictionMode(default_mode)

        _stream_engine = StreamPredictionEngine(prediction_mode=mode)

        # 如果配置了启用流式预测，自动启动
        if stream_config.get('enabled', False):
            _stream_engine.start()

    return _stream_engine


@router.post(
    "/stream/ingest",
    response_model=StreamDataIngestResponse,
    tags=["流式预测"],
    summary="流式数据注入"
)
async def stream_ingest(request: StreamDataIngestRequest):
    """
    注入单条或微批次流数据

    数据进入滑动窗口，窗口满后自动触发预测。
    """
    try:
        engine = get_stream_engine()

        if not engine.is_running:
            return StreamDataIngestResponse(
                success=False,
                message="流式预测引擎未启动",
                accepted=False
            )

        if engine.prediction_mode.value != 'stream':
            return StreamDataIngestResponse(
                success=False,
                message=f"当前为 {engine.prediction_mode.value} 模式，请切换到 stream 模式",
                accepted=False
            )

        # 构建消息数据
        message_data = {
            'node_type': request.node_type,
            'node_id': request.node_id,
        }

        if request.value is not None and request.timestamp is not None:
            message_data['value'] = request.value
            message_data['timestamp'] = request.timestamp
        elif request.values is not None and request.timestamps is not None:
            message_data['values'] = request.values
            message_data['timestamps'] = request.timestamps
        elif request.data is not None:
            message_data['data'] = request.data
        else:
            raise HTTPException(
                status_code=400,
                detail="缺少数据参数：需要 value/timestamp 或 values/timestamps 或 data"
            )

        if request.metadata:
            message_data['metadata'] = request.metadata

        # 注入消息
        accepted = engine.ingest_message(message_data)

        # 获取窗口状态
        window_status = engine.get_window_status(request.node_id)

        return StreamDataIngestResponse(
            success=True,
            message="数据注入成功",
            node_id=request.node_id,
            node_type=request.node_type,
            window_current_size=window_status.get('current_size', 0) if window_status else 0,
            window_is_full=window_status.get('is_full', False) if window_status else False,
            accepted=accepted
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式数据注入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/stream/ingest/batch",
    response_model=StreamBatchIngestResponse,
    tags=["流式预测"],
    summary="批量流式数据注入"
)
async def stream_ingest_batch(request: StreamBatchIngestRequest):
    """
    批量注入多条流数据
    """
    try:
        engine = get_stream_engine()

        if not engine.is_running:
            return StreamBatchIngestResponse(
                success=False,
                total_count=len(request.messages),
                accepted_count=0,
                rejected_count=len(request.messages),
                messages=[{"error": "流式预测引擎未启动"}]
            )

        if engine.prediction_mode.value != 'stream':
            return StreamBatchIngestResponse(
                success=False,
                total_count=len(request.messages),
                accepted_count=0,
                rejected_count=len(request.messages),
                messages=[{"error": f"当前为 {engine.prediction_mode.value} 模式"}]
            )

        accepted_count = 0
        rejected_count = 0
        results = []

        for msg in request.messages:
            try:
                accepted = engine.ingest_message(msg)
                if accepted:
                    accepted_count += 1
                else:
                    rejected_count += 1
                results.append({
                    'node_id': msg.get('node_id'),
                    'accepted': accepted
                })
            except Exception as e:
                rejected_count += 1
                results.append({
                    'node_id': msg.get('node_id'),
                    'accepted': False,
                    'error': str(e)
                })

        return StreamBatchIngestResponse(
            success=True,
            total_count=len(request.messages),
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            messages=results
        )

    except Exception as e:
        logger.error(f"批量流式数据注入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stream/window/{bolt_id}",
    response_model=StreamWindowStatusResponse,
    tags=["流式预测"],
    summary="获取窗口状态"
)
async def get_stream_window(bolt_id: str):
    """
    获取指定螺栓的滑动窗口状态
    """
    try:
        engine = get_stream_engine()

        window_status = engine.get_window_status(bolt_id)
        if window_status is None:
            raise HTTPException(
                status_code=404,
                detail=f"螺栓 {bolt_id} 的窗口不存在"
            )

        return StreamWindowStatusResponse(**window_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取窗口状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stream/status",
    response_model=StreamEngineStatusResponse,
    tags=["流式预测"],
    summary="获取流式预测引擎状态"
)
async def get_stream_engine_status():
    """
    获取流式预测引擎的运行状态和统计信息
    """
    try:
        engine = get_stream_engine()
        stats = engine.get_stats_dict()
        return StreamEngineStatusResponse(**stats)

    except Exception as e:
        logger.error(f"获取引擎状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/stream/mode",
    response_model=StreamModeSwitchResponse,
    tags=["流式预测"],
    summary="切换预测模式"
)
async def switch_prediction_mode(request: StreamModeSwitchRequest):
    """
    切换预测模式：batch 或 stream

    - batch: 批处理模式，流式数据被忽略
    - stream: 流式模式，启用实时预测
    """
    try:
        engine = get_stream_engine()

        success = engine.set_prediction_mode(request.mode)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"无效的预测模式: {request.mode}"
            )

        return StreamModeSwitchResponse(
            success=True,
            current_mode=engine.prediction_mode.value,
            message=f"已切换到 {request.mode} 模式"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换预测模式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/stream/start",
    tags=["流式预测"],
    summary="启动流式预测引擎"
)
async def start_stream_engine():
    """
    启动流式预测引擎
    """
    try:
        engine = get_stream_engine()

        if engine.is_running:
            return {
                "success": True,
                "message": "流式预测引擎已在运行中",
                "is_running": True
            }

        engine.start()

        return {
            "success": True,
            "message": "流式预测引擎已启动",
            "is_running": True
        }

    except Exception as e:
        logger.error(f"启动流式预测引擎失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/stream/stop",
    tags=["流式预测"],
    summary="停止流式预测引擎"
)
async def stop_stream_engine():
    """
    停止流式预测引擎
    """
    try:
        engine = get_stream_engine()

        if not engine.is_running:
            return {
                "success": True,
                "message": "流式预测引擎未在运行",
                "is_running": False
            }

        engine.stop()

        return {
            "success": True,
            "message": "流式预测引擎已停止",
            "is_running": False
        }

    except Exception as e:
        logger.error(f"停止流式预测引擎失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/stream/config",
    response_model=StreamConfigResponse,
    tags=["流式预测"],
    summary="更新流式预测配置"
)
async def update_stream_config(request: StreamConfigUpdateRequest):
    """
    动态更新流式预测配置

    支持更新：窗口大小、最大并发流数、每流速率限制
    """
    try:
        engine = get_stream_engine()

        updated = {}

        if request.window_size is not None:
            engine.set_window_size(request.window_size)
            updated['window_size'] = request.window_size

        if request.max_concurrent_streams is not None:
            engine.set_max_concurrent_streams(request.max_concurrent_streams)
            updated['max_concurrent_streams'] = request.max_concurrent_streams

        if request.rate_per_stream is not None:
            engine.backpressure_manager.set_rate_per_stream(request.rate_per_stream)
            updated['rate_per_stream'] = request.rate_per_stream

        return StreamConfigResponse(
            success=True,
            config=updated,
            message="配置更新成功"
        )

    except Exception as e:
        logger.error(f"更新流式配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/stream/window/{bolt_id}",
    tags=["流式预测"],
    summary="清空指定螺栓窗口"
)
async def clear_stream_window(bolt_id: str):
    """
    清空指定螺栓的滑动窗口数据
    """
    try:
        engine = get_stream_engine()

        success = engine.clear_window(bolt_id)

        return {
            "success": success,
            "message": f"已清空螺栓 {bolt_id} 的窗口" if success else "清空失败"
        }

    except Exception as e:
        logger.error(f"清空窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/stream/windows",
    tags=["流式预测"],
    summary="清空所有窗口"
)
async def clear_all_stream_windows():
    """
    清空所有螺栓的滑动窗口数据
    """
    try:
        engine = get_stream_engine()

        success = engine.clear_all_windows()

        return {
            "success": success,
            "message": "已清空所有窗口" if success else "清空失败"
        }

    except Exception as e:
        logger.error(f"清空所有窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
