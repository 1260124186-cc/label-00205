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
    StrategyConfigRequest, StrategyConfigResponse
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
