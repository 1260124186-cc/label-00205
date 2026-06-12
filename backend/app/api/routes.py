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
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
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
    FederatedPrivacyConfig, FederatedAggregatorConfig
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
