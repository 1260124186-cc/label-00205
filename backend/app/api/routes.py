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
from datetime import datetime
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
