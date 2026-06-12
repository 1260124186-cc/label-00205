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
from datetime import datetime
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
