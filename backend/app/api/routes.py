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
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends, Request
from loguru import logger

from app.api.auth import get_tenant_context, revoke_tenant_token, verify_api_key, require_permission, api_key_manager, per_key_rate_limiter, audit_logger, APIKeyManager

from app.api.schemas import (
    HealthResponse, HealthComponentStatus, ErrorResponse,
    BoltPredictionRequest, BoltPredictionResponse,
    BoltEnsemblePredictionRequest, BoltEnsemblePredictionResponse,
    FlangePredictionRequest, FlangePredictionResponse,
    RiskAssessmentRequest, RiskAssessmentResponse,
    RiskAssessExplainRequest, RiskAssessExplainResponse,
    RiskProbabilityDistributionSchema, FactorContributionSchema,
    RiskCalibrationUpdateRequest, RiskCalibrationResponse,
    MonthlyForecastRequest, MonthlyForecastResponse,
    TrainingRequest, TrainingResponse,
    ModelInfoResponse,
    StrategyConfigRequest, StrategyConfigResponse,
    StrategyConfigUpdateRequest, StrategyConfigItemResponse,
    EffectiveStrategyResponse, StrategyConfigListResponse,
    StrategyRollbackRequest, StrategyAuditLogResponse,
    StrategyAuditLogListResponse, StrategyNodeOverrideDeleteRequest,
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
    EpochMetricsSchema, TrainingSessionSchema, ModelVersionSchema,
    ModelVersionListResponse, ModelVersionActivateRequest,
    ModelVersionRollbackRequest,
    ModelVersionCompareRequest, ModelVersionCompareResponse,
    TrainingSessionListResponse, TrainingStatusResponse,
    EarlyStoppingConfig, LRSchedulerConfig, ClassImbalanceConfig,
    IncrementalTrainingConfig, FocalLossConfig, TrainingConfigSchema,
    EnhancedTrainingRequest, EnhancedTrainingResponse,
    TrainingProgressSchema,
    LabelImportCSVRequest, LabelImportDBRequest,
    LabelImportResultSchema, LabelImportResponse,
    LabelImportFileItemSchema, LabelImportFileListResponse,
    WarningStrategyConfigSchema, ThresholdConfigSchema,
    ScheduledJobSchema, SchedulerJobUpdateRequest,
    SchedulerTriggerRequest, ConfigCenterResponse,
    JobExecutionLogSchema, JobExecutionLogListResponse,
    LeaderStatusSchema, SchedulerTriggerResponse,
    AnomalyDataResponse, AnomalyQueryRequest, AnomalyListResponse,
    AnomalyConfirmRequest, AnomalyFalsePositiveRequest,
    AnomalyBatchConfirmRequest, AnomalyBatchFalsePositiveRequest,
    AnomalyBatchResultResponse, AnomalyStatisticsResponse,
    AnomalyWarningImpactResponse,
    APIKeyCreateRequest, APIKeyCreateResponse,
    APIKeyInfoResponse, APIKeyListResponse,
    APIKeyRotateResponse, APIKeyRevokeResponse,
    APIAuditLogResponse, APIAuditLogListResponse,
    RateLimitStatusResponse,
    DiagnosisReportRequest, DiagnosisReportResponse,
    ReportGenerateRequest, ReportStatisticsSchema,
    PeriodicReportResponse, BatchReportGenerateRequest,
    BatchReportResponse,
    FaultDetailSchema, FaultPatternSchema,
    BoltMultivariatePredictionRequest, BoltMultivariatePredictionResponse,
    MultivariateChannelSchema, DataQualityInfo, TemperatureCompensationInfo, FeatureImportanceInfo,
    CarbonMonthlyRankingRequest, CarbonMonthlyRankingResponse,
    CarbonRiskItemSchema,
    HICarbonDualViewRequest, HICarbonDualViewResponse, HICarbonDualItemSchema,
    ESGReportExportRequest, ESGReportFragmentResponse,
    ESGReportSummarySchema, ESGTrendAnalysisSchema,
    CarbonModelConfigResponse, CarbonModelConfigUpdateRequest,
    DegradationParamsSchema, LeakageParamsSchema, EnergyCarbonParamsSchema,
    ChecklistItemSchema,
    StandardTemplateCreateRequest, StandardTemplateUpdateRequest, StandardTemplateResponse, StandardTemplateListResponse,
    InspectionTaskCreateRequest, InspectionItemCheckRequest, AutoCheckMandatoryRequest,
    InspectionTaskResponse, InspectionTaskListResponse,
    WorkOrderCloseCheckResponse, InspectionPdfExportResponse,
    BoltSkuMappingCreate, BoltSkuMappingUpdate, BoltSkuMappingResponse, BoltSkuMappingListResponse,
    BoltSkuQueryRequest,
    SparePartInventoryResponse, SparePartInventoryListResponse,
    StockAvailabilityCheckResponse,
    SparePartDemandFromRulRequest, SparePartDemandResponse, SparePartDemandListResponse,
    SparePartDemandApproveRequest, SparePartDemandFulfillRequest,
    SparePartRulScanRequest, SparePartRulScanResponse,
    SparePartDemandSummaryRequest, SparePartDemandSummaryResponse, SparePartDemandSummaryListResponse,
    PurchaseAnalysisRequest, PurchaseAnalysisResponse,
    PurchaseConfigSaveRequest, PurchaseConfigResponse,
    PurchasePlanRequest, PurchasePlanResponse,
    BoltStatusDataSchema, Flange3DCreateRequest, Flange3DExportRequest,
    Flange3DUpdateRequest, Flange3DExplosionRequest,
    BoltCoordinateItemSchema, Flange3DSceneInfoResponse,
    Flange3DExportResponse, Flange3DUpdateResponse,
    Flange3DExplosionResponse, Flange3DListResponse,
    # HPO schemas
    SearchSpaceSchema, ObjectiveConfigSchema,
    HPOCreateStudyRequest, HPOCreateStudyResponse,
    HPOStartStudyRequest, HPOStartStudyResponse,
    HPOApplyConfigRequest, HPOApplyConfigResponse,
    HPOSetNodeOverrideRequest, HPONodeOverrideResponse,
    HPOTrialSchema, HPOStudySchema, HPONodeOverrideSchema,
    HPOStudyStatusResponse, HPOStudyListResponse, HPOTrialListResponse,
    HPOCompareConfigResponse,
    # 风险热力图与传播可视化
    RiskGraphNodeSchema, RiskGraphEdgeSchema,
    PropagationGraphResponse,
    GeoJSONHeatmapRequest,
    EChartsGraphRequest, EChartsGraphResponse,
    TimeSliceRequest, TimeSliceNodeSchema, TimeSliceDataSchema, TimeSeriesResponse,
    PropagationPathRequest, PropagationPathSchema, PropagationPathListResponse,
    RiskSummaryResponse,
    EdgeWeightConfigRequest, EdgeWeightConfigResponse,
    SignificantChangeRequest, SignificantChangeSliceSchema, SignificantChangeListResponse,
    SignificantChangeItemSchema,
    WSMessageSchema, IncrementalUpdateSchema,
    # What-if 情景仿真
    WhatIfSimulationRequest, WhatIfSimulationResponse,
    SimulationScenarioHypothesis, SimulationThresholdsSchema,
    WhatIfScenarioRequest, SimulatedTrajectoryPointSchema,
    FirstThresholdCrossingSchema, RiskLevelTimelineItemSchema,
    RecommendedInterventionSchema, ScenarioSummarySchema,
    WhatIfScenarioResultSchema, ScenarioComparisonItemSchema,
    WhatIfScenarioComparisonSchema,
)
from app.services.prediction_service import PredictionService
from app.services.training_service import TrainingService
from app.services.visualization_3d import Visualization3DService
from app.services.risk_visualization.service import RiskVisualizationService
from app.services.what_if_simulation import WhatIfSimulator
from app.api.validators import (
    DataValidator,
    ValidationMode,
    format_validation_errors,
    get_validator,
)
from app.utils.config import config
from app.schedulers.job_execution import JobExecutionService
from app.schedulers.leader_election import get_leader_election
from app.schedulers.job_execution import get_instance_id
from app import __version__


# 创建路由器
router = APIRouter(dependencies=[Depends(verify_api_key)])

# 服务实例
prediction_service = None
training_service = None
visualization_3d_service = None
risk_visualization_service = None
what_if_simulator = None
federated_server = None
federated_clients: Dict[str, Any] = {}


def get_prediction_service() -> PredictionService:
    """获取预测服务实例"""
    global prediction_service
    if prediction_service is None:
        prediction_service = PredictionService()
    return prediction_service


def get_what_if_simulator() -> WhatIfSimulator:
    """获取What-if仿真引擎实例"""
    global what_if_simulator
    if what_if_simulator is None:
        what_if_simulator = WhatIfSimulator()
    return what_if_simulator


def get_training_service() -> TrainingService:
    """获取训练服务实例"""
    global training_service
    if training_service is None:
        training_service = TrainingService()
    return training_service


def get_visualization_3d_service() -> Visualization3DService:
    """获取3D可视化服务实例"""
    global visualization_3d_service
    if visualization_3d_service is None:
        visualization_3d_service = Visualization3DService()
    return visualization_3d_service


def get_risk_visualization_service() -> RiskVisualizationService:
    """获取风险可视化服务实例"""
    global risk_visualization_service
    if risk_visualization_service is None:
        risk_visualization_service = RiskVisualizationService()
    return risk_visualization_service


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


# ==================== 螺栓预测 ====================

@router.post(
    "/predict/bolt",
    response_model=BoltPredictionResponse,
    tags=["预测"],
    summary="螺栓状态预测"
)
async def predict_bolt(
    request: BoltPredictionRequest,
    validation_mode: str = Query("strict", description="校验模式: strict=严格模式, lenient=宽松模式"),
    version: Optional[str] = Query(None, description="使用指定版本的模型进行预测"),
    shadow_version: Optional[str] = Query(None, description="Shadow模式版本号，仅预测不写库，用于A/B对比"),
):
    """
    预测单个螺栓的状态

    基于最近100条预紧力数据，预测螺栓当前状态。

    状态类别:
    - 0: 正常
    - 1: 关注级预警
    - 2: 检查级预警
    - 3: 紧急级预警
    - 4: 故障

    校验模式:
    - strict: 严格模式，数据不合规直接拒绝
    - lenient: 宽松模式，自动截断/填充数据
    """
    try:
        service = get_prediction_service()
        validator = get_validator()

        # 获取螺栓ID（支持中文字段名）
        bolt_id = getattr(request, '螺栓id', None) or request.bolt_id

        # 确定校验模式
        mode = ValidationMode.LENIENT if validation_mode.lower() == 'lenient' else ValidationMode.STRICT

        # 数据校验
        validation_result = validator.validate_bolt_prediction(
            bolt_id=bolt_id,
            data=request.data,
            mode=mode
        )

        if not validation_result.is_valid:
            error_response = format_validation_errors(validation_result)
            raise HTTPException(
                status_code=400,
                detail=error_response
            )

        # 使用校验清洗后的数据
        cleaned = validation_result.cleaned_data
        values = cleaned['values']
        timestamps = cleaned['timestamps']

        # 执行预测
        result = service.predict_bolt(
            bolt_id=bolt_id,
            data=values,
            timestamps=timestamps,
            version=version,
            shadow_version=shadow_version,
        )

        # 添加校验信息到响应头
        fault_detail_obj = None
        if result.get('fault_detail'):
            fd = result['fault_detail']
            pattern_obj = None
            if fd.get('pattern'):
                pattern_obj = FaultPatternSchema(**fd['pattern'])
            fault_detail_obj = FaultDetailSchema(
                fault_type=fd['fault_type'],
                fault_confidence=fd['fault_confidence'],
                fault_name=fd.get('fault_name', ''),
                severity=fd.get('severity', 0),
                evidence=fd.get('evidence', []),
                recommendations=fd.get('recommendations', []),
                pattern=pattern_obj,
            )

        response = BoltPredictionResponse(
            bolt_id=bolt_id,
            status=result['status'],
            status_code=result['status_code'],
            confidence=result['confidence'],
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            diagnosis=result['diagnosis'],
            recommendations=result['recommendations'],
            prediction_time=datetime.now(),
            model_version=result.get('model_version'),
            shadow_version=result.get('shadow_version'),
            shadow_result=result.get('shadow_result'),
            fault_detail=fault_detail_obj,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"螺栓预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/predict/bolt/ensemble",
    response_model=BoltEnsemblePredictionResponse,
    tags=["预测"],
    summary="螺栓集成学习预测调试"
)
async def predict_bolt_ensemble(
    request: BoltEnsemblePredictionRequest,
    validation_mode: str = Query("strict", description="校验模式: strict=严格模式, lenient=宽松模式"),
):
    """
    螺栓集成学习预测调试接口

    返回各子模型分项结果与最终融合结论，用于调试和分析集成学习效果。

    支持配置:
    - method: 投票策略 (hard/soft/weighted)
    - weights: 自定义各预测器权重

    状态类别:
    - 0: 正常
    - 1: 关注级预警
    - 2: 检查级预警
    - 3: 紧急级预警
    - 4: 故障
    """
    try:
        service = get_prediction_service()
        validator = get_validator()

        mode = ValidationMode.LENIENT if validation_mode.lower() == 'lenient' else ValidationMode.STRICT

        validation_result = validator.validate_bolt_prediction(
            bolt_id=request.bolt_id,
            data=request.data,
            mode=mode
        )

        if not validation_result.is_valid:
            error_response = format_validation_errors(validation_result)
            raise HTTPException(
                status_code=400,
                detail=error_response
            )

        cleaned = validation_result.cleaned_data
        values = cleaned['values']

        result = service.predict_bolt_ensemble(
            bolt_id=request.bolt_id,
            data=values,
            version=request.version,
            method=request.method,
            weights=request.weights,
        )

        return BoltEnsemblePredictionResponse(
            bolt_id=request.bolt_id,
            prediction_source=result['prediction_source'],
            ensemble_method=result['ensemble_method'],
            final_status=result['final_status'],
            final_status_code=result['final_status_code'],
            final_confidence=result['final_confidence'],
            final_probs=result.get('final_probs'),
            weights=result['weights'],
            individual_results=result['individual_results'],
            individual_probs=result['individual_probs'],
            model_version=result['model_version'],
            duration_ms=result['duration_ms'],
            ema_accuracy=result['ema_accuracy'],
            performance_history=result['performance_history'],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"螺栓Ensemble预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/predict/bolt/multivariate",
    response_model=BoltMultivariatePredictionResponse,
    tags=["预测"],
    summary="螺栓多变量耦合预测（温度/振动/扭矩等联合输入）"
)
async def predict_bolt_multivariate(
    request: BoltMultivariatePredictionRequest,
    save_to_db: bool = Query(True, description="是否保存预测结果到数据库"),
):
    """
    螺栓多变量耦合预测接口

    支持温度、振动、扭矩、湿度、压力等多传感器数据与预紧力联合预测。
    内部使用跨通道 Attention 建模变量间的耦合关系。

    **两种数据输入方式（二选一）**：

    1. **分通道模式（推荐）**：
       - 使用 `channels` 字段传入各通道的时序数据
       - 各通道时间戳可以不同步，服务端自动对齐插值
       - 例：`{"preload": [[时间,值], ...], "temperature": [[时间,值], ...], ...}`

    2. **对齐数组模式**：
       - 使用 `aligned_data` + `aligned_channel_names`
       - 每行格式：[时间, 通道1值, 通道2值, ...]
       - 适用于各传感器已同步采集的场景

    **缺失降级策略**（可通过 enable_degradation 控制）：
    - 缺失通道数不严重：自动线性插值补全 → 标记为 `data_quality.level=partial`
    - 缺失严重（<50%完整度）且 `enable_degradation=True` → 自动降级为仅预紧力单变量预测 → 标记为 `data_quality.level=degraded`

    状态类别:
    - 0: 正常
    - 1: 关注级预警
    - 2: 检查级预警
    - 3: 紧急级预警
    - 4: 故障

    响应中新增多变量专属字段:
    - `data_quality`: 数据质量评估（full/partial/degraded，含插值点、降级信息）
    - `temp_compensation`: 温度耦合补偿详情（系数α、相关系数等）
    - `feature_importance`: 各通道对预测结果的重要性权重（可解释性）
    - `channels_info`: 实际参与计算的通道元数据（单位、描述）
    """
    try:
        from datetime import datetime

        service = get_prediction_service()
        bolt_id = request.bolt_id

        # 解析目标时间戳（可选）
        target_ts = None
        if request.timestamps:
            target_ts = np.array([
                pd.Timestamp(t).to_pydatetime() if isinstance(t, str) else t
                for t in request.timestamps
            ])

        channels_data = None
        aligned_array = None
        aligned_channel_names = None

        # 模式 1: channels 分通道数据
        if request.channels and len(request.channels) > 0:
            channels_data = {}
            for ch_name, rows in request.channels.items():
                try:
                    ts_list = []
                    val_list = []
                    for row in rows:
                        if len(row) < 2:
                            continue
                        t_raw = row[0]
                        v_raw = row[1]
                        if isinstance(t_raw, str):
                            try:
                                ts = pd.Timestamp(t_raw).to_pydatetime()
                            except Exception:
                                ts = float(t_raw)
                        else:
                            ts = t_raw
                        try:
                            val = float(v_raw) if v_raw is not None else np.nan
                        except (ValueError, TypeError):
                            val = np.nan
                        ts_list.append(ts)
                        val_list.append(val)
                    if len(ts_list) > 0:
                        channels_data[ch_name] = (
                            np.array(ts_list),
                            np.array(val_list, dtype=np.float32),
                        )
                except Exception as ch_e:
                    logger.warning(f"通道 {ch_name} 解析异常，跳过: {ch_e}")
                    continue

            if not channels_data:
                raise HTTPException(
                    status_code=400,
                    detail="channels 字段为空或解析失败，请提供至少一个有效通道（推荐包含 preload）"
                )

        # 模式 2: aligned_data 已对齐数组
        elif request.aligned_data and len(request.aligned_data) > 0:
            if not request.aligned_channel_names or len(request.aligned_channel_names) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="使用 aligned_data 模式时必须同时提供 aligned_channel_names"
                )

            try:
                raw = np.array(request.aligned_data, dtype=object)
                if raw.ndim != 2:
                    raise ValueError("aligned_data 必须是二维数组 [[时间, 通道1, 通道2, ...], ...]")

                N, M = raw.shape
                if M != len(request.aligned_channel_names) + 1:
                    raise ValueError(
                        f"aligned_data 列数={M}，"
                        f"需要 {len(request.aligned_channel_names) + 1} "
                        f"(=1时间列 + {len(request.aligned_channel_names)}通道列)"
                    )

                # 解析时间列
                t_raw_col = raw[:, 0]
                ts_parsed = []
                for t in t_raw_col:
                    if isinstance(t, str):
                        try:
                            ts_parsed.append(pd.Timestamp(t).to_pydatetime())
                        except Exception:
                            ts_parsed.append(float(t))
                    else:
                        ts_parsed.append(t)

                # 解析通道值
                values_parsed = np.zeros((N, M - 1), dtype=np.float32)
                for c in range(M - 1):
                    col = raw[:, c + 1]
                    for i in range(N):
                        v = col[i]
                        try:
                            values_parsed[i, c] = float(v) if v is not None else np.nan
                        except (ValueError, TypeError):
                            values_parsed[i, c] = np.nan

                aligned_array = values_parsed
                aligned_channel_names = list(request.aligned_channel_names)
                # 提供给预处理模块：如果请求未带 timestamps，则使用解析的 ts
                if target_ts is None:
                    target_ts = np.array(ts_parsed)

            except HTTPException:
                raise
            except Exception as parse_e:
                raise HTTPException(
                    status_code=400,
                    detail=f"aligned_data 解析失败: {parse_e}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="必须提供 channels 或 aligned_data 两种输入方式之一"
            )

        # 调用编排器的多变量预测方法
        result = service.predict_bolt_multivariate(
            bolt_id=bolt_id,
            channels_data=channels_data,
            aligned_array=aligned_array,
            aligned_channel_names=aligned_channel_names,
            target_timestamps=target_ts,
            apply_temp_compensation=request.apply_temp_compensation,
            enable_degradation=request.enable_degradation,
            version=request.version,
            save_to_db=save_to_db,
        )

        # 组装响应 Schema
        channels_info_objs = [
            MultivariateChannelSchema(**ci) for ci in result.get('channels_info', [])
        ]
        dq = result.get('data_quality', {})
        data_quality_obj = DataQualityInfo(
            level=dq.get('level', 'full'),
            complete_ratio=dq.get('complete_ratio', 1.0),
            missing_channels=dq.get('missing_channels', []),
            interpolation_count=dq.get('interpolation_count', 0),
            degradation_applied=dq.get('degradation_applied', False),
            actual_channels_used=dq.get('actual_channels_used', []),
        )

        tc = result.get('temp_compensation')
        temp_comp_obj = None
        if tc and tc.get('applied', False):
            temp_comp_obj = TemperatureCompensationInfo(
                applied=True,
                temperature_coefficient=tc.get('temperature_coefficient'),
                correlation=tc.get('correlation'),
                original_mean_preload=tc.get('original_mean_preload'),
                compensated_mean_preload=tc.get('compensated_mean_preload'),
                delta_t_mean=tc.get('delta_t_mean'),
            )
        elif tc:
            temp_comp_obj = TemperatureCompensationInfo(applied=False)

        fi = result.get('feature_importance')
        fi_obj = None
        if fi:
            fi_obj = FeatureImportanceInfo(
                preload=float(fi.get('preload', 0.0)),
                temperature=float(fi.get('temperature', 0.0)),
                humidity=float(fi.get('humidity', 0.0)),
                vibration=float(fi.get('vibration', 0.0)),
                torque=float(fi.get('torque', 0.0)),
                others=fi.get('others', {}) if fi.get('others') else {},
            )

        fault_detail_obj = None
        fd = result.get('fault_detail')
        if fd:
            pattern_obj = None
            if fd.get('pattern'):
                pattern_obj = FaultPatternSchema(**fd['pattern'])
            fault_detail_obj = FaultDetailSchema(
                fault_type=fd['fault_type'],
                fault_confidence=fd['fault_confidence'],
                fault_name=fd.get('fault_name', ''),
                severity=fd.get('severity', 0),
                evidence=fd.get('evidence', []),
                recommendations=fd.get('recommendations', []),
                pattern=pattern_obj,
            )

        response = BoltMultivariatePredictionResponse(
            bolt_id=result['bolt_id'],
            status=result['status'],
            status_code=result['status_code'],
            confidence=result['confidence'],
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            diagnosis=result['diagnosis'],
            recommendations=result['recommendations'],
            prediction_time=result.get('prediction_time') or datetime.now(),
            model_version=result.get('model_version'),
            input_dim_actual=result.get('input_dim_actual', 1),
            channels_info=channels_info_objs,
            data_quality=data_quality_obj,
            temp_compensation=temp_comp_obj,
            feature_importance=fi_obj,
            sequence_length_used=result.get('sequence_length_used', 0),
            prediction_source=result.get('prediction_source', 'multivariate_lstm'),
            fault_detail=fault_detail_obj,
            shadow_version=result.get('shadow_version'),
            shadow_result=result.get('shadow_result'),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"螺栓多变量耦合预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 法兰面预测 ====================

@router.post(
    "/predict/flange",
    response_model=FlangePredictionResponse,
    tags=["预测"],
    summary="法兰面状态预测"
)
async def predict_flange(
    request: FlangePredictionRequest,
    validation_mode: str = Query("strict", description="校验模式: strict=严格模式, lenient=宽松模式"),
    version: Optional[str] = Query(None, description="使用指定版本的模型进行预测"),
    shadow_version: Optional[str] = Query(None, description="Shadow模式版本号，仅预测不写库，用于A/B对比"),
):
    """
    预测法兰面的整体状态

    基于法兰面上所有螺栓的预紧力数据，预测法兰面状态。

    校验模式:
    - strict: 严格模式，数据不合规直接拒绝
    - lenient: 宽松模式，自动截断/填充数据
    """
    try:
        service = get_prediction_service()
        validator = get_validator()

        # 获取法兰面ID
        flange_id = getattr(request, '法兰面id', None) or request.flange_id

        # 确定校验模式
        mode = ValidationMode.LENIENT if validation_mode.lower() == 'lenient' else ValidationMode.STRICT

        # 数据校验
        validation_result = validator.validate_flange_prediction(
            flange_id=flange_id,
            data=request.data,
            mode=mode
        )

        if not validation_result.is_valid:
            error_response = format_validation_errors(validation_result)
            raise HTTPException(
                status_code=400,
                detail=error_response
            )

        # 使用校验清洗后的数据
        cleaned = validation_result.cleaned_data
        multi_bolt_data = cleaned['all_values']

        # 执行预测
        result = service.predict_flange(
            flange_id=flange_id,
            multi_bolt_data=multi_bolt_data,
            version=version,
            shadow_version=shadow_version,
        )

        fault_detail_obj = None
        if result.get('fault_detail'):
            fd = result['fault_detail']
            pattern_obj = None
            if fd.get('pattern'):
                pattern_obj = FaultPatternSchema(**fd['pattern'])
            fault_detail_obj = FaultDetailSchema(
                fault_type=fd['fault_type'],
                fault_confidence=fd['fault_confidence'],
                fault_name=fd.get('fault_name', ''),
                severity=fd.get('severity', 0),
                evidence=fd.get('evidence', []),
                recommendations=fd.get('recommendations', []),
                pattern=pattern_obj,
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
            prediction_time=datetime.now(),
            correlation_matrix=result.get('correlation_matrix'),
            causal_graph=result.get('causal_graph'),
            leading_bolts=result.get('leading_bolts'),
            propagation_paths=result.get('propagation_paths'),
            root_cause_analysis=result.get('root_cause_analysis'),
            root_cause_measures=result.get('root_cause_measures'),
            model_version=result.get('model_version'),
            shadow_version=result.get('shadow_version'),
            shadow_result=result.get('shadow_result'),
            fault_detail=fault_detail_obj,
        )

    except HTTPException:
        raise
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
async def assess_risk(
    request: RiskAssessmentRequest,
    validation_mode: str = Query("strict", description="校验模式: strict=严格模式, lenient=宽松模式")
):
    """
    评估节点（螺栓或法兰面）的风险

    返回风险评分(1-10)、风险等级(低/中/高)、概率分布P(高/中/低)和各因子贡献度。

    校验模式:
    - strict: 严格模式，数据不合规直接拒绝
    - lenient: 宽松模式，自动截断/填充数据
    """
    try:
        service = get_prediction_service()
        validator = get_validator()

        mode = ValidationMode.LENIENT if validation_mode.lower() == 'lenient' else ValidationMode.STRICT

        validation_result = validator.validate_risk_assessment(
            node_id=request.node_id,
            node_type=request.node_type,
            data=request.data,
            mode=mode
        )

        if not validation_result.is_valid:
            error_response = format_validation_errors(validation_result)
            raise HTTPException(
                status_code=400,
                detail=error_response
            )

        cleaned = validation_result.cleaned_data
        values = cleaned['values']

        result = service.assess_risk(
            node_id=request.node_id,
            node_type=request.node_type,
            data=values
        )

        prob_dist = None
        if 'probability_distribution' in result and result['probability_distribution']:
            pd = result['probability_distribution']
            prob_dist = RiskProbabilityDistributionSchema(
                p_high=pd.get('p_high', 0),
                p_medium=pd.get('p_medium', 0),
                p_low=pd.get('p_low', 0),
            )

        factor_contribs = None
        if 'factor_contributions' in result and result['factor_contributions']:
            factor_contribs = [
                FactorContributionSchema(**fc) for fc in result['factor_contributions']
            ]

        return RiskAssessmentResponse(
            node_id=request.node_id,
            node_type=request.node_type,
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            factors=result['factors'],
            diagnosis=result['diagnosis'],
            recommendations=result['recommendations'],
            confidence=result['confidence'],
            probability_distribution=prob_dist,
            factor_contributions=factor_contribs,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"风险评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/risk/assess/explain",
    response_model=RiskAssessExplainResponse,
    tags=["风险评估"],
    summary="风险评估可解释性分析"
)
async def assess_risk_explain(
    request: RiskAssessExplainRequest,
    validation_mode: str = Query("strict", description="校验模式: strict=严格模式, lenient=宽松模式")
):
    """
    风险评估可解释性分析（类似 SHAP）

    返回各因子对风险评分的贡献度，包含：
    - 概率分布 P(高/中/低)
    - 各因子贡献度（原始评分、权重、加权评分、贡献占比、方向）
    - 基准值与总贡献偏移
    - 可读性总结
    """
    try:
        service = get_prediction_service()
        validator = get_validator()

        mode = ValidationMode.LENIENT if validation_mode.lower() == 'lenient' else ValidationMode.STRICT

        validation_result = validator.validate_risk_assessment(
            node_id=request.node_id,
            node_type=request.node_type,
            data=request.data,
            mode=mode
        )

        if not validation_result.is_valid:
            error_response = format_validation_errors(validation_result)
            raise HTTPException(
                status_code=400,
                detail=error_response
            )

        cleaned = validation_result.cleaned_data
        values = cleaned['values']

        result = service.explain_risk(
            node_id=request.node_id,
            node_type=request.node_type,
            data=values,
        )

        pd = result['probability_distribution']
        prob_dist = RiskProbabilityDistributionSchema(
            p_high=pd.get('p_high', 0),
            p_medium=pd.get('p_medium', 0),
            p_low=pd.get('p_low', 0),
        )

        factor_contribs = [
            FactorContributionSchema(**fc) for fc in result['factor_contributions']
        ]

        return RiskAssessExplainResponse(
            node_id=request.node_id,
            node_type=request.node_type,
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            probability_distribution=prob_dist,
            factor_contributions=factor_contribs,
            base_value=result['base_value'],
            total_contribution=result['total_contribution'],
            summary=result['summary'],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"风险评估可解释性分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/risk/calibration",
    response_model=RiskCalibrationResponse,
    tags=["风险评估"],
    summary="更新节点级风险校准配置"
)
async def update_risk_calibration(request: RiskCalibrationUpdateRequest):
    """
    更新节点级风险模型校准（权重/阈值覆盖）

    - 设置后该节点使用自定义权重和阈值
    - 不设置则使用全局配置
    - 支持版本管理与回滚
    """
    try:
        import json
        from app.utils.database import get_db
        from app.models.risk_model import invalidate_node_calibration_cache

        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=503, detail="数据库不可用")

            try:
                db.execute("SELECT 1 FROM sc_risk_calibration LIMIT 1")
            except Exception:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS sc_risk_calibration (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        node_type VARCHAR(64) NOT NULL,
                        node_id VARCHAR(128) NOT NULL,
                        weights TEXT,
                        thresholds TEXT,
                        version INT NOT NULL DEFAULT 1,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        description VARCHAR(512),
                        operator_id VARCHAR(64),
                        operator_name VARCHAR(64),
                        create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_node (node_type, node_id, is_active)
                    )
                """)
                db.commit()

            active = db.execute(
                "SELECT id, version FROM sc_risk_calibration "
                "WHERE node_type = :nt AND node_id = :nid AND is_active = 1 "
                "ORDER BY version DESC LIMIT 1",
                {"nt": request.node_type, "nid": request.node_id},
            ).first()

            new_version = 1
            if active:
                new_version = active[1] + 1
                db.execute(
                    "UPDATE sc_risk_calibration SET is_active = 0 "
                    "WHERE node_type = :nt AND node_id = :nid AND is_active = 1",
                    {"nt": request.node_type, "nid": request.node_id},
                )

            weights_json = json.dumps(request.prior_weights, ensure_ascii=False) if request.prior_weights else None
            thresholds_json = json.dumps(request.risk_thresholds, ensure_ascii=False) if request.risk_thresholds else None

            db.execute(
                "INSERT INTO sc_risk_calibration "
                "(node_type, node_id, weights, thresholds, version, is_active, description, operator_id, operator_name) "
                "VALUES (:nt, :nid, :w, :t, :v, 1, :desc, :oid, :oname)",
                {
                    "nt": request.node_type,
                    "nid": request.node_id,
                    "w": weights_json,
                    "t": thresholds_json,
                    "v": new_version,
                    "desc": request.description,
                    "oid": request.operator_id,
                    "oname": request.operator_name,
                },
            )
            db.commit()

        invalidate_node_calibration_cache()

        from app.models.risk_model import BayesianRiskModel
        model = BayesianRiskModel()
        eff_weights = model.get_effective_weights(request.node_type, request.node_id)
        eff_thresholds = model.get_effective_thresholds(request.node_type, request.node_id)

        return RiskCalibrationResponse(
            node_type=request.node_type,
            node_id=request.node_id,
            prior_weights=eff_weights,
            risk_thresholds=eff_thresholds,
            version=new_version,
            is_active=True,
            description=request.description,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新风险校准配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/calibration",
    response_model=RiskCalibrationResponse,
    tags=["风险评估"],
    summary="查询节点级风险校准配置"
)
async def get_risk_calibration(
    node_type: str = Query(..., description="节点类型 bolt/flange/production_line"),
    node_id: str = Query(..., description="节点ID"),
):
    """
    查询节点级风险模型校准配置

    返回该节点生效的权重和阈值配置（含节点级覆盖）。
    """
    try:
        from app.models.risk_model import BayesianRiskModel
        model = BayesianRiskModel()
        eff_weights = model.get_effective_weights(node_type, node_id)
        eff_thresholds = model.get_effective_thresholds(node_type, node_id)

        return RiskCalibrationResponse(
            node_type=node_type,
            node_id=node_id,
            prior_weights=eff_weights,
            risk_thresholds=eff_thresholds,
        )

    except Exception as e:
        logger.error(f"查询风险校准配置失败: {e}")
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

    包括训练状态、最后训练时间、验证准确率、版本信息等。
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
            validation_accuracy=info.get('validation_accuracy'),
            version=info.get('version'),
            file_hash=info.get('file_hash'),
            create_time=info.get('create_time'),
            training_session_id=info.get('training_session_id'),
            description=info.get('description'),
            validation_samples=info.get('validation_samples'),
            is_incremental=info.get('is_incremental'),
            parent_version=info.get('parent_version'),
            metrics=info.get('metrics'),
            version_history=info.get('version_history')
        )

    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/train/enhanced",
    response_model=EnhancedTrainingResponse,
    tags=["模型管理"],
    summary="增强版训练模型（增量训练/学习率调度/类不平衡等）"
)
async def train_model_enhanced(
    request: EnhancedTrainingRequest,
    background_tasks: BackgroundTasks
):
    """
    增强版训练接口

    支持：
    - 增量训练（冻结部分层 + 新数据 fine-tune）
    - 可配置早停机制
    - 可配置学习率调度（ReduceLROnPlateau/StepLR/Cosine）
    - 类别不平衡处理（加权损失/过采样）
    - Focal Loss
    - 人工标注数据覆盖

    训练任务在后台执行，通过 session_id 查询进度和结果。
    """
    try:
        service = get_training_service()

        training_config = None
        if request.training_config:
            training_config = request.training_config.model_dump(exclude_none=True)

        session_id = service.start_training(
            model_type=request.model_type,
            node_id=request.node_id,
            force_retrain=request.force_retrain,
            training_config=training_config,
            data_source=request.data_source,
            is_incremental=request.is_incremental,
            base_model_version=request.base_model_version,
            freeze_layers=request.freeze_layers
        )

        background_tasks.add_task(
            service.execute_training,
            session_id=session_id
        )

        return EnhancedTrainingResponse(
            session_id=session_id,
            model_type=request.model_type,
            node_id=request.node_id,
            status="started",
            message=(
                f"训练任务已启动（{'增量训练' if request.is_incremental else '完整训练'}），"
                f"请使用 session_id={session_id} 查询状态"
            ),
            is_incremental=request.is_incremental
        )

    except Exception as e:
        logger.error(f"启动增强训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/train/status/{session_id}",
    response_model=TrainingStatusResponse,
    tags=["模型管理"],
    summary="查询训练状态"
)
async def get_training_status_endpoint(session_id: str):
    """
    根据 session_id 查询训练任务的状态和进度

    状态: pending → running → completed/failed
    """
    try:
        service = get_training_service()
        status_info = service.get_training_status(session_id)

        progress = None
        if 'progress' in status_info and status_info['progress']:
            prog = status_info['progress']
            progress = TrainingProgressSchema(
                phase=prog.get('phase'),
                current_epoch=prog.get('current_epoch'),
                total_epochs=prog.get('total_epochs'),
                current_loss=prog.get('current_loss'),
                current_acc=prog.get('current_acc'),
                bolt_id=prog.get('bolt_id'),
                flange_id=prog.get('flange_id')
            )

        return TrainingStatusResponse(
            session_id=session_id,
            model_type=status_info.get('model_type'),
            node_id=status_info.get('node_id'),
            status=status_info.get('status', 'unknown'),
            message=status_info.get('message', '未知状态'),
            start_time=status_info.get('start_time'),
            end_time=status_info.get('end_time'),
            is_incremental=status_info.get('is_incremental'),
            data_source=status_info.get('data_source'),
            total_epochs=status_info.get('total_epochs'),
            current_epoch=status_info.get('current_epoch'),
            best_epoch=status_info.get('best_epoch'),
            best_val_acc=status_info.get('best_val_acc'),
            best_val_loss=status_info.get('best_val_loss'),
            final_train_acc=status_info.get('final_train_acc'),
            final_train_loss=status_info.get('final_train_loss'),
            final_val_acc=status_info.get('final_val_acc'),
            final_val_loss=status_info.get('final_val_loss'),
            precision=status_info.get('precision'),
            recall=status_info.get('recall'),
            f1_score=status_info.get('f1_score'),
            samples_count=status_info.get('samples_count'),
            val_samples_count=status_info.get('val_samples_count'),
            error_message=status_info.get('error_message'),
            progress=progress
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询训练状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/train/sessions",
    response_model=TrainingSessionListResponse,
    tags=["模型管理"],
    summary="列出训练会话历史"
)
async def list_training_sessions(
    model_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500, description="返回数量限制")
):
    """
    列出训练会话记录

    可按模型类型和状态过滤，默认返回最近50条。
    """
    try:
        service = get_training_service()
        sessions = service.list_training_sessions(
            model_type=model_type,
            status=status,
            limit=limit
        )

        items = [
            TrainingSessionItemSchema(
                session_id=s['session_id'],
                model_type=s.get('model_type'),
                model_id=s.get('model_id'),
                status=s.get('status', 'unknown'),
                start_time=s.get('start_time'),
                end_time=s.get('end_time'),
                best_val_acc=s.get('best_val_acc'),
                f1_score=s.get('f1_score'),
                samples_count=s.get('samples_count'),
                error_message=s.get('error_message')
            )
            for s in sessions
        ]

        return TrainingSessionListResponse(
            total=len(items),
            items=items
        )

    except Exception as e:
        logger.error(f"列出训练会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/versions/{model_type}/{node_id}",
    response_model=ModelVersionListResponse,
    tags=["模型管理"],
    summary="列出模型版本历史"
)
async def list_model_versions(model_type: str, node_id: str):
    """
    列出指定模型的所有版本

    包括版本号、创建时间、训练指标、是否活动版本等。
    """
    try:
        from app.utils.database import get_db, ModelVersionORM
        import json

        items = []
        with get_db() as db:
            if db is None:
                raise HTTPException(status_code=503, detail="数据库不可用")

            versions = db.query(ModelVersionORM).filter(
                ModelVersionORM.model_id == node_id,
                ModelVersionORM.model_type == model_type
            ).order_by(
                ModelVersionORM.create_time.desc()
            ).limit(50).all()

            for v in versions:
                metrics = None
                if v.metrics:
                    try:
                        metrics = json.loads(v.metrics)
                    except Exception:
                        pass

                items.append(ModelVersionSchema(
                    version=v.version,
                    create_time=v.create_time,
                    is_active=v.is_active or False,
                    description=v.description,
                    file_path=v.file_path,
                    file_hash=v.file_hash,
                    file_size_bytes=v.file_size_bytes,
                    training_samples=v.training_samples,
                    validation_samples=v.validation_samples,
                    training_duration_seconds=v.training_duration_seconds,
                    parent_version=v.parent_version,
                    training_session_id=v.training_session_id,
                    metrics=metrics
                ))

        return ModelVersionListResponse(
            model_type=model_type,
            node_id=node_id,
            total=len(items),
            items=items
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出模型版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/activate",
    response_model=ModelVersionSchema,
    tags=["模型管理"],
    summary="激活指定模型版本"
)
async def activate_model_version(request: ModelVersionActivateRequest):
    """
    激活指定的模型版本（切换活动版本）

    通过 model_type、node_id 和 version 切换当前活动版本。
    激活后，后续预测将使用该版本的模型。
    """
    try:
        from app.services.model_version_service import get_model_version_service

        service = get_model_version_service()
        result = service.activate_version(
            model_type=request.model_type,
            node_id=request.node_id,
            version=request.version
        )

        try:
            pred_service = get_prediction_service()
            pred_service.reload_model(
                model_type=request.model_type,
                node_id=request.node_id,
            )
            logger.info(f"已清除模型缓存: {request.model_type}/{request.node_id}")
        except Exception as e:
            logger.warning(f"清除模型缓存失败: {e}")

        return ModelVersionSchema(
            version=result['version'],
            create_time=result['create_time'],
            is_active=result['is_active'],
            description=result.get('description'),
            file_path=result.get('file_path'),
            file_hash=result.get('file_hash'),
            file_size_bytes=result.get('file_size_bytes'),
            training_samples=result.get('training_samples'),
            validation_samples=result.get('validation_samples'),
            training_duration_seconds=result.get('training_duration_seconds'),
            parent_version=result.get('parent_version'),
            training_session_id=result.get('training_session_id'),
            metrics=result.get('metrics')
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活模型版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/rollback",
    response_model=ModelVersionSchema,
    tags=["模型管理"],
    summary="回滚模型版本"
)
async def rollback_model_version(request: ModelVersionRollbackRequest):
    """
    回滚到指定版本（或上一个版本）

    如果指定了 version，则回滚到该版本；
    如果未指定 version，则回滚到上一个版本。
    """
    try:
        from app.services.model_version_service import get_model_version_service

        service = get_model_version_service()
        result = service.rollback(
            model_type=request.model_type,
            node_id=request.node_id,
            version=request.version
        )

        try:
            pred_service = get_prediction_service()
            pred_service.reload_model(
                model_type=request.model_type,
                node_id=request.node_id,
            )
            logger.info(f"已清除模型缓存: {request.model_type}/{request.node_id}")
        except Exception as e:
            logger.warning(f"清除模型缓存失败: {e}")

        return ModelVersionSchema(
            version=result['version'],
            create_time=result['create_time'],
            is_active=result['is_active'],
            description=result.get('description'),
            file_path=result.get('file_path'),
            file_hash=result.get('file_hash'),
            file_size_bytes=result.get('file_size_bytes'),
            training_samples=result.get('training_samples'),
            validation_samples=result.get('validation_samples'),
            training_duration_seconds=result.get('training_duration_seconds'),
            parent_version=result.get('parent_version'),
            training_session_id=result.get('training_session_id'),
            metrics=result.get('metrics')
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回滚模型版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/versions/{model_type}/{node_id}/cleanup",
    tags=["模型管理"],
    summary="手动清理旧版本"
)
async def cleanup_old_versions(model_type: str, node_id: str):
    """
    手动清理超过 max_versions 限制的旧版本

    保留最新的 N 个版本（N = max_versions），删除其余非活动版本。
    """
    try:
        from app.services.model_version_service import get_model_version_service

        service = get_model_version_service()
        deleted_count = service.cleanup_old_versions_manual(model_type, node_id)

        return {
            'model_type': model_type,
            'node_id': node_id,
            'deleted_count': deleted_count,
            'message': f'已清理 {deleted_count} 个旧版本'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理旧版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 人工标注数据导入 ====================

@router.get(
    "/model/label/import/files",
    response_model=LabelImportFileListResponse,
    tags=["模型管理"],
    summary="列出可导入的标注CSV文件"
)
async def list_import_files():
    """
    列出导入目录中所有可导入的CSV文件
    """
    try:
        from app.services.label_import import label_import_service
        files = label_import_service.list_import_files()

        items = [
            LabelImportFileItemSchema(
                filename=f['filename'],
                path=f['path'],
                size_bytes=f['size_bytes'],
                modified_time=f['modified_time']
            )
            for f in files
        ]

        return LabelImportFileListResponse(
            total=len(items),
            items=items
        )

    except Exception as e:
        logger.error(f"列出可导入文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/label/import/csv",
    response_model=LabelImportResponse,
    tags=["模型管理"],
    summary="从CSV导入人工标注数据"
)
async def import_labels_from_csv(request: LabelImportCSVRequest):
    """
    从CSV文件导入人工标注数据

    人工标注数据的标签优先级高于系统自动生成的规则标签。

    CSV要求:
    - 节点ID列（如 bolt_id、传感器id 等，自动检测）
    - 标签列（数字 0-4 或中文标签名: 正常/关注级预警/检查级预警/紧急级预警/故障）
    - 可选: 数据点列、时间戳列、标注人列
    """
    try:
        from app.services.label_import import label_import_service

        result = label_import_service.import_from_csv(
            csv_path=request.csv_path,
            node_type=request.node_type,
            label_column=request.label_column,
            id_column=request.id_column,
            data_column=request.data_column,
            timestamp_column=request.timestamp_column,
            labeler_name=request.labeler_name,
            auto_approve=request.auto_approve,
            skip_errors=request.skip_errors
        )

        return LabelImportResponse(
            status="success",
            message=(
                f"CSV标注导入完成: 成功{result.imported}条, "
                f"重复{result.duplicates}条, 错误{result.errors}条"
            ),
            result=LabelImportResultSchema(
                total=result.total,
                imported=result.imported,
                skipped=result.skipped,
                duplicates=result.duplicates,
                errors=result.errors,
                error_details=result.error_details if result.error_details else None
            )
        )

    except FileNotFoundError as e:
        logger.warning(f"CSV导入失败 - 文件不存在: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.warning(f"CSV导入失败 - 参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"CSV标注导入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/label/import/db",
    response_model=LabelImportResponse,
    tags=["模型管理"],
    summary="从数据库表导入人工标注数据"
)
async def import_labels_from_db(request: LabelImportDBRequest):
    """
    从现有数据库表导入人工标注数据

    指定源表名、ID字段和标签字段，可带WHERE条件。
    导入的标注会覆盖规则标签。
    """
    try:
        from app.services.label_import import label_import_service

        result = label_import_service.import_from_db(
            source_table=request.source_table,
            node_type=request.node_type,
            id_field=request.id_field,
            label_field=request.label_field,
            data_field=request.data_field,
            timestamp_field=request.timestamp_field,
            where_clause=request.where_clause,
            labeler_name=request.labeler_name,
            auto_approve=request.auto_approve
        )

        return LabelImportResponse(
            status="success",
            message=(
                f"数据库标注导入完成: 成功{result.imported}条, "
                f"重复{result.duplicates}条, 错误{result.errors}条"
            ),
            result=LabelImportResultSchema(
                total=result.total,
                imported=result.imported,
                skipped=result.skipped,
                duplicates=result.duplicates,
                errors=result.errors,
                error_details=result.error_details if result.error_details else None
            )
        )

    except ConnectionError as e:
        logger.warning(f"DB导入失败 - 连接错误: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        logger.warning(f"DB导入失败 - 参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DB标注导入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 策略配置 ====================

@router.get(
    "/strategy/config",
    response_model=EffectiveStrategyResponse,
    tags=["配置"],
    summary="查询当前生效策略"
)
async def get_strategy_config(
    node_type: Optional[str] = Query(None, description="节点类型 bolt/flange/production_line"),
    node_id: Optional[str] = Query(None, description="节点ID"),
):
    """
    查询当前生效的预警策略

    - 不传参数：返回全局策略
    - 传入 node_type + node_id：返回该节点的生效策略（含节点覆盖）
    - 节点级覆盖优先于全局策略
    """
    try:
        from app.services.prediction.strategy_config_service import (
            get_strategy_config_service,
        )
        service = get_strategy_config_service()

        global_cfg = service.get_effective()
        global_item = StrategyConfigItemResponse(**global_cfg)

        node_overrides = []
        if node_type and node_id:
            override_cfg = service.get_effective(node_type, node_id)
            if override_cfg.get('scope') != 'global':
                node_overrides.append(StrategyConfigItemResponse(**override_cfg))
            effective_cfg = override_cfg
        else:
            effective_cfg = global_cfg

        effective_item = StrategyConfigItemResponse(**effective_cfg)

        return EffectiveStrategyResponse(
            global_config=global_item,
            node_overrides=node_overrides,
            effective=effective_item,
        )

    except Exception as e:
        logger.error(f"查询策略配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/strategy/config",
    response_model=StrategyConfigItemResponse,
    tags=["配置"],
    summary="更新预警策略（立即生效）"
)
async def update_strategy_config(request: StrategyConfigUpdateRequest):
    """
    更新预警策略配置，更新后立即生效

    - scope=global: 更新全局策略
    - scope=bolt/flange/production_line + node_type + node_id: 创建/更新节点级覆盖
    - 节点级覆盖优先于全局策略
    - 每次更新自动生成新版本，旧版本保留可回滚
    - 所有变更记录审计日志
    """
    try:
        if request.scope != 'global' and (not request.node_type or not request.node_id):
            raise HTTPException(
                status_code=400,
                detail="scope非global时，node_type和node_id为必填"
            )

        from app.services.prediction.strategy_config_service import (
            get_strategy_config_service,
        )
        service = get_strategy_config_service()

        result = service.update_config(
            scope=request.scope,
            node_type=request.node_type if request.scope != 'global' else None,
            node_id=request.node_id if request.scope != 'global' else None,
            strategy_type=request.strategy_type,
            confidence_threshold=request.confidence_threshold,
            false_positive_threshold=request.false_positive_threshold,
            false_negative_threshold=request.false_negative_threshold,
            description=request.description,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
        )

        if result is None:
            raise HTTPException(status_code=500, detail="策略配置更新失败")

        return StrategyConfigItemResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"策略配置更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/strategy/config/list",
    response_model=StrategyConfigListResponse,
    tags=["配置"],
    summary="列出策略配置（含历史版本）"
)
async def list_strategy_configs(
    scope: Optional[str] = Query(None, description="作用域过滤"),
    node_type: Optional[str] = Query(None, description="节点类型过滤"),
    node_id: Optional[str] = Query(None, description="节点ID过滤"),
    is_active: Optional[bool] = Query(None, description="是否仅当前生效"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
):
    try:
        from app.services.prediction.strategy_config_service import (
            get_strategy_config_service,
        )
        service = get_strategy_config_service()

        items = service.list_configs(
            scope=scope,
            node_type=node_type,
            node_id=node_id,
            is_active=is_active,
            limit=limit,
        )

        return StrategyConfigListResponse(
            total=len(items),
            items=[StrategyConfigItemResponse(**i) for i in items],
        )

    except Exception as e:
        logger.error(f"列出策略配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/strategy/config/rollback",
    response_model=StrategyConfigItemResponse,
    tags=["配置"],
    summary="回滚策略到历史版本"
)
async def rollback_strategy_config(request: StrategyRollbackRequest):
    """
    回滚策略配置到指定版本

    - 回滚基于历史版本创建新版本（版本号自增）
    - 操作记录审计日志
    """
    try:
        from app.services.prediction.strategy_config_service import (
            get_strategy_config_service,
        )
        service = get_strategy_config_service()

        result = service.rollback(
            target_version=request.target_version,
            scope=request.scope,
            node_type=request.node_type,
            node_id=request.node_id,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="回滚目标版本不存在")

        return StrategyConfigItemResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"策略回滚失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/strategy/config/audit",
    response_model=StrategyAuditLogListResponse,
    tags=["配置"],
    summary="查询策略变更审计日志"
)
async def get_strategy_audit_logs(
    scope: Optional[str] = Query(None, description="作用域过滤"),
    node_type: Optional[str] = Query(None, description="节点类型过滤"),
    node_id: Optional[str] = Query(None, description="节点ID过滤"),
    action: Optional[str] = Query(None, description="操作类型过滤: create/update/rollback"),
    operator_id: Optional[str] = Query(None, description="操作人ID过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    try:
        from app.services.prediction.strategy_config_service import (
            get_strategy_config_service,
        )
        service = get_strategy_config_service()

        items = service.get_audit_logs(
            scope=scope,
            node_type=node_type,
            node_id=node_id,
            action=action,
            operator_id=operator_id,
            limit=limit,
            offset=offset,
        )

        return StrategyAuditLogListResponse(
            total=len(items),
            items=[StrategyAuditLogResponse(**i) for i in items],
        )

    except Exception as e:
        logger.error(f"查询策略审计日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/strategy/config/override",
    tags=["配置"],
    summary="删除节点级策略覆盖"
)
async def delete_strategy_override(request: StrategyNodeOverrideDeleteRequest):
    """
    删除节点级策略覆盖，该节点回退到全局策略

    - 仅删除节点级覆盖，不影响全局策略
    - 操作记录审计日志
    """
    try:
        from app.services.prediction.strategy_config_service import (
            get_strategy_config_service,
        )
        service = get_strategy_config_service()

        success = service.delete_node_override(
            node_type=request.node_type,
            node_id=request.node_id,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
        )

        if not success:
            raise HTTPException(status_code=404, detail="未找到该节点的策略覆盖")

        return {"message": f"已删除 {request.node_type}/{request.node_id} 的策略覆盖，回退到全局策略"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除节点策略覆盖失败: {e}")
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


# ---------- 当前用户信息 ----------

@router.get(
    "/tenant/me",
    tags=["多租户"],
    summary="获取当前登录用户信息",
)
async def get_current_tenant_user(
    tenant_context: Dict[str, Any] = Depends(get_tenant_context)
):
    """获取当前登录用户的信息（通过 X-Tenant-Token 或 X-Tenant-API-Key）"""
    if tenant_context["auth_method"] == "none":
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": "未登录或认证凭据无效"},
        )

    try:
        from app.services.tenant import TenantService, TenantUserService
        tenant_svc = TenantService()
        user_svc = TenantUserService()

        tenant = None
        user = None
        display_name = None

        if tenant_context.get("tenant_id"):
            tenant = tenant_svc.get_tenant(tenant_context["tenant_id"])
        if tenant_context.get("user_id") and tenant_context.get("tenant_id"):
            user = user_svc.get_user(tenant_context["tenant_id"], tenant_context["user_id"])
            if user:
                display_name = user.display_name

        result = {
            "tenant_id": tenant_context["tenant_id"],
            "tenant_code": tenant.tenant_code if tenant else None,
            "tenant_name": tenant.tenant_name if tenant else None,
            "user_id": tenant_context.get("user_id"),
            "username": tenant_context.get("username"),
            "display_name": display_name or tenant_context.get("username"),
            "role": tenant_context["role"],
            "permissions": tenant_context.get("permissions", []),
            "auth_method": tenant_context["auth_method"],
            "email": user.email if user else None,
            "phone": user.phone if user else None,
            "org_node_id": user.org_node_id if user else None,
            "status": user.status if user else None,
            "last_login_time": user.last_login_time if user else None,
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/tenant/logout",
    tags=["多租户"],
    summary="租户用户登出",
)
async def tenant_logout(
    request: Request,
    tenant_context: Dict[str, Any] = Depends(get_tenant_context)
):
    """登出，撤销当前登录令牌"""
    if tenant_context["auth_method"] == "token":
        from app.api.auth import _tenant_tokens
        token_header = request.headers.get("X-Tenant-Token") or request.headers.get("x-tenant-token")
        if token_header and token_header in _tenant_tokens:
            revoke_tenant_token(token_header)
    return {"status": "success", "message": "登出成功"}


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


# ============================================================
# 模型管理模块
# ============================================================

def _get_training_monitor():
    from app.core.training_monitor import TrainingMonitor
    return TrainingMonitor()


def _model_version_to_dict(v) -> Dict[str, Any]:
    return {
        'version': v.version,
        'model_id': v.model_id,
        'model_type': v.model_type,
        'created_at': v.created_at,
        'file_path': v.file_path,
        'file_hash': v.file_hash,
        'metrics': v.metrics,
        'config': v.config,
        'is_active': v.is_active,
        'description': v.description,
    }


def _training_session_to_dict(s) -> Dict[str, Any]:
    metrics_history = []
    for m in s.metrics_history:
        if hasattr(m, 'to_dict'):
            metrics_history.append(m.to_dict())
        else:
            metrics_history.append({
                'epoch': m.epoch,
                'train_loss': m.train_loss,
                'val_loss': m.val_loss,
                'train_acc': m.train_acc,
                'val_acc': m.val_acc,
                'learning_rate': m.learning_rate,
                'duration_seconds': m.duration_seconds,
                'timestamp': m.timestamp,
            })
    return {
        'session_id': s.session_id,
        'model_id': s.model_id,
        'model_type': s.model_type,
        'status': s.status.value if hasattr(s.status, 'value') else s.status,
        'start_time': s.start_time,
        'end_time': s.end_time,
        'total_epochs': s.total_epochs,
        'current_epoch': s.current_epoch,
        'best_metrics': s.best_metrics,
        'metrics_history': metrics_history,
        'config': s.config,
        'error_message': s.error_message,
    }


@router.get(
    "/model/versions/{model_type}/{model_id}",
    response_model=ModelVersionListResponse,
    tags=["模型管理"],
    summary="获取模型版本列表"
)
async def get_model_versions(model_type: str, model_id: str):
    """获取指定模型的所有版本列表"""
    try:
        version_manager = _get_version_manager()
        versions = version_manager.get_all_versions(model_id)

        if not versions:
            return {
                'model_id': model_id,
                'model_type': model_type,
                'versions': []
            }

        version_dicts = [_model_version_to_dict(v) for v in reversed(versions)]

        return {
            'model_id': model_id,
            'model_type': model_type,
            'versions': version_dicts,
        }
    except Exception as e:
        logger.error(f"获取模型版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/versions/{model_type}/{model_id}/active",
    response_model=ModelVersionSchema,
    tags=["模型管理"],
    summary="获取当前活动版本"
)
async def get_active_model_version(model_type: str, model_id: str):
    """获取当前激活的模型版本"""
    try:
        version_manager = _get_version_manager()
        active_version = version_manager.get_version(model_id)

        if active_version is None:
            raise HTTPException(status_code=404, detail="未找到活动版本")

        return _model_version_to_dict(active_version)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取活动版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/versions/{model_type}/{model_id}/activate",
    response_model=ModelVersionSchema,
    tags=["模型管理"],
    summary="激活/回滚模型版本"
)
async def activate_model_version(
    model_type: str,
    model_id: str,
    request: ModelVersionActivateRequest
):
    """激活指定版本（用于回滚或切换版本）"""
    try:
        version_manager = _get_version_manager()

        target_version = version_manager.get_version(model_id, request.version)
        if target_version is None:
            raise HTTPException(status_code=404, detail="版本不存在")

        result = version_manager.rollback(model_id, request.version)
        if result is None:
            raise HTTPException(status_code=500, detail="版本激活失败")

        return _model_version_to_dict(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/model/versions/{model_type}/{model_id}/compare",
    response_model=ModelVersionCompareResponse,
    tags=["模型管理"],
    summary="对比两个模型版本"
)
async def compare_model_versions(
    model_type: str,
    model_id: str,
    request: ModelVersionCompareRequest
):
    """对比两个模型版本的指标差异"""
    try:
        version_manager = _get_version_manager()

        result = version_manager.compare_versions(
            model_id,
            request.version1,
            request.version2
        )

        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"版本对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/model/versions/{model_type}/{model_id}/{version}",
    tags=["模型管理"],
    summary="删除模型版本"
)
async def delete_model_version(model_type: str, model_id: str, version: str):
    """删除指定的模型版本（不能删除活动版本）"""
    try:
        version_manager = _get_version_manager()

        success = version_manager.delete_version(model_id, version)
        if not success:
            raise HTTPException(status_code=400, detail="删除失败，可能是活动版本或版本不存在")

        return {
            'success': True,
            'message': f'版本 {version} 已删除',
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除版本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/training/status",
    response_model=TrainingStatusResponse,
    tags=["模型管理"],
    summary="获取训练状态"
)
async def get_training_status():
    """获取当前训练状态和最近的训练会话"""
    try:
        monitor = _get_training_monitor()
        recent_sessions = monitor.get_recent_sessions(10)

        current_session = None
        is_training = False

        if monitor.current_session is not None:
            current_session = _training_session_to_dict(monitor.current_session)
            is_training = True

        session_dicts = [
            _training_session_to_dict(s) for s in recent_sessions
        ]

        return {
            'is_training': is_training,
            'current_session': current_session,
            'recent_sessions': session_dicts,
        }
    except Exception as e:
        logger.error(f"获取训练状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/training/sessions",
    response_model=TrainingSessionListResponse,
    tags=["模型管理"],
    summary="获取训练会话列表"
)
async def list_training_sessions(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
):
    """获取历史训练会话列表"""
    try:
        monitor = _get_training_monitor()
        sessions = monitor.get_recent_sessions(limit)

        session_dicts = [
            _training_session_to_dict(s) for s in sessions
        ]

        return {
            'total': len(session_dicts),
            'items': session_dicts,
        }
    except Exception as e:
        logger.error(f"获取训练会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/training/sessions/{session_id}",
    response_model=TrainingSessionSchema,
    tags=["模型管理"],
    summary="获取训练会话详情"
)
async def get_training_session(session_id: str):
    """获取指定训练会话的详细信息，包含训练曲线数据"""
    try:
        monitor = _get_training_monitor()
        session = monitor.load_session(session_id)

        if session is None:
            raise HTTPException(status_code=404, detail="训练会话不存在")

        return _training_session_to_dict(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取训练会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model/list",
    tags=["模型管理"],
    summary="获取所有模型列表"
)
async def list_all_models():
    """获取系统中所有的模型列表"""
    try:
        version_manager = _get_version_manager()

        models = []
        for model_id, versions in version_manager._versions.items():
            if versions:
                active_version = None
                for v in versions:
                    if v.is_active:
                        active_version = v.version
                        break

                latest = versions[-1]
                models.append({
                    'model_id': model_id,
                    'model_type': latest.model_type,
                    'version_count': len(versions),
                    'active_version': active_version,
                    'latest_version': latest.version,
                    'latest_metrics': latest.metrics,
                    'last_updated': latest.created_at,
                })

        return {
            'total': len(models),
            'models': models,
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 配置中心 ====================

def _get_config_manager():
    from app.core.config_manager import ConfigManager
    return ConfigManager()


def _get_scheduler():
    from app.schedulers.scheduler import scheduler
    return scheduler


@router.get(
    "/config/center",
    response_model=ConfigCenterResponse,
    tags=["配置中心"],
    summary="获取所有配置中心数据"
)
async def get_config_center():
    """获取预警策略、阈值、调度任务的所有配置"""
    try:
        cm = _get_config_manager()
        sched = _get_scheduler()

        # 预警策略配置
        strategy_type = cm.get('warning_strategy.strategy_type', 1)
        warning_strategy = {
            'strategy_type': strategy_type,
            'strategy_1_confidence_threshold': cm.get(
                'warning_strategy.strategy_1.confidence_threshold', 0.7
            ),
            'strategy_1_false_positive_threshold': cm.get(
                'warning_strategy.strategy_1.false_positive_threshold', 0.05
            ),
            'strategy_2_confidence_threshold': cm.get(
                'warning_strategy.strategy_2.confidence_threshold', 0.95
            ),
            'strategy_2_false_negative_threshold': cm.get(
                'warning_strategy.strategy_2.false_negative_threshold', 0.10
            ),
        }

        # 阈值配置
        thresholds = {
            'high_risk_threshold': cm.get('risk_assessment.high_risk_threshold', 3),
            'medium_risk_threshold': cm.get('risk_assessment.medium_risk_threshold', 7),
            'min_normal_preload': cm.get('risk_assessment.preload_thresholds.min_normal', 400),
            'max_normal_preload': cm.get('risk_assessment.preload_thresholds.max_normal', 800),
            'warning_deviation': cm.get('risk_assessment.preload_thresholds.warning_deviation', 0.1),
            'critical_deviation': cm.get('risk_assessment.preload_thresholds.critical_deviation', 0.2),
            'auto_create_work_order_level': cm.get('alert.auto_create_work_order_level', 3),
            'default_upgrade_minutes': cm.get('alert.default_upgrade_minutes', 30),
        }

        # 调度任务
        scheduled_jobs = []
        job_keys = [
            ('training_job', '模型训练任务'),
            ('prediction_job', '预测任务'),
            ('monthly_prediction_job', '月度预测任务'),
            ('alert_upgrade_job', '告警自动升级任务'),
            ('audit_cleanup_job', '审计过期记录清理任务'),
        ]
        for job_id, job_name in job_keys:
            job_cron = cm.get(f'scheduler.{job_id}.cron', '')
            job_enabled = cm.get(f'scheduler.{job_id}.enabled', True)
            next_run = None
            try:
                if sched.is_running:
                    jobs = sched.get_jobs()
                    for j in jobs:
                        if j['id'] == job_id:
                            next_run = j['next_run']
                            break
            except Exception:
                pass
            scheduled_jobs.append({
                'id': job_id,
                'name': job_name,
                'enabled': job_enabled,
                'cron': job_cron,
                'next_run': next_run,
                'description': job_name,
            })

        return {
            'warning_strategy': warning_strategy,
            'thresholds': thresholds,
            'scheduled_jobs': scheduled_jobs,
            'updated_at': datetime.now(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置中心数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/config/warning-strategy",
    response_model=WarningStrategyConfigSchema,
    tags=["配置中心"],
    summary="更新预警策略配置"
)
async def update_warning_strategy(request: WarningStrategyConfigSchema):
    """更新预警策略配置（策略类型、阈值等）"""
    try:
        cm = _get_config_manager()

        updates = {
            'warning_strategy.strategy_type': request.strategy_type,
            'warning_strategy.strategy_1.confidence_threshold':
                request.strategy_1_confidence_threshold,
            'warning_strategy.strategy_1.false_positive_threshold':
                request.strategy_1_false_positive_threshold,
            'warning_strategy.strategy_2.confidence_threshold':
                request.strategy_2_confidence_threshold,
            'warning_strategy.strategy_2.false_negative_threshold':
                request.strategy_2_false_negative_threshold,
        }
        cm.batch_update(updates)
        cm.save()

        return request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新预警策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/config/thresholds",
    response_model=ThresholdConfigSchema,
    tags=["配置中心"],
    summary="更新阈值配置"
)
async def update_thresholds(request: ThresholdConfigSchema):
    """更新风险阈值、预紧力阈值、偏差比例等"""
    try:
        cm = _get_config_manager()

        updates = {
            'risk_assessment.high_risk_threshold': request.high_risk_threshold,
            'risk_assessment.medium_risk_threshold': request.medium_risk_threshold,
            'risk_assessment.preload_thresholds.min_normal': request.min_normal_preload,
            'risk_assessment.preload_thresholds.max_normal': request.max_normal_preload,
            'risk_assessment.preload_thresholds.warning_deviation': request.warning_deviation,
            'risk_assessment.preload_thresholds.critical_deviation': request.critical_deviation,
            'alert.auto_create_work_order_level': request.auto_create_work_order_level,
            'alert.default_upgrade_minutes': request.default_upgrade_minutes,
        }
        cm.batch_update(updates)
        cm.save()

        return request
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新阈值配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/config/scheduler/jobs",
    response_model=List[ScheduledJobSchema],
    tags=["配置中心"],
    summary="获取调度任务列表"
)
async def list_scheduler_jobs():
    """获取所有调度任务的配置和运行状态"""
    try:
        cm = _get_config_manager()
        sched = _get_scheduler()

        job_keys = [
            ('training_job', '模型训练任务'),
            ('prediction_job', '预测任务'),
            ('monthly_prediction_job', '月度预测任务'),
            ('alert_upgrade_job', '告警自动升级任务'),
            ('audit_cleanup_job', '审计过期记录清理任务'),
        ]
        jobs = []
        for job_id, job_name in job_keys:
            job_cron = cm.get(f'scheduler.{job_id}.cron', '')
            job_enabled = cm.get(f'scheduler.{job_id}.enabled', True)
            next_run = None
            try:
                if sched.is_running:
                    sched_jobs = sched.get_jobs()
                    for j in sched_jobs:
                        if j['id'] == job_id:
                            next_run = j['next_run']
                            break
            except Exception:
                pass
            jobs.append({
                'id': job_id,
                'name': job_name,
                'enabled': job_enabled,
                'cron': job_cron,
                'next_run': next_run,
                'description': job_name,
            })

        return jobs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取调度任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/config/scheduler/jobs/{job_id}",
    response_model=ScheduledJobSchema,
    tags=["配置中心"],
    summary="更新调度任务配置"
)
async def update_scheduler_job(job_id: str, request: SchedulerJobUpdateRequest):
    """更新指定任务的 Cron 表达式或启用/禁用状态"""
    try:
        cm = _get_config_manager()
        sched = _get_scheduler()

        valid_jobs = [
            'training_job', 'prediction_job', 'monthly_prediction_job',
            'alert_upgrade_job', 'audit_cleanup_job'
        ]
        if job_id not in valid_jobs:
            raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

        job_names = {
            'training_job': '模型训练任务',
            'prediction_job': '预测任务',
            'monthly_prediction_job': '月度预测任务',
            'alert_upgrade_job': '告警自动升级任务',
            'audit_cleanup_job': '审计过期记录清理任务',
        }

        if request.cron is not None:
            cm.set(f'scheduler.{job_id}.cron', request.cron, validate=False)
            try:
                if sched.is_running:
                    sched.update_job_cron(job_id, request.cron)
            except Exception as cron_err:
                logger.warning(f"更新运行中调度器失败: {cron_err}")

        if request.enabled is not None:
            cm.set(f'scheduler.{job_id}.enabled', request.enabled, validate=False)
            try:
                if sched.is_running:
                    if request.enabled:
                        sched.enable_job(job_id)
                    else:
                        sched.disable_job(job_id)
            except Exception as enable_err:
                logger.warning(f"更新运行中调度器状态失败: {enable_err}")

        cm.save()

        job_cron = cm.get(f'scheduler.{job_id}.cron', '')
        job_enabled = cm.get(f'scheduler.{job_id}.enabled', True)
        next_run = None
        try:
            if sched.is_running:
                sched_jobs = sched.get_jobs()
                for j in sched_jobs:
                    if j['id'] == job_id:
                        next_run = j['next_run']
                        break
        except Exception:
            pass

        return {
            'id': job_id,
            'name': job_names[job_id],
            'enabled': job_enabled,
            'cron': job_cron,
            'next_run': next_run,
            'description': job_names[job_id],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新调度任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/config/scheduler/jobs/{job_id}/trigger",
    tags=["配置中心"],
    summary="手动触发调度任务"
)
async def trigger_scheduler_job(job_id: str):
    """立即执行指定的调度任务"""
    try:
        valid_jobs = [
            'training_job', 'prediction_job', 'monthly_prediction_job',
            'alert_upgrade_job', 'audit_cleanup_job'
        ]
        if job_id not in valid_jobs:
            raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

        sched = _get_scheduler()
        if not sched.is_running:
            raise HTTPException(status_code=503, detail="调度器未启动")

        success = sched.run_job_now(job_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"任务 {job_id} 未在调度器中注册")

        return {
            'job_id': job_id,
            'status': 'triggered',
            'message': f'任务 {job_id} 已触发执行',
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发调度任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 调度器扩展API ----------

_job_execution_service = JobExecutionService()


@router.post(
    "/scheduler/trigger/{job_name}",
    tags=["调度器"],
    summary="手动触发调度任务（按任务名称）",
    response_model=SchedulerTriggerResponse,
)
async def trigger_scheduler_job_by_name(
    job_name: str,
    background_tasks: BackgroundTasks,
    require_leader: bool = Query(False, description="是否需要Leader节点才能执行"),
    num_shards: Optional[int] = Query(None, ge=1, le=32, description="分片数（仅适用于支持分片的任务）"),
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """
    按任务名称手动触发调度任务。

    支持的任务名称:
    - training_job: 模型训练
    - prediction_job: 预测任务（支持分片）
    - monthly_prediction_job: 月度预测
    - alert_upgrade_job: 告警升级
    - audit_cleanup_job: 审计清理

    Args:
        job_name: 任务名称
        require_leader: 是否需要Leader节点才能执行
        num_shards: 分片数（仅适用于prediction_job）
    """
    try:
        valid_jobs = [
            'training_job', 'prediction_job', 'monthly_prediction_job',
            'alert_upgrade_job', 'audit_cleanup_job'
        ]
        if job_name not in valid_jobs:
            raise HTTPException(
                status_code=404,
                detail=f"任务 {job_name} 不存在，支持的任务: {', '.join(valid_jobs)}"
            )

        leader_election = get_leader_election()
        is_leader = None

        if require_leader:
            acquired = leader_election.try_acquire_leadership(job_name)
            if not acquired:
                leader_info = leader_election.get_leader_info(job_name)
                current_leader = leader_info.get('leader_id') if leader_info else 'unknown'
                return SchedulerTriggerResponse(
                    job_name=job_name,
                    status='skipped',
                    message=f'当前实例不是Leader，Leader节点: {current_leader}',
                    is_leader=False,
                )
            is_leader = True

        sched = _get_scheduler()
        if not sched.is_running:
            if require_leader and is_leader:
                leader_election.release_leadership(job_name)
            raise HTTPException(status_code=503, detail="调度器未启动")

        job_type_map = {
            'training_job': 'training',
            'prediction_job': 'prediction',
            'monthly_prediction_job': 'prediction',
            'alert_upgrade_job': 'alert',
            'audit_cleanup_job': 'maintenance',
        }
        job_type = job_type_map.get(job_name, 'other')

        log_id = None
        try:
            log_id = _job_execution_service.start_execution(
                job_name=job_name,
                job_type=job_type,
                trigger_type='manual',
                shard_index=0 if job_name == 'prediction_job' and num_shards else None,
                shard_total=num_shards,
            )
        except Exception as log_err:
            logger.warning(f"创建任务执行日志失败: {log_err}")

        success = sched.run_job_now(job_name, num_shards=num_shards, log_id=log_id)
        if not success:
            if log_id:
                _job_execution_service.skip_execution(log_id, reason='任务调度失败')
            if require_leader and is_leader:
                leader_election.release_leadership(job_name)
            raise HTTPException(status_code=404, detail=f"任务 {job_name} 未在调度器中注册")

        return SchedulerTriggerResponse(
            job_name=job_name,
            status='triggered',
            message=f'任务 {job_name} 已触发执行',
            log_id=log_id,
            is_leader=is_leader,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发调度任务失败 [{job_name}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scheduler/logs",
    tags=["调度器"],
    summary="查询任务执行日志列表",
    response_model=JobExecutionLogListResponse,
)
async def get_job_execution_logs(
    job_name: Optional[str] = Query(None, description="按任务名称过滤"),
    job_type: Optional[str] = Query(None, description="按任务类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    trigger_type: Optional[str] = Query(None, description="按触发类型过滤"),
    start_time_from: Optional[datetime] = Query(None, description="开始时间起始"),
    start_time_to: Optional[datetime] = Query(None, description="开始时间结束"),
    instance_id: Optional[str] = Query(None, description="按实例ID过滤"),
    has_errors: Optional[bool] = Query(None, description="是否仅显示有错误的"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页大小"),
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """查询任务执行日志列表"""
    try:
        logs, total = _job_execution_service.repository.get_recent_logs(
            job_name=job_name,
            job_type=job_type,
            status=status,
            trigger_type=trigger_type,
            start_time_from=start_time_from,
            start_time_to=start_time_to,
            instance_id=instance_id,
            has_errors=has_errors,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        for log in logs:
            if 'error_summary' in log and log['error_summary']:
                try:
                    log['error_summary'] = json.loads(log['error_summary'])
                except (json.JSONDecodeError, TypeError):
                    pass
            if 'error_details' in log and log['error_details']:
                try:
                    log['error_details'] = json.loads(log['error_details'])
                except (json.JSONDecodeError, TypeError):
                    pass

        return JobExecutionLogListResponse(
            total=total,
            items=[JobExecutionLogSchema(**log) for log in logs],
        )
    except Exception as e:
        logger.error(f"查询任务执行日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scheduler/logs/{log_id}",
    tags=["调度器"],
    summary="获取任务执行日志详情",
    response_model=JobExecutionLogSchema,
)
async def get_job_execution_log_detail(
    log_id: int,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """获取单条任务执行日志详情"""
    try:
        log = _job_execution_service.repository.get_log_by_id(log_id)
        if not log:
            raise HTTPException(status_code=404, detail=f"日志ID {log_id} 不存在")

        if 'error_summary' in log and log['error_summary']:
            try:
                log['error_summary'] = json.loads(log['error_summary'])
            except (json.JSONDecodeError, TypeError):
                pass
        if 'error_details' in log and log['error_details']:
            try:
                log['error_details'] = json.loads(log['error_details'])
            except (json.JSONDecodeError, TypeError):
                pass

        return JobExecutionLogSchema(**log)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务执行日志详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scheduler/leader/{job_key}",
    tags=["调度器"],
    summary="获取Leader选举状态",
    response_model=LeaderStatusSchema,
)
async def get_leader_status(
    job_key: str,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """获取指定任务的Leader选举状态"""
    try:
        leader_election = get_leader_election()
        leader_info = leader_election.get_leader_info(job_key)

        if not leader_info:
            raise HTTPException(
                status_code=404,
                detail=f"任务 {job_key} 暂无Leader记录"
            )

        now = datetime.now()
        lease_expire = leader_info.get('lease_expire_time', now)
        is_expired = lease_expire < now
        is_current_instance = leader_info.get('leader_id') == get_instance_id()

        return LeaderStatusSchema(
            leader_key=job_key,
            leader_id=leader_info.get('leader_id', ''),
            lease_expire_time=lease_expire,
            last_heartbeat=leader_info.get('last_heartbeat', now),
            version=leader_info.get('version', 0),
            is_expired=is_expired,
            is_current_instance=is_current_instance,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Leader状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 异常检测增强与闭环
# ============================================================

_anomaly_service = None


def _get_anomaly_service():
    """获取异常服务实例"""
    global _anomaly_service
    if _anomaly_service is None:
        from app.services.anomaly_service import get_anomaly_service
        _anomaly_service = get_anomaly_service()
    return _anomaly_service


@router.post(
    "/anomaly/query",
    response_model=AnomalyListResponse,
    tags=["异常管理"],
    summary="查询异常数据"
)
async def query_anomalies(
    request: AnomalyQueryRequest,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """
    查询异常数据，支持多维度过滤：
    - sensor_id: 传感器/螺栓ID
    - 时间范围: start_time ~ end_time
    - anomaly_type: 异常类型
    - classification: 异常分类
    - is_confirmed: 是否已确认
    - is_false_positive: 是否为误报
    - 异常评分范围
    """
    try:
        service = _get_anomaly_service()
        total, anomalies = service.query_anomalies(
            sensor_id=request.sensor_id,
            start_time=request.start_time,
            end_time=request.end_time,
            anomaly_type=request.anomaly_type,
            classification=request.classification,
            is_confirmed=request.is_confirmed,
            is_false_positive=request.is_false_positive,
            min_score=request.min_score,
            max_score=request.max_score,
            limit=request.limit,
            offset=request.offset,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )

        items = [
            AnomalyDataResponse(**a)
            for a in anomalies
        ]

        return AnomalyListResponse(total=total, items=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询异常数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/anomaly/{anomaly_id}",
    response_model=AnomalyDataResponse,
    tags=["异常管理"],
    summary="获取异常详情"
)
async def get_anomaly_detail(
    anomaly_id: int,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """根据ID获取单条异常记录详情"""
    try:
        service = _get_anomaly_service()
        anomaly = service.get_anomaly_by_id(anomaly_id)
        if not anomaly:
            raise HTTPException(status_code=404, detail="异常记录不存在")
        return AnomalyDataResponse(**anomaly)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取异常详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/anomaly/confirm",
    response_model=AnomalyDataResponse,
    tags=["异常管理"],
    summary="确认异常（真实异常）"
)
async def confirm_anomaly(
    request: AnomalyConfirmRequest,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """
    确认异常为真实异常。
    标记 is_confirmed=True, is_false_positive=False。
    """
    try:
        service = _get_anomaly_service()
        result = service.confirm_anomaly(
            anomaly_id=request.anomaly_id,
            confirmed_by=request.confirmed_by,
            confirm_note=request.confirm_note,
        )
        if not result:
            raise HTTPException(status_code=404, detail="异常记录不存在")
        return AnomalyDataResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认异常失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/anomaly/false-positive",
    response_model=AnomalyDataResponse,
    tags=["异常管理"],
    summary="标注异常为误报"
)
async def mark_anomaly_false_positive(
    request: AnomalyFalsePositiveRequest,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """
    标注异常为误报。
    标记 is_confirmed=True, is_false_positive=True。
    """
    try:
        service = _get_anomaly_service()
        result = service.mark_false_positive(
            anomaly_id=request.anomaly_id,
            confirmed_by=request.confirmed_by,
            confirm_note=request.confirm_note,
        )
        if not result:
            raise HTTPException(status_code=404, detail="异常记录不存在")
        return AnomalyDataResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标注误报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/anomaly/batch-confirm",
    response_model=AnomalyBatchResultResponse,
    tags=["异常管理"],
    summary="批量确认异常"
)
async def batch_confirm_anomalies(
    request: AnomalyBatchConfirmRequest,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """批量确认异常为真实异常"""
    try:
        service = _get_anomaly_service()
        result = service.batch_confirm_anomalies(
            anomaly_ids=request.anomaly_ids,
            confirmed_by=request.confirmed_by,
            confirm_note=request.confirm_note,
        )
        return AnomalyBatchResultResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量确认异常失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/anomaly/batch-false-positive",
    response_model=AnomalyBatchResultResponse,
    tags=["异常管理"],
    summary="批量标注误报"
)
async def batch_mark_false_positives(
    request: AnomalyBatchFalsePositiveRequest,
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """批量标注异常为误报"""
    try:
        service = _get_anomaly_service()
        result = service.batch_mark_false_positives(
            anomaly_ids=request.anomaly_ids,
            confirmed_by=request.confirmed_by,
            confirm_note=request.confirm_note,
        )
        return AnomalyBatchResultResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量标注误报失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/anomaly/statistics/summary",
    response_model=AnomalyStatisticsResponse,
    tags=["异常管理"],
    summary="获取异常统计信息"
)
async def get_anomaly_statistics(
    sensor_id: Optional[str] = Query(None, description="传感器ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """
    获取异常统计信息：
    - 异常总数
    - 已确认/未确认数
    - 误报数/真实异常数
    - 误报率
    - 按类型分布
    - 按分类分布
    """
    try:
        service = _get_anomaly_service()
        stats = service.get_anomaly_statistics(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time,
        )
        return AnomalyStatisticsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取异常统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/anomaly/warning-impact/{sensor_id}",
    response_model=AnomalyWarningImpactResponse,
    tags=["异常管理"],
    summary="检查异常对预警等级的影响"
)
async def check_anomaly_warning_impact(
    sensor_id: str,
    current_level: int = Query(1, ge=1, le=4, description="当前预警等级 1-4"),
    _: Dict[str, Any] = Depends(get_tenant_context),
):
    """
    检查同一时段异常数是否超过阈值，决定是否需要提升预警等级。

    - 统计指定时间窗口内的异常数量
    - 与配置的阈值比较
    - 返回是否需要提升预警等级
    """
    try:
        service = _get_anomaly_service()
        impact = service.check_anomaly_impact_on_warning(
            sensor_id=sensor_id,
            current_warning_level=current_level,
        )
        return AnomalyWarningImpactResponse(**impact)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查异常对预警影响失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== API密钥管理 ====================

@router.post(
    "/auth/keys",
    response_model=APIKeyCreateResponse,
    tags=["API密钥管理"],
    summary="创建API密钥",
    dependencies=[Depends(require_permission("admin"))],
)
async def create_api_key(request: APIKeyCreateRequest):
    try:
        key, key_id = api_key_manager.add_key(
            name=request.name,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            expires_hours=request.expires_hours,
        )
        key_info = api_key_manager._key_info[key_id]
        return APIKeyCreateResponse(
            key=key,
            key_id=key_id,
            name=request.name,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            expires_at=key_info.get("expires_at"),
            created_at=str(key_info.get("created_at", "")),
        )
    except Exception as e:
        logger.error(f"创建API密钥失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/auth/keys",
    response_model=APIKeyListResponse,
    tags=["API密钥管理"],
    summary="列出所有API密钥",
    dependencies=[Depends(require_permission("admin"))],
)
async def list_api_keys():
    try:
        keys = api_key_manager.list_keys()
        items = []
        for k in keys:
            items.append(APIKeyInfoResponse(
                key_id=k["key_id"],
                key_preview=k["key_preview"],
                name=k["name"],
                permissions=k["permissions"],
                rate_limit=k["rate_limit"],
                is_expired=k.get("is_expired", False),
                expires_at=k.get("expires_at"),
                created_at=str(k.get("created_at", "")),
            ))
        return APIKeyListResponse(total=len(items), items=items)
    except Exception as e:
        logger.error(f"列出API密钥失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/auth/keys/{key_id}/rotate",
    response_model=APIKeyRotateResponse,
    tags=["API密钥管理"],
    summary="轮换API密钥",
    dependencies=[Depends(require_permission("admin"))],
)
async def rotate_api_key(key_id: str):
    try:
        result = api_key_manager.rotate_key(key_id)
        if not result:
            raise HTTPException(status_code=404, detail="密钥不存在")
        return APIKeyRotateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"轮换API密钥失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/auth/keys/{key_id}",
    response_model=APIKeyRevokeResponse,
    tags=["API密钥管理"],
    summary="吊销API密钥",
    dependencies=[Depends(require_permission("admin"))],
)
async def revoke_api_key(key_id: str):
    try:
        success = api_key_manager.revoke_key(key_id)
        if not success:
            raise HTTPException(status_code=404, detail="密钥不存在")
        return APIKeyRevokeResponse(key_id=key_id, revoked=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"吊销API密钥失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/auth/keys/{key_id}/rate-limit",
    response_model=RateLimitStatusResponse,
    tags=["API密钥管理"],
    summary="查询密钥限流状态",
    dependencies=[Depends(require_permission("admin"))],
)
async def get_rate_limit_status(key_id: str):
    try:
        limit = api_key_manager.get_key_rate_limit(key_id)
        if limit is None:
            raise HTTPException(status_code=404, detail="密钥不存在")
        status = per_key_rate_limiter.get_status(key_id, limit)
        return RateLimitStatusResponse(
            key_id=key_id,
            limit=limit,
            remaining=status["remaining"],
            used=status["used"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询限流状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== API审计日志 ====================

@router.get(
    "/auth/audit-logs",
    response_model=APIAuditLogListResponse,
    tags=["API审计日志"],
    summary="查询API审计日志",
    dependencies=[Depends(require_permission("admin"))],
)
async def query_audit_logs(
    key_id: Optional[str] = Query(None, description="按密钥ID过滤"),
    path: Optional[str] = Query(None, description="按路径过滤"),
    method: Optional[str] = Query(None, description="按HTTP方法过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    try:
        audit_logger.flush()
        logs, total = audit_logger.query_logs(
            key_id=key_id,
            path=path,
            method=method,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        items = []
        for log in logs:
            extra = {}
            if hasattr(log, "extra_info") and log.extra_info:
                import json
                try:
                    extra = json.loads(log.extra_info)
                except Exception:
                    extra = {}
            items.append(APIAuditLogResponse(
                id=log.id,
                key_id=log.key_id or "",
                key_name=log.key_name or "",
                method=log.method or "",
                path=log.path or "",
                status_code=log.status_code or 0,
                client_ip=log.client_ip or "",
                request_id=log.request_id or "",
                extra_info=extra,
                create_time=log.create_time,
            ))
        return APIAuditLogListResponse(total=total, items=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询审计日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LLM 智能诊断报告 ====================

_diagnosis_report_service = None


def _get_diagnosis_report_service():
    """获取诊断报告服务实例"""
    global _diagnosis_report_service
    if _diagnosis_report_service is None:
        from app.services.report import get_diagnosis_report_service
        _diagnosis_report_service = get_diagnosis_report_service()
    return _diagnosis_report_service


@router.post(
    "/report/diagnosis",
    response_model=DiagnosisReportResponse,
    tags=["LLM智能诊断"],
    summary="生成单次诊断报告"
)
async def generate_diagnosis_report(request: DiagnosisReportRequest):
    """
    生成单次诊断报告（可选调用 LLM）

    输入结构化数据，输出诊断摘要、推荐措施和紧急程度。
    LLM 不可用时自动降级到模板生成。
    """
    try:
        service = _get_diagnosis_report_service()

        report = await service.generate_single_report_async(
            status=request.status,
            risk_score=request.risk_score,
            node_type=request.node_type,
            node_id=request.node_id or "",
            fault_type=request.fault_type,
            trend=request.trend,
            recent_values=request.recent_values,
            historical_incidents=request.historical_incidents,
        )

        return DiagnosisReportResponse(
            diagnosis_summary=report.diagnosis_summary,
            recommended_actions=report.recommended_actions,
            urgency_level=report.urgency_level.value if hasattr(report.urgency_level, 'value') else report.urgency_level,
            model=report.model,
            tokens_used=report.tokens_used,
            latency_ms=report.latency_ms,
            is_fallback=report.is_fallback,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成诊断报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/report/generate",
    response_model=PeriodicReportResponse,
    tags=["LLM智能诊断"],
    summary="生成周期报告（周报/月报）"
)
async def generate_periodic_report(request: ReportGenerateRequest):
    """
    按 bolt_id/flange_id 聚合近期预测生成周报/月报

    - report_type: weekly（周报）/ monthly（月报）
    - use_llm: 是否使用 LLM 生成（默认 True，不可用时自动降级）
    """
    try:
        service = _get_diagnosis_report_service()

        report = await service.generate_periodic_report_async(
            node_type=request.node_type,
            node_id=request.node_id,
            report_type=request.report_type,
            use_llm=request.use_llm if request.use_llm is not None else True,
        )

        return PeriodicReportResponse(
            report_type=report.report_type.value if hasattr(report.report_type, 'value') else report.report_type,
            node_id=report.node_id,
            node_type=report.node_type,
            period_start=report.period_start,
            period_end=report.period_end,
            diagnosis_summary=report.diagnosis_summary,
            recommended_actions=report.recommended_actions,
            urgency_level=report.urgency_level.value if hasattr(report.urgency_level, 'value') else report.urgency_level,
            statistics=ReportStatisticsSchema(
                prediction_count=report.statistics.prediction_count,
                avg_risk_score=report.statistics.avg_risk_score,
                min_risk_score=report.statistics.min_risk_score,
                max_risk_score=report.statistics.max_risk_score,
                status_distribution=report.statistics.status_distribution,
                trend=report.statistics.trend,
                max_status=report.statistics.max_status,
                fault_types=report.statistics.fault_types,
            ),
            generated_at=report.generated_at,
            model=report.model,
            is_fallback=report.is_fallback,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成周期报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/report/batch-generate",
    response_model=BatchReportResponse,
    tags=["LLM智能诊断"],
    summary="批量生成周期报告"
)
async def batch_generate_periodic_reports(request: BatchReportGenerateRequest):
    """
    批量生成多个节点的周期报告（周报/月报）
    """
    try:
        service = _get_diagnosis_report_service()

        results = []
        errors = {}
        success_count = 0
        failed_count = 0

        for node_id in request.node_ids:
            try:
                report = await service.generate_periodic_report_async(
                    node_type=request.node_type,
                    node_id=node_id,
                    report_type=request.report_type,
                    use_llm=True,
                )

                results.append(PeriodicReportResponse(
                    report_type=report.report_type.value if hasattr(report.report_type, 'value') else report.report_type,
                    node_id=report.node_id,
                    node_type=report.node_type,
                    period_start=report.period_start,
                    period_end=report.period_end,
                    diagnosis_summary=report.diagnosis_summary,
                    recommended_actions=report.recommended_actions,
                    urgency_level=report.urgency_level.value if hasattr(report.urgency_level, 'value') else report.urgency_level,
                    statistics=ReportStatisticsSchema(
                        prediction_count=report.statistics.prediction_count,
                        avg_risk_score=report.statistics.avg_risk_score,
                        min_risk_score=report.statistics.min_risk_score,
                        max_risk_score=report.statistics.max_risk_score,
                        status_distribution=report.statistics.status_distribution,
                        trend=report.statistics.trend,
                        max_status=report.statistics.max_status,
                        fault_types=report.statistics.fault_types,
                    ),
                    generated_at=report.generated_at,
                    model=report.model,
                    is_fallback=report.is_fallback,
                ))
                success_count += 1
            except Exception as e:
                errors[node_id] = str(e)
                failed_count += 1

        return BatchReportResponse(
            total=len(request.node_ids),
            success=success_count,
            failed=failed_count,
            results=results,
            errors=errors,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/report/config",
    tags=["LLM智能诊断"],
    summary="获取 LLM 配置状态"
)
async def get_llm_config_status():
    """
    获取 LLM 配置状态，包括是否启用、当前 provider、支持的功能等
    """
    try:
        from app.core.llm_client import LLMClient

        llm_client = LLMClient()

        return {
            "enabled": llm_client.is_enabled(),
            "provider": llm_client.provider,
            "supported_providers": list(llm_client._clients.keys()),
            "fallback_available": "local" in llm_client._clients,
            "message": "LLM 诊断功能已启用" if llm_client.is_enabled() else "LLM 诊断功能已禁用，将使用模板降级",
        }
    except Exception as e:
        logger.error(f"获取 LLM 配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 碳排与能效关联分析 ====================

_carbon_energy_service = None


def get_carbon_energy_service():
    """获取碳排与能效分析服务实例"""
    global _carbon_energy_service
    if _carbon_energy_service is None:
        from app.services.carbon_energy_service import CarbonEnergyService
        _carbon_energy_service = CarbonEnergyService()
    return _carbon_energy_service


@router.post(
    "/carbon/ranking/monthly",
    response_model=CarbonMonthlyRankingResponse,
    tags=["碳排与能效分析"],
    summary="装置级月度碳排风险贡献排行"
)
async def get_carbon_monthly_ranking(request: CarbonMonthlyRankingRequest):
    """
    生成装置级月度碳排风险贡献排行

    基于预紧力劣化、估算泄漏率、能耗/碳排增量简化模型，
    对各装置进行碳排风险评分与优先级排序。

    不强制精确计量，强调趋势与优先级。
    """
    try:
        service = get_carbon_energy_service()
        result = service.generate_monthly_ranking(
            nodes_data=request.nodes,
            top_n=request.top_n,
        )

        ranked_items = [
            CarbonRiskItemSchema(**item) for item in result['ranked_items']
        ]

        return CarbonMonthlyRankingResponse(
            report_month=result['report_month'],
            total_nodes=result['total_nodes'],
            total_monthly_carbon_increment_kg=result['total_monthly_carbon_increment_kg'],
            total_monthly_leakage_volume_m3=result['total_monthly_leakage_volume_m3'],
            risk_distribution=result['risk_distribution'],
            ranked_items=ranked_items,
            generated_at=result['generated_at'],
        )
    except Exception as e:
        logger.error(f"生成月度碳排风险排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/carbon/hi-dual-view",
    response_model=HICarbonDualViewResponse,
    tags=["碳排与能效分析"],
    summary="HI rollup 与碳排并列展示"
)
async def get_hi_carbon_dual_view(request: HICarbonDualViewRequest):
    """
    生成健康指数(HI)与碳排风险并列展示数据

    每个装置同时展示：
    - HI 分数、等级、趋势
    - 预紧力劣化速率
    - 估算泄漏率
    - 月度碳排增量、碳排风险等级、趋势
    """
    try:
        service = get_carbon_energy_service()
        result = service.generate_hi_carbon_dual_view(nodes_data=request.nodes)

        items = [
            HICarbonDualItemSchema(**item) for item in result['items']
        ]

        return HICarbonDualViewResponse(
            report_month=result['report_month'],
            total_nodes=result['total_nodes'],
            items=items,
            generated_at=result['generated_at'],
        )
    except Exception as e:
        logger.error(f"生成HI碳排并列视图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/carbon/esg/export",
    response_model=ESGReportFragmentResponse,
    tags=["碳排与能效分析"],
    summary="导出 ESG 报表片段"
)
async def export_esg_report_fragment(request: ESGReportExportRequest):
    """
    导出适用于企业 ESG 报告 / 温室气体排放清单的片段内容

    - 支持 json / csv 格式输出
    - 包含汇总数据、Top 高风险装置、趋势分析、建议措施
    - 可选择包含方法学说明
    - 不强制精确计量，强调趋势与优先级
    """
    try:
        service = get_carbon_energy_service()

        ranking_data = service.generate_monthly_ranking(
            nodes_data=request.nodes,
            top_n=request.top_n,
        )

        fragment = service.generate_esg_report_fragment(
            ranking_data=ranking_data,
            include_methodology=request.include_methodology,
        )

        csv_content = None
        if request.format.lower() == "csv":
            csv_content = service.export_esg_csv(fragment)

        top_risk_items = [
            CarbonRiskItemSchema(**item) for item in fragment.top_risk_items
        ]

        return ESGReportFragmentResponse(
            report_period=fragment.report_period,
            generated_at=fragment.generated_at,
            summary=ESGReportSummarySchema(**fragment.summary),
            top_risk_items=top_risk_items,
            trend_analysis=ESGTrendAnalysisSchema(**fragment.trend_analysis),
            recommendations=fragment.recommendations,
            methodology_note=fragment.methodology_note if fragment.methodology_note else None,
            csv_content=csv_content,
        )
    except Exception as e:
        logger.error(f"导出ESG报表片段失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/carbon/config",
    response_model=CarbonModelConfigResponse,
    tags=["碳排与能效分析"],
    summary="获取碳排模型系数配置"
)
async def get_carbon_model_config():
    """
    获取当前生效的碳排与能效分析模型系数配置

    包含：
    - 预紧力劣化模型参数
    - 泄漏率估算模型参数
    - 能耗与碳排增量模型参数
    """
    try:
        service = get_carbon_energy_service()
        cfg = service.get_model_config()

        return CarbonModelConfigResponse(
            degradation=DegradationParamsSchema(**cfg['degradation']),
            leakage=LeakageParamsSchema(**cfg['leakage']),
            energy_carbon=EnergyCarbonParamsSchema(**cfg['energy_carbon']),
        )
    except Exception as e:
        logger.error(f"获取碳排模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/carbon/config",
    response_model=CarbonModelConfigResponse,
    tags=["碳排与能效分析"],
    summary="更新碳排模型系数配置"
)
async def update_carbon_model_config(request: CarbonModelConfigUpdateRequest):
    """
    更新碳排与能效分析模型系数配置

    支持部分更新，仅传需要修改的参数即可。
    更新后会持久化到数据库配置表，下次启动自动加载。
    """
    try:
        from app.utils.database import get_db
        import json

        service = get_carbon_energy_service()
        cfg_mgr = service.config_mgr

        if request.degradation:
            for field_name, value in request.degradation.model_dump(exclude_unset=True).items():
                if hasattr(cfg_mgr.degradation, field_name):
                    setattr(cfg_mgr.degradation, field_name, value)
            try:
                with get_db() as db:
                    deg_dict = {
                        k: getattr(cfg_mgr.degradation, k)
                        for k in ['nominal_preload', 'min_effective_preload_ratio',
                                  'relaxation_rate_per_month', 'temperature_acceleration_factor',
                                  'vibration_acceleration_factor', 'cycle_acceleration_factor']
                    }
                    db.execute(
                        "INSERT OR REPLACE INTO sc_health_config (config_key, config_value, description, update_time) "
                        "VALUES ('carbon_degradation_params', :v, '碳排-预紧力劣化模型参数', :t)",
                        {"v": json.dumps(deg_dict), "t": datetime.now().isoformat()}
                    )
                    db.commit()
            except Exception as e:
                logger.warning(f"持久化碳排劣化参数到数据库失败: {e}")

        if request.leakage:
            for field_name, value in request.leakage.model_dump(exclude_unset=True).items():
                if hasattr(cfg_mgr.leakage, field_name):
                    setattr(cfg_mgr.leakage, field_name, value)
            try:
                with get_db() as db:
                    leak_dict = {
                        k: getattr(cfg_mgr.leakage, k)
                        for k in ['base_leakage_rate_m3_per_hour', 'critical_leakage_threshold',
                                  'preload_leakage_sensitivity', 'seal_aging_factor_per_year',
                                  'pressure_sensitivity']
                    }
                    db.execute(
                        "INSERT OR REPLACE INTO sc_health_config (config_key, config_value, description, update_time) "
                        "VALUES ('carbon_leakage_params', :v, '碳排-泄漏率估算模型参数', :t)",
                        {"v": json.dumps(leak_dict), "t": datetime.now().isoformat()}
                    )
                    db.commit()
            except Exception as e:
                logger.warning(f"持久化碳排泄漏参数到数据库失败: {e}")

        if request.energy_carbon:
            for field_name, value in request.energy_carbon.model_dump(exclude_unset=True).items():
                if hasattr(cfg_mgr.energy, field_name):
                    setattr(cfg_mgr.energy, field_name, value)
            try:
                with get_db() as db:
                    eng_dict = {
                        k: getattr(cfg_mgr.energy, k)
                        for k in ['energy_per_leakage_unit', 'carbon_factor_electricity',
                                  'carbon_factor_natural_gas', 'carbon_factor_steam',
                                  'compressor_efficiency', 'recovery_rate',
                                  'base_monthly_energy_kwh', 'base_monthly_carbon_kg']
                    }
                    db.execute(
                        "INSERT OR REPLACE INTO sc_health_config (config_key, config_value, description, update_time) "
                        "VALUES ('carbon_energy_params', :v, '碳排-能耗与碳排增量模型参数', :t)",
                        {"v": json.dumps(eng_dict), "t": datetime.now().isoformat()}
                    )
                    db.commit()
            except Exception as e:
                logger.warning(f"持久化碳排能耗参数到数据库失败: {e}")

        cfg = service.get_model_config()
        return CarbonModelConfigResponse(
            degradation=DegradationParamsSchema(**cfg['degradation']),
            leakage=LeakageParamsSchema(**cfg['leakage']),
            energy_carbon=EnergyCarbonParamsSchema(**cfg['energy_carbon']),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新碳排模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 合规与检验标准检查引擎 ====================

def get_compliance_service():
    from app.services.compliance import ComplianceInspectionService
    return ComplianceInspectionService()


@router.get(
    "/compliance/templates",
    response_model=StandardTemplateListResponse,
    tags=["合规检验"],
    summary="获取标准模板库列表",
)
async def list_standard_templates(
    category: Optional[str] = Query(None, description="装置类别过滤"),
):
    try:
        service = get_compliance_service()
        templates = service.list_standard_templates(category=category)
        return StandardTemplateListResponse(
            total=len(templates),
            items=[StandardTemplateResponse(**t) for t in templates],
        )
    except Exception as e:
        logger.error(f"获取标准模板列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/templates/{code}",
    response_model=StandardTemplateResponse,
    tags=["合规检验"],
    summary="获取标准模板详情",
)
async def get_standard_template(code: str):
    try:
        service = get_compliance_service()
        template = service.get_standard_template(code)
        if not template:
            raise HTTPException(status_code=404, detail=f"标准模板 {code} 不存在")
        return StandardTemplateResponse(**template)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取标准模板详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/compliance/templates",
    response_model=StandardTemplateResponse,
    tags=["合规检验"],
    summary="创建标准模板",
)
async def create_standard_template(request: StandardTemplateCreateRequest):
    try:
        service = get_compliance_service()
        template = service.create_standard_template(request.model_dump())
        return StandardTemplateResponse(**template)
    except Exception as e:
        logger.error(f"创建标准模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/compliance/templates/{template_id}",
    response_model=StandardTemplateResponse,
    tags=["合规检验"],
    summary="更新标准模板",
)
async def update_standard_template(template_id: int, request: StandardTemplateUpdateRequest):
    try:
        service = get_compliance_service()
        template = service.update_standard_template(template_id, request.model_dump(exclude_unset=True))
        if not template:
            raise HTTPException(status_code=404, detail="标准模板不存在")
        return StandardTemplateResponse(**template)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新标准模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/compliance/templates/{template_id}",
    tags=["合规检验"],
    summary="删除标准模板（软删除）",
)
async def delete_standard_template(template_id: int):
    try:
        service = get_compliance_service()
        success = service.delete_standard_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="标准模板不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除标准模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/checklist/{equipment_type}",
    tags=["合规检验"],
    summary="按装置类型加载检查清单",
)
async def load_checklist_by_equipment_type(equipment_type: str):
    try:
        service = get_compliance_service()
        items = service.load_checklist_by_equipment_type(equipment_type)
        return {"equipment_type": equipment_type, "items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"加载检查清单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/compliance/inspection/tasks",
    response_model=InspectionTaskResponse,
    tags=["合规检验"],
    summary="创建检验任务",
)
async def create_inspection_task(request: InspectionTaskCreateRequest):
    try:
        service = get_compliance_service()
        task = service.create_inspection_task(
            work_order_id=request.work_order_id,
            equipment_type=request.equipment_type,
            standard_codes=request.standard_codes,
            node_type=request.node_type,
            node_id=request.node_id,
            alert_level=request.alert_level,
            auto_check_mandatory=request.auto_check_mandatory,
        )
        return InspectionTaskResponse(**task)
    except Exception as e:
        logger.error(f"创建检验任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/inspection/tasks",
    response_model=InspectionTaskListResponse,
    tags=["合规检验"],
    summary="查询检验任务列表",
)
async def list_inspection_tasks(
    status: Optional[str] = Query(None, description="状态过滤 pending/in_progress/completed"),
    equipment_type: Optional[str] = Query(None, description="装置类型过滤"),
    work_order_id: Optional[int] = Query(None, description="工单ID过滤"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        service = get_compliance_service()
        result = service.list_inspection_tasks(
            status=status,
            equipment_type=equipment_type,
            work_order_id=work_order_id,
            limit=limit,
            offset=offset,
        )
        return InspectionTaskListResponse(
            total=result["total"],
            items=[InspectionTaskResponse(**t) for t in result["items"]],
        )
    except Exception as e:
        logger.error(f"查询检验任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/inspection/tasks/{task_id}",
    response_model=InspectionTaskResponse,
    tags=["合规检验"],
    summary="获取检验任务详情",
)
async def get_inspection_task(task_id: int):
    try:
        service = get_compliance_service()
        task = service.get_inspection_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="检验任务不存在")
        return InspectionTaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取检验任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/inspection/work-order/{work_order_id}",
    response_model=InspectionTaskResponse,
    tags=["合规检验"],
    summary="根据工单ID获取检验任务",
)
async def get_inspection_task_by_work_order(work_order_id: int):
    try:
        service = get_compliance_service()
        task = service.get_inspection_task_by_work_order(work_order_id)
        if not task:
            raise HTTPException(status_code=404, detail="该工单无关联检验任务")
        return InspectionTaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工单检验任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/compliance/inspection/tasks/{task_id}/check",
    response_model=InspectionTaskResponse,
    tags=["合规检验"],
    summary="勾选检验项",
)
async def check_inspection_item(task_id: int, request: InspectionItemCheckRequest):
    try:
        service = get_compliance_service()
        task = service.check_inspection_item(
            task_id=task_id,
            item_code=request.item_code,
            result=request.result,
            inspector_id=request.inspector_id,
            inspector_name=request.inspector_name,
            evidence=request.evidence,
            remarks=request.remarks,
        )
        if not task:
            raise HTTPException(status_code=404, detail="检验任务或检验项不存在")
        return InspectionTaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"勾选检验项失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/compliance/inspection/tasks/{task_id}/auto-check",
    response_model=InspectionTaskResponse,
    tags=["合规检验"],
    summary="紧急预警自动勾选必检项",
)
async def auto_check_mandatory_items(task_id: int, request: AutoCheckMandatoryRequest):
    try:
        service = get_compliance_service()
        task = service.auto_check_mandatory_items(
            task_id=task_id,
            alert_level=request.alert_level,
            prediction_evidence=request.prediction_evidence,
        )
        if not task:
            raise HTTPException(status_code=404, detail="检验任务不存在")
        return InspectionTaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动勾选必检项失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/inspection/tasks/{task_id}/score",
    tags=["合规检验"],
    summary="获取检验完成度评分",
)
async def get_completion_score(task_id: int):
    try:
        service = get_compliance_service()
        score = service.calculate_completion_score(task_id)
        return {"task_id": task_id, "completion_score": score}
    except Exception as e:
        logger.error(f"获取完成度评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/work-order/{work_order_id}/close-check",
    response_model=WorkOrderCloseCheckResponse,
    tags=["合规检验"],
    summary="检查工单是否可以关闭",
)
async def check_work_order_close(work_order_id: int):
    try:
        service = get_compliance_service()
        result = service.can_close_work_order(work_order_id)
        return WorkOrderCloseCheckResponse(**result)
    except Exception as e:
        logger.error(f"检查工单关闭条件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/compliance/inspection/tasks/{task_id}/export-pdf",
    response_model=InspectionPdfExportResponse,
    tags=["合规检验"],
    summary="导出PDF检验报告",
)
async def export_inspection_pdf(task_id: int):
    try:
        service = get_compliance_service()
        html_content = service.generate_pdf_html(task_id)
        return InspectionPdfExportResponse(
            html_content=html_content,
            export_time=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"导出PDF检验报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 备件库存与 RUL 联动模块
# ============================================================

_spare_part_service = None
_purchase_optimizer = None


def get_spare_part_service():
    """获取备件库存服务实例"""
    global _spare_part_service
    if _spare_part_service is None:
        from app.services.spare_parts import SparePartService
        _spare_part_service = SparePartService()
    return _spare_part_service


def get_purchase_optimizer():
    """获取采购优化器实例"""
    global _purchase_optimizer
    if _purchase_optimizer is None:
        from app.services.spare_parts import PurchaseOptimizer
        _purchase_optimizer = PurchaseOptimizer()
    return _purchase_optimizer


def _bolt_sku_mapping_to_dict(mapping) -> Dict[str, Any]:
    """将螺栓-SKU映射ORM对象转为响应字典"""
    return {
        'id': mapping.id,
        'bolt_model': mapping.bolt_model,
        'bolt_specification': mapping.bolt_specification,
        'material': mapping.material,
        'standard': mapping.standard,
        'diameter': mapping.diameter,
        'length': mapping.length,
        'performance_grade': mapping.performance_grade,
        'sku_code': mapping.sku_code,
        'sku_name': mapping.sku_name,
        'unit': mapping.unit,
        'unit_price': mapping.unit_price,
        'supplier': mapping.supplier,
        'manufacturer': mapping.manufacturer,
        'purchase_cycle_days': mapping.purchase_cycle_days,
        'min_order_quantity': mapping.min_order_quantity,
        'tenant_id': mapping.tenant_id,
        'is_active': bool(mapping.is_active),
        'create_time': mapping.create_time,
        'update_time': mapping.update_time,
    }


def _spare_part_inventory_to_dict(inventory) -> Dict[str, Any]:
    """将备件库存ORM对象转为响应字典"""
    return {
        'id': inventory.id,
        'sku_code': inventory.sku_code,
        'sku_name': inventory.sku_name,
        'warehouse_code': inventory.warehouse_code,
        'warehouse_name': inventory.warehouse_name,
        'quantity_on_hand': inventory.quantity_on_hand,
        'quantity_reserved': inventory.quantity_reserved,
        'quantity_available': inventory.quantity_available,
        'quantity_in_transit': inventory.quantity_in_transit,
        'reorder_point': inventory.reorder_point,
        'safety_stock': inventory.safety_stock,
        'abc_category': inventory.abc_category,
        'turnover_rate': inventory.turnover_rate,
        'last_count_date': inventory.last_count_date,
        'next_count_date': inventory.next_count_date,
        'tenant_id': inventory.tenant_id,
        'create_time': inventory.create_time,
        'update_time': inventory.update_time,
    }


def _spare_part_demand_to_dict(demand) -> Dict[str, Any]:
    """将备件需求ORM对象转为响应字典"""
    data = {
        'id': demand.id,
        'demand_no': demand.demand_no,
        'source_type': demand.source_type,
        'source_id': demand.source_id,
        'node_type': demand.node_type,
        'node_id': demand.node_id,
        'bolt_model': demand.bolt_model,
        'sku_code': demand.sku_code,
        'sku_name': demand.sku_name,
        'required_quantity': demand.required_quantity,
        'urgency': demand.urgency,
        'priority': demand.priority,
        'rul_days': demand.rul_days,
        'expected_failure_date': demand.expected_failure_date,
        'demand_date': demand.demand_date,
        'stock_status': demand.stock_status,
        'available_quantity': demand.available_quantity,
        'shortage_quantity': demand.shortage_quantity,
        'work_order_id': demand.work_order_id,
        'work_order_upgraded': bool(demand.work_order_upgraded),
        'demand_status': demand.demand_status,
        'device_id': demand.device_id,
        'device_name': demand.device_name,
        'approved_by': demand.approved_by,
        'approved_time': demand.approved_time,
        'fulfilled_quantity': demand.fulfilled_quantity,
        'fulfilled_time': demand.fulfilled_time,
        'tenant_id': demand.tenant_id,
        'create_time': demand.create_time,
        'update_time': demand.update_time,
    }
    if demand.extra_info:
        try:
            data['extra_info'] = json.loads(demand.extra_info)
        except Exception:
            data['extra_info'] = {}
    else:
        data['extra_info'] = {}
    return data


def _demand_summary_to_dict(summary) -> Dict[str, Any]:
    """将需求汇总ORM对象转为响应字典"""
    data = {
        'id': summary.id,
        'summary_no': summary.summary_no,
        'device_id': summary.device_id,
        'device_name': summary.device_name,
        'report_period': summary.report_period,
        'report_date': summary.report_date,
        'total_sku_types': summary.total_sku_types,
        'total_quantity': summary.total_quantity,
        'total_value': summary.total_value,
        'shortage_sku_count': summary.shortage_sku_count,
        'critical_count': summary.critical_count,
        'urgent_count': summary.urgent_count,
        'normal_count': summary.normal_count,
        'tenant_id': summary.tenant_id,
        'create_time': summary.create_time,
    }
    for field, attr in [
        ('demand_details', summary.demand_details),
        ('inventory_analysis', summary.inventory_analysis),
        ('purchase_recommendations', summary.purchase_recommendations),
    ]:
        if attr:
            try:
                data[field] = json.loads(attr)
            except Exception:
                data[field] = attr
        else:
            data[field] = None
    return data


def _purchase_config_to_dict(config) -> Dict[str, Any]:
    """将采购配置ORM对象转为响应字典"""
    return {
        'id': config.id,
        'sku_code': config.sku_code,
        'sku_name': config.sku_name,
        'avg_lead_time_days': config.avg_lead_time_days,
        'lead_time_std_days': config.lead_time_std_days,
        'count_cycle_days': config.count_cycle_days,
        'avg_daily_demand': config.avg_daily_demand,
        'demand_std': config.demand_std,
        'safety_stock_days': config.safety_stock_days,
        'calculated_safety_stock': config.calculated_safety_stock,
        'reorder_point': config.reorder_point,
        'economic_order_quantity': config.economic_order_quantity,
        'service_level': config.service_level,
        'abc_category': config.abc_category,
        'annual_demand': config.annual_demand,
        'order_cost': config.order_cost,
        'holding_cost_rate': config.holding_cost_rate,
        'unit_price': config.unit_price,
        'tenant_id': config.tenant_id,
        'create_time': config.create_time,
        'update_time': config.update_time,
    }


# ==================== 螺栓-SKU映射管理 ====================

@router.get(
    "/spare-parts/sku-mappings",
    response_model=BoltSkuMappingListResponse,
    tags=["备件库存"],
    summary="查询螺栓-SKU映射列表",
)
async def list_sku_mappings(
    bolt_model: Optional[str] = Query(None, description="螺栓型号模糊查询"),
    sku_code: Optional[str] = Query(None, description="SKU编码精确查询"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询螺栓型号与备件SKU的映射关系列表"""
    try:
        service = get_spare_part_service()
        mappings = service.list_sku_mappings(
            bolt_model=bolt_model,
            sku_code=sku_code,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )
        items = [_bolt_sku_mapping_to_dict(m) for m in mappings]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询SKU映射列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/sku-mappings/query",
    response_model=BoltSkuMappingListResponse,
    tags=["备件库存"],
    summary="高级查询螺栓-SKU映射",
)
async def query_sku_mappings(request: BoltSkuQueryRequest):
    """根据螺栓规格参数高级查询SKU映射"""
    try:
        service = get_spare_part_service()
        mappings = service.query_sku_mappings(
            bolt_model=request.bolt_model,
            diameter=request.diameter,
            length=request.length,
            performance_grade=request.performance_grade,
            material=request.material,
            standard=request.standard,
            limit=request.limit or 100,
        )
        items = [_bolt_sku_mapping_to_dict(m) for m in mappings]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"高级查询SKU映射失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/sku-mappings/{mapping_id}",
    response_model=BoltSkuMappingResponse,
    tags=["备件库存"],
    summary="获取螺栓-SKU映射详情",
)
async def get_sku_mapping(mapping_id: int):
    """获取单个螺栓-SKU映射详情"""
    try:
        service = get_spare_part_service()
        mapping = service.get_sku_mapping(mapping_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="映射不存在")
        return _bolt_sku_mapping_to_dict(mapping)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取SKU映射详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/sku-for-bolt/{bolt_model}",
    response_model=BoltSkuMappingResponse,
    tags=["备件库存"],
    summary="根据螺栓型号查询SKU",
)
async def get_sku_for_bolt(bolt_model: str):
    """根据螺栓型号查询对应的备件SKU"""
    try:
        service = get_spare_part_service()
        mapping = service.get_sku_for_bolt(bolt_model)
        if not mapping:
            raise HTTPException(status_code=404, detail=f"未找到螺栓型号 {bolt_model} 对应的SKU")
        return _bolt_sku_mapping_to_dict(mapping)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"根据螺栓型号查询SKU失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/sku-mappings",
    response_model=BoltSkuMappingResponse,
    tags=["备件库存"],
    summary="创建螺栓-SKU映射",
)
async def create_sku_mapping(request: BoltSkuMappingCreate):
    """创建螺栓型号与备件SKU的映射关系"""
    try:
        service = get_spare_part_service()
        mapping = service.create_sku_mapping(**request.model_dump())
        if not mapping:
            raise HTTPException(status_code=500, detail="创建映射失败")
        return _bolt_sku_mapping_to_dict(mapping)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建SKU映射失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/spare-parts/sku-mappings/{mapping_id}",
    response_model=BoltSkuMappingResponse,
    tags=["备件库存"],
    summary="更新螺栓-SKU映射",
)
async def update_sku_mapping(mapping_id: int, request: BoltSkuMappingUpdate):
    """更新螺栓-SKU映射关系"""
    try:
        service = get_spare_part_service()
        mapping = service.update_sku_mapping(mapping_id, **request.model_dump(exclude_unset=True))
        if not mapping:
            raise HTTPException(status_code=404, detail="映射不存在")
        return _bolt_sku_mapping_to_dict(mapping)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新SKU映射失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/spare-parts/sku-mappings/{mapping_id}",
    tags=["备件库存"],
    summary="删除螺栓-SKU映射",
)
async def delete_sku_mapping(mapping_id: int):
    """删除螺栓-SKU映射关系"""
    try:
        service = get_spare_part_service()
        success = service.delete_sku_mapping(mapping_id)
        if not success:
            raise HTTPException(status_code=404, detail="映射不存在")
        return {"status": "success", "message": "映射已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除SKU映射失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 库存查询管理 ====================

@router.get(
    "/spare-parts/inventory",
    response_model=SparePartInventoryListResponse,
    tags=["备件库存"],
    summary="查询备件库存列表",
)
async def list_inventory(
    sku_code: Optional[str] = Query(None, description="SKU编码"),
    sku_name: Optional[str] = Query(None, description="SKU名称模糊查询"),
    warehouse_code: Optional[str] = Query(None, description="仓库编码"),
    abc_category: Optional[str] = Query(None, description="ABC分类 A/B/C"),
    stock_status: Optional[str] = Query(None, description="库存状态: in_stock/shortage/out_of_stock"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询备件库存列表，支持多条件筛选"""
    try:
        service = get_spare_part_service()
        inventory_list = service.list_inventory(
            sku_code=sku_code,
            sku_name=sku_name,
            warehouse_code=warehouse_code,
            abc_category=abc_category,
            stock_status=stock_status,
            limit=limit,
            offset=offset,
        )
        items = [_spare_part_inventory_to_dict(inv) for inv in inventory_list]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询库存列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/inventory/{sku_code}",
    response_model=SparePartInventoryResponse,
    tags=["备件库存"],
    summary="查询单个SKU库存",
)
async def get_inventory(sku_code: str, warehouse_code: Optional[str] = Query(None, description="仓库编码")):
    """查询指定SKU的库存详情"""
    try:
        service = get_spare_part_service()
        inventory = service.check_inventory(sku_code, warehouse_code)
        if not inventory:
            raise HTTPException(status_code=404, detail=f"未找到SKU {sku_code} 的库存记录")
        return _spare_part_inventory_to_dict(inventory)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询SKU库存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/inventory/{sku_code}/availability",
    response_model=StockAvailabilityCheckResponse,
    tags=["备件库存"],
    summary="检查库存可用性",
)
async def check_stock_availability(
    sku_code: str,
    required_quantity: int = Query(..., ge=1, description="需求数量"),
    warehouse_code: Optional[str] = Query(None, description="仓库编码"),
):
    """检查指定SKU的库存是否满足需求数量"""
    try:
        service = get_spare_part_service()
        result = service.check_stock_availability(
            sku_code=sku_code,
            required_quantity=required_quantity,
            warehouse_code=warehouse_code,
        )
        return result
    except Exception as e:
        logger.error(f"检查库存可用性失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 备件需求管理 ====================

@router.post(
    "/spare-parts/demands/from-rul",
    response_model=SparePartDemandResponse,
    tags=["备件库存"],
    summary="根据RUL预测生成备件需求",
)
async def generate_demand_from_rul(request: SparePartDemandFromRulRequest):
    """
    根据螺栓RUL预测结果自动生成备件需求建议

    - 当RUL低于阈值时自动创建需求单
    - 自动检查库存可用性
    - 缺货时自动创建工单并升级优先级
    """
    try:
        service = get_spare_part_service()

        rul_prediction_dict = request.rul_prediction.model_dump() if request.rul_prediction else None

        demand = service.generate_demand_from_rul(
            rul_prediction=rul_prediction_dict,
            bolt_model=request.bolt_model,
            bolt_id=request.bolt_id,
            device_id=request.device_id,
            device_name=request.device_name,
            required_quantity=request.required_quantity or 1,
            rul_threshold_days=request.rul_threshold_days,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
        )
        if not demand:
            raise HTTPException(status_code=500, detail="生成备件需求失败")
        return _spare_part_demand_to_dict(demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"根据RUL生成备件需求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/demands/scan-rul",
    response_model=SparePartRulScanResponse,
    tags=["备件库存"],
    summary="批量扫描RUL生成备件需求",
)
async def scan_rul_and_generate_demands(request: SparePartRulScanRequest):
    """
    批量扫描数据库中所有RUL低于阈值的预测记录，自动生成备件需求

    - 可指定RUL阈值（默认30天）
    - 可按装置筛选
    - 支持自动创建缺货工单
    """
    try:
        service = get_spare_part_service()
        result = service.scan_rul_and_generate_demands(
            rul_threshold_days=request.rul_threshold_days,
            device_id=request.device_id,
            create_work_order=request.create_work_order or True,
            operator_id=request.operator_id,
            operator_name=request.operator_name,
        )
        return result
    except Exception as e:
        logger.error(f"批量扫描RUL生成需求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/demands",
    response_model=SparePartDemandListResponse,
    tags=["备件库存"],
    summary="查询备件需求列表",
)
async def list_demands(
    demand_status: Optional[str] = Query(None, description="需求状态: pending/approved/fulfilled/cancelled"),
    urgency: Optional[str] = Query(None, description="紧急程度: critical/urgent/normal"),
    stock_status: Optional[str] = Query(None, description="库存状态: in_stock/shortage/out_of_stock"),
    device_id: Optional[str] = Query(None, description="装置ID"),
    sku_code: Optional[str] = Query(None, description="SKU编码"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询备件需求列表"""
    try:
        service = get_spare_part_service()
        demands = service.list_demands(
            demand_status=demand_status,
            urgency=urgency,
            stock_status=stock_status,
            device_id=device_id,
            sku_code=sku_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        items = [_spare_part_demand_to_dict(d) for d in demands]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询需求列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/demands/{demand_id}",
    response_model=SparePartDemandResponse,
    tags=["备件库存"],
    summary="获取备件需求详情",
)
async def get_demand(demand_id: int):
    """获取单个备件需求详情"""
    try:
        service = get_spare_part_service()
        demand = service.get_demand(demand_id)
        if not demand:
            raise HTTPException(status_code=404, detail="需求不存在")
        return _spare_part_demand_to_dict(demand)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取需求详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/demands/{demand_id}/approve",
    response_model=SparePartDemandResponse,
    tags=["备件库存"],
    summary="审批备件需求",
)
async def approve_demand(demand_id: int, request: SparePartDemandApproveRequest):
    """审批备件需求，通过后可进行出库操作"""
    try:
        service = get_spare_part_service()
        demand = service.approve_demand(
            demand_id=demand_id,
            approved=request.approved,
            approved_quantity=request.approved_quantity,
            approver_id=request.approver_id,
            approver_name=request.approver_name,
            approval_notes=request.approval_notes,
        )
        if not demand:
            raise HTTPException(status_code=404, detail="需求不存在")
        return _spare_part_demand_to_dict(demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"审批需求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/demands/{demand_id}/fulfill",
    response_model=SparePartDemandResponse,
    tags=["备件库存"],
    summary="完成备件需求（出库）",
)
async def fulfill_demand(demand_id: int, request: SparePartDemandFulfillRequest):
    """完成备件需求，执行出库扣减库存"""
    try:
        service = get_spare_part_service()
        demand = service.fulfill_demand(
            demand_id=demand_id,
            fulfilled_quantity=request.fulfilled_quantity,
            operator_id=request.operator_id_id,
            operator_name=request.operator_name_id if hasattr(request, 'operator_name_id') else request.operator_name,
            fulfillment_notes=request.fulfillment_notes,
        )
        if not demand:
            raise HTTPException(status_code=404, detail="需求不存在")
        return _spare_part_demand_to_dict(demand)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成需求（出库）失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/demands/{demand_id}/upgrade-work-order",
    tags=["备件库存"],
    summary="升级关联工单优先级",
)
async def upgrade_demand_work_order(
    demand_id: int,
    reason: Optional[str] = Query(None, description="升级原因"),
):
    """当备件缺货时，手动升级关联工单的优先级"""
    try:
        service = get_spare_part_service()
        result = service.upgrade_work_order_priority(
            demand_id=demand_id,
            reason=reason,
        )
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('message', '升级失败'))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"升级工单优先级失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 装置需求汇总报表 ====================

@router.post(
    "/spare-parts/summaries/device",
    response_model=SparePartDemandSummaryResponse,
    tags=["备件库存"],
    summary="生成装置备件需求汇总报表",
)
async def generate_device_summary(request: SparePartDemandSummaryRequest):
    """
    按装置维度汇总备件需求，生成统计报表

    - 汇总指定装置的所有未完成需求
    - 按紧急程度分类统计
    - 分析库存状况
    - 生成采购建议
    """
    try:
        service = get_spare_part_service()
        summary = service.generate_device_summary(
            device_id=request.device_id,
            device_name=request.device_name,
            report_period=request.report_period,
            include_approved_only=request.include_approved_only or False,
            operator_id=request.operator_id_id,
            operator_name=request.operator_name_id if hasattr(request, 'operator_name_id') else request.operator_name,
        )
        if not summary:
            raise HTTPException(status_code=500, detail="生成汇总报表失败")
        return _demand_summary_to_dict(summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成装置需求汇总失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/summaries",
    response_model=SparePartDemandSummaryListResponse,
    tags=["备件库存"],
    summary="查询需求汇总报表列表",
)
async def list_summaries(
    device_id: Optional[str] = Query(None, description="装置ID"),
    report_period: Optional[str] = Query(None, description="报告周期"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(50, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询装置需求汇总报表列表"""
    try:
        service = get_spare_part_service()
        summaries = service.list_summaries(
            device_id=device_id,
            report_period=report_period,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        items = [_demand_summary_to_dict(s) for s in summaries]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询汇总报表列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/summaries/{summary_id}",
    response_model=SparePartDemandSummaryResponse,
    tags=["备件库存"],
    summary="获取需求汇总报表详情",
)
async def get_summary(summary_id: int):
    """获取单个需求汇总报表详情"""
    try:
        service = get_spare_part_service()
        summary = service.get_summary(summary_id)
        if not summary:
            raise HTTPException(status_code=404, detail="汇总报表不存在")
        return _demand_summary_to_dict(summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取汇总报表详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 采购周期与安全库存建议 ====================

@router.post(
    "/spare-parts/purchase/analyze",
    response_model=PurchaseAnalysisResponse,
    tags=["采购优化"],
    summary="分析SKU采购策略",
)
async def analyze_sku_purchase(request: PurchaseAnalysisRequest):
    """
    分析单个SKU的采购策略，提供安全库存和经济订货批量建议

    - 计算需求统计数据（日均需求、标准差、变异系数）
    - 计算安全库存（考虑需求和提前期不确定性）
    - 计算经济订货批量 EOQ
    - 计算再订货点 ROP
    - 进行ABC分类
    """
    try:
        optimizer = get_purchase_optimizer()
        result = optimizer.analyze_sku(
            sku_code=request.sku_code,
            sku_name=request.sku_name,
            history_days=request.history_days or 90,
            service_level=request.service_level or 0.95,
            safety_stock_method=request.safety_stock_method or 'statistical',
            safety_stock_days=request.safety_stock_days,
            unit_price=request.unit_price,
            order_cost=request.order_cost,
            holding_cost_rate=request.holding_cost_rate or 0.25,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"分析SKU采购策略失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/purchase/config",
    response_model=PurchaseConfigResponse,
    tags=["采购优化"],
    summary="保存采购周期配置",
)
async def save_purchase_config(request: PurchaseConfigSaveRequest):
    """保存SKU的采购周期与安全库存配置到数据库"""
    try:
        optimizer = get_purchase_optimizer()
        config = optimizer.save_config(**request.model_dump())
        if not config:
            raise HTTPException(status_code=500, detail="保存配置失败")
        return _purchase_config_to_dict(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存采购配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/purchase/configs",
    tags=["采购优化"],
    summary="查询采购配置列表",
)
async def list_purchase_configs(
    sku_code: Optional[str] = Query(None, description="SKU编码"),
    abc_category: Optional[str] = Query(None, description="ABC分类 A/B/C"),
    service_level: Optional[float] = Query(None, description="服务水平"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询采购周期配置列表"""
    try:
        optimizer = get_purchase_optimizer()
        configs = optimizer.list_configs(
            sku_code=sku_code,
            abc_category=abc_category,
            service_level=service_level,
            limit=limit,
            offset=offset,
        )
        items = [_purchase_config_to_dict(c) for c in configs]
        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"查询采购配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/spare-parts/purchase/configs/{sku_code}",
    response_model=PurchaseConfigResponse,
    tags=["采购优化"],
    summary="获取SKU采购配置",
)
async def get_purchase_config(sku_code: str):
    """获取指定SKU的采购配置"""
    try:
        optimizer = get_purchase_optimizer()
        config = optimizer.get_config(sku_code)
        if not config:
            raise HTTPException(status_code=404, detail=f"未找到SKU {sku_code} 的采购配置")
        return _purchase_config_to_dict(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取采购配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/spare-parts/purchase/plan",
    response_model=PurchasePlanResponse,
    tags=["采购优化"],
    summary="生成综合采购计划",
)
async def generate_purchase_plan(request: PurchasePlanRequest):
    """
    生成综合采购计划，考虑RUL预测需求和库存状况

    - 汇总所有缺货和低于安全库存的SKU
    - 考虑RUL预测产生的未来需求
    - 合并相同SKU的需求
    - 考虑经济订货批量进行数量优化
    - 按紧急程度排序
    """
    try:
        optimizer = get_purchase_optimizer()
        result = optimizer.generate_purchase_plan(
            device_id=request.device_id,
            include_rul_demands=request.include_rul_demands or True,
            rul_days_ahead=request.rul_days_ahead or 30,
            apply_eoq=request.apply_eoq or True,
            service_level=request.service_level or 0.95,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成采购计划失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 3D数字孪生可视化 ====================

@router.post(
    "/visualization/3d/scene",
    response_model=Flange3DSceneInfoResponse,
    tags=["3D可视化"],
    summary="创建法兰3D场景"
)
async def create_flange_3d_scene(request: Flange3DCreateRequest):
    """
    创建法兰3D数字孪生场景

    支持：
    - 程序化生成法兰3D模型
    - 螺栓坐标映射表导入（CSV/JSON）
    - 状态/健康度/风险颜色映射
    - 环形自动分布螺栓

    螺栓坐标CSV格式：
    - 2D展开图: bolt_id,position_index,angle_deg,radius_mm
    - 3D坐标: bolt_id,x,y,z

    螺栓坐标JSON格式：
    - 数组: [{"bolt_id": "B001", "x": 100, "y": 0, "z": 50}, ...]
    - 对象: {"flange_radius": 100, "bolts": [{"bolt_id": "B001", "angle_deg": 0}, ...]}
    """
    try:
        service = get_visualization_3d_service()

        bolt_data_dict = None
        if request.bolt_data:
            bolt_data_dict = {
                item.bolt_id: item.model_dump(exclude_none=True)
                for item in request.bolt_data
            }

        scene = service.create_flange_scene(
            flange_id=request.flange_id,
            bolt_ids=request.bolt_ids,
            bolt_count=request.bolt_count or 8,
            bolt_data=bolt_data_dict,
            bolt_coordinate_csv=request.bolt_coordinate_csv,
            bolt_coordinate_json=request.bolt_coordinate_json,
            flange_params=request.flange_params,
            visualization_mode=request.visualization_mode or "status",
        )

        bolt_coords = [
            BoltCoordinateItemSchema(
                bolt_id=coord.bolt_id,
                x=coord.x,
                y=coord.y,
                z=coord.z,
                angle=coord.angle,
                radius=coord.radius,
                position_index=coord.position_index,
            )
            for coord in service.bolt_mapper.get_all_coordinates()
        ]

        return Flange3DSceneInfoResponse(
            flange_id=scene['flange_id'],
            visualization_mode=scene['visualization_mode'],
            bolt_count=len(scene['bolt_ids']),
            bolt_ids=scene['bolt_ids'],
            flange_params=scene['flange_params'],
            bolt_coordinates=bolt_coords,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建法兰3D场景失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/visualization/3d/scene/{flange_id}",
    response_model=Flange3DSceneInfoResponse,
    tags=["3D可视化"],
    summary="获取法兰3D场景信息"
)
async def get_flange_3d_scene(flange_id: str):
    """获取指定法兰的3D场景信息"""
    try:
        service = get_visualization_3d_service()
        scene_info = service.get_scene_info(flange_id)
        if not scene_info:
            raise HTTPException(status_code=404, detail=f"场景 {flange_id} 不存在")

        bolt_coords = [
            BoltCoordinateItemSchema(
                bolt_id=coord.bolt_id,
                x=coord.x,
                y=coord.y,
                z=coord.z,
                angle=coord.angle,
                radius=coord.radius,
                position_index=coord.position_index,
            )
            for coord in service.bolt_mapper.get_all_coordinates()
        ]

        return Flange3DSceneInfoResponse(
            flange_id=scene_info['flange_id'],
            visualization_mode=scene_info['visualization_mode'],
            bolt_count=scene_info['bolt_count'],
            bolt_ids=scene_info['bolt_ids'],
            flange_params=scene_info['flange_params'],
            bolt_coordinates=bolt_coords,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取法兰3D场景信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/visualization/3d/scenes",
    response_model=Flange3DListResponse,
    tags=["3D可视化"],
    summary="获取3D场景列表"
)
async def list_flange_3d_scenes():
    """获取所有已创建的3D场景列表"""
    try:
        service = get_visualization_3d_service()
        scenes = service.list_scenes()
        return Flange3DListResponse(
            total=len(scenes),
            scenes=scenes,
        )
    except Exception as e:
        logger.error(f"获取3D场景列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/visualization/3d/export/{flange_id}",
    response_model=Flange3DExportResponse,
    tags=["3D可视化"],
    summary="导出法兰3D场景"
)
async def export_flange_3d_scene(
    flange_id: str,
    format: str = Query("threejs", description="导出格式: gltf/threejs/unity/all"),
    visualization_mode: Optional[str] = Query(None, description="可视化模式"),
):
    """
    导出法兰3D场景为指定格式

    支持格式：
    - **gltf**: glTF 2.0格式，支持Three.js、Unity、Unreal等多种引擎
    - **threejs**: Three.js Object3D JSON格式，可直接用THREE.ObjectLoader加载
    - **unity**: Unity数据包格式，包含网格、材质、螺栓状态数据
    - **all**: 导出所有格式
    """
    try:
        service = get_visualization_3d_service()
        scene_info = service.get_scene_info(flange_id)
        if not scene_info:
            raise HTTPException(status_code=404, detail=f"场景 {flange_id} 不存在")

        if visualization_mode:
            from app.services.visualization_3d.color_mapper import ColorMapper
            scene_data = service._scenes.get(flange_id)
            if scene_data:
                scene_data['visualization_mode'] = visualization_mode

        mode = visualization_mode or scene_info['visualization_mode']

        if format == 'gltf':
            data = service.export_gltf(flange_id)
        elif format == 'threejs':
            data = service.export_threejs(flange_id)
        elif format == 'unity':
            data = service.export_unity(flange_id)
        elif format == 'all':
            data = service.export_all_formats(flange_id)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")

        return Flange3DExportResponse(
            flange_id=flange_id,
            format=format,
            visualization_mode=mode,
            export_time=datetime.now(),
            data=data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出法兰3D场景失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/visualization/3d/update",
    response_model=Flange3DUpdateResponse,
    tags=["3D可视化"],
    summary="更新螺栓状态（增量更新）"
)
async def update_bolt_3d_status(request: Flange3DUpdateRequest):
    """
    增量更新螺栓状态数据

    用于实时更新螺栓的状态、健康度、风险等级等数据，
    前端可通过返回数据更新3D视图中螺栓的颜色和状态。
    """
    try:
        service = get_visualization_3d_service()
        scene_info = service.get_scene_info(request.flange_id)
        if not scene_info:
            raise HTTPException(status_code=404, detail=f"场景 {request.flange_id} 不存在")

        bolt_data_dict = {
            item.bolt_id: item.model_dump(exclude_none=True)
            for item in request.bolt_data
        }

        scene_data = service.update_bolt_status(
            flange_id=request.flange_id,
            bolt_data=bolt_data_dict,
            visualization_mode=request.visualization_mode,
        )

        bolt_updates = []
        for bolt_id, data in bolt_data_dict.items():
            if bolt_id in scene_data['bolt_data']:
                bolt_updates.append({
                    'bolt_id': bolt_id,
                    'color_hex': scene_data['bolt_data'][bolt_id].get('color_hex'),
                    'data': scene_data['bolt_data'][bolt_id],
                })

        return Flange3DUpdateResponse(
            flange_id=request.flange_id,
            updated_count=len(bolt_updates),
            visualization_mode=scene_data['visualization_mode'],
            bolt_updates=bolt_updates,
            update_time=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新螺栓3D状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/visualization/3d/explosion/{flange_id}",
    response_model=Flange3DExplosionResponse,
    tags=["3D可视化"],
    summary="获取爆炸图位置"
)
async def get_flange_explosion_positions(
    flange_id: str,
    explosion_factor: float = Query(1.0, description="爆炸因子 0-1", ge=0, le=2),
):
    """
    获取螺栓爆炸图位置

    - explosion_factor = 0: 原始位置
    - explosion_factor = 1: 完全爆炸
    - 爆炸方向：径向向外 + 轴向偏移
    """
    try:
        service = get_visualization_3d_service()
        scene_info = service.get_scene_info(flange_id)
        if not scene_info:
            raise HTTPException(status_code=404, detail=f"场景 {flange_id} 不存在")

        positions = service.get_explosion_positions(flange_id, explosion_factor)

        bolt_positions = {
            bolt_id: list(pos)
            for bolt_id, pos in positions.items()
        }

        return Flange3DExplosionResponse(
            flange_id=flange_id,
            explosion_factor=explosion_factor,
            bolt_positions=bolt_positions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取爆炸图位置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/visualization/3d/scene/{flange_id}",
    tags=["3D可视化"],
    summary="删除3D场景缓存"
)
async def delete_flange_3d_scene(flange_id: str):
    """删除指定法兰的3D场景缓存"""
    try:
        service = get_visualization_3d_service()
        service.clear_scene(flange_id)
        return {"status": "success", "message": f"场景 {flange_id} 已删除"}
    except Exception as e:
        logger.error(f"删除3D场景失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 超参优化 (HPO) 模块
# ============================================================

_hpo_service = None


def get_hpo_service():
    """获取 HPO 服务实例"""
    global _hpo_service
    if _hpo_service is None:
        from app.services.hpo import HPOService
        _hpo_service = HPOService()
    return _hpo_service


def _convert_search_space_to_dict(
    search_space: Optional[SearchSpaceSchema],
) -> Optional[Dict[str, Any]]:
    """将搜索空间 schema 转换为字典"""
    if search_space is None:
        return None
    result = {}
    for field_name, field_value in search_space.model_dump(exclude_none=True).items():
        if field_name == 'custom_params' and field_value:
            for k, v in field_value.items():
                result[k] = v
        elif field_name == 'fixed_params' and field_value:
            result['_fixed_'] = field_value
        else:
            result[field_name] = field_value
    return result


@router.post(
    "/hpo/studies",
    response_model=HPOCreateStudyResponse,
    tags=["超参优化"],
    summary="创建HPO研究"
)
async def create_hpo_study(request: HPOCreateStudyRequest):
    """
    创建超参优化研究

    支持配置：
    - 搜索空间：层数、hidden size、dropout、lr、sequence_length
    - 优化目标：验证F1 + 误报惩罚 + 推理延迟约束
    - 优化框架：Optuna / Ray Tune
    - 优化算法：TPE、Random、CMA-ES、Grid、ASHA等
    - Per-node 超参：为不同节点设置独立超参
    """
    try:
        service = get_hpo_service()

        custom_search_space = _convert_search_space_to_dict(request.search_space)
        objective_config = request.objective_config.model_dump(exclude_none=True) if request.objective_config else None

        result = service.create_study(
            study_name=request.study_name,
            model_type=request.model_type,
            node_id=request.node_id,
            node_type=request.node_type,
            custom_search_space=custom_search_space,
            fixed_params=request.search_space.fixed_params if request.search_space else None,
            objective_config=objective_config,
            framework=request.framework,
            optimizer=request.optimizer,
            max_trials=request.max_trials,
            max_concurrent_trials=request.max_concurrent_trials,
            min_trials_to_prune=request.min_trials_to_prune,
            pruner_type=request.pruner_type,
            per_node_hpo_enabled=request.per_node_hpo_enabled,
            node_scope=request.node_scope,
            tenant_id=request.tenant_id,
            created_by=request.created_by,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "创建研究失败"))

        return HPOCreateStudyResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建HPO研究失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hpo/studies",
    response_model=HPOStudyListResponse,
    tags=["超参优化"],
    summary="获取HPO研究列表"
)
async def list_hpo_studies(
    model_type: Optional[str] = Query(None, description="模型类型过滤 bolt/flange"),
    status: Optional[str] = Query(None, description="状态过滤 pending/running/completed/failed"),
    limit: int = Query(50, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取HPO研究列表，支持按模型类型和状态过滤"""
    try:
        service = get_hpo_service()
        result = service.list_studies(
            model_type=model_type,
            status=status,
            limit=limit,
            offset=offset,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail="获取研究列表失败")

        studies = [HPOStudySchema(**s) for s in result.get("studies", [])]
        return HPOStudyListResponse(
            success=True,
            total=result.get("total", 0),
            studies=studies,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HPO研究列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hpo/studies/{study_id}",
    response_model=HPOStudyStatusResponse,
    tags=["超参优化"],
    summary="获取HPO研究详情和状态"
)
async def get_hpo_study_status(study_id: str):
    """
    获取指定HPO研究的详细信息和当前状态

    返回内容：
    - 研究基本信息
    - 试验统计（总数、各状态数量、最新10条）
    - 当前最优试验
    """
    try:
        service = get_hpo_service()
        result = service.get_study_status(study_id)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("message", "研究不存在"))

        study_data = result.get("study", {})
        study_schema = HPOStudySchema(**study_data)

        trials_data = result.get("trials", {})
        best_trial = result.get("best_trial")
        best_trial_schema = HPOTrialSchema(**best_trial) if best_trial else None

        return HPOStudyStatusResponse(
            success=True,
            study=study_schema,
            trials=trials_data,
            best_trial=best_trial_schema,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HPO研究状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/hpo/studies/start",
    response_model=HPOStartStudyResponse,
    tags=["超参优化"],
    summary="启动HPO研究"
)
async def start_hpo_study(
    request: HPOStartStudyRequest,
    background_tasks: BackgroundTasks,
):
    """
    启动已创建的HPO研究，在后台执行超参搜索

    Args:
        study_id: 研究ID
        auto_apply_best: 研究完成后是否自动应用最优配置到训练任务
    """
    try:
        service = get_hpo_service()

        study_data = service.storage_service.get_study(request.study_id)
        if not study_data:
            raise HTTPException(status_code=404, detail=f"研究不存在: {request.study_id}")

        if study_data.get("status") == "running":
            raise HTTPException(status_code=400, detail="研究已在运行中")

        background_tasks.add_task(
            service.start_study,
            study_id=request.study_id,
            auto_apply_best=request.auto_apply_best,
        )

        return HPOStartStudyResponse(
            study_id=request.study_id,
            status="started",
            message=f"HPO研究已启动，将在后台执行。使用 study_id={request.study_id} 查询状态",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动HPO研究失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hpo/studies/{study_id}/trials",
    response_model=HPOTrialListResponse,
    tags=["超参优化"],
    summary="获取研究的试验列表"
)
async def list_hpo_trials(
    study_id: str,
    status: Optional[str] = Query(None, description="状态过滤 pending/running/completed/failed/pruned"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取指定研究的所有试验记录"""
    try:
        service = get_hpo_service()
        result = service.list_trials(
            study_id=study_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail="获取试验列表失败")

        trials = [HPOTrialSchema(**t) for t in result.get("trials", [])]
        return HPOTrialListResponse(
            success=True,
            total=result.get("total", 0),
            trials=trials,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HPO试验列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hpo/studies/{study_id}/trials/{trial_id}",
    response_model=HPOTrialSchema,
    tags=["超参优化"],
    summary="获取单个试验详情"
)
async def get_hpo_trial(study_id: str, trial_id: str):
    """获取指定试验的详细信息"""
    try:
        service = get_hpo_service()
        trial = service.storage_service.get_trial(trial_id)

        if not trial:
            raise HTTPException(status_code=404, detail="试验不存在")

        if trial.get("study_id") != study_id:
            raise HTTPException(status_code=400, detail="试验不属于该研究")

        return HPOTrialSchema(**trial)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HPO试验详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/hpo/studies/{study_id}/apply",
    response_model=HPOApplyConfigResponse,
    tags=["超参优化"],
    summary="应用最优配置到训练任务"
)
async def apply_hpo_best_config(
    study_id: str,
    request: Optional[HPOApplyConfigRequest] = None,
):
    """
    将研究找到的最优超参配置应用到训练任务

    - 不指定 node_ids：应用到研究关联的节点（全局或单个节点）
    - 指定 node_ids：应用到指定的多个节点（per-node 模式）
    """
    try:
        service = get_hpo_service()

        node_ids = request.node_ids if request and request.node_ids else None

        result = service.apply_best_config(
            study_id=study_id,
            node_ids=node_ids,
        )

        if not result.get("success", True) and result.get("success") is not None:
            raise HTTPException(status_code=400, detail=result.get("message", "应用配置失败"))

        return HPOApplyConfigResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用HPO最优配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hpo/studies/{study_id}/compare",
    response_model=HPOCompareConfigResponse,
    tags=["超参优化"],
    summary="比较最优配置与当前配置"
)
async def compare_hpo_config(study_id: str):
    """
    比较HPO研究找到的最优配置与当前训练配置

    返回：
    - 最优参数和当前参数
    - 最优指标和当前指标
    - 参数变化详情
    - 指标改进幅度
    """
    try:
        service = get_hpo_service()
        result = service.compare_configs(study_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "比较配置失败"))

        return HPOCompareConfigResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"比较HPO配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/hpo/studies/{study_id}/node-override",
    response_model=HPONodeOverrideResponse,
    tags=["超参优化"],
    summary="设置节点超参覆盖"
)
async def set_hpo_node_override(
    study_id: str,
    request: HPOSetNodeOverrideRequest,
):
    """
    为特定节点设置独立的超参搜索空间或固定参数

    用于 per-node 超参优化，为不同节点设置不同的搜索空间。
    """
    try:
        service = get_hpo_service()

        search_space_override = _convert_search_space_to_dict(request.search_space_override)

        result = service.set_node_override(
            study_id=study_id,
            node_id=request.node_id,
            node_type=request.node_type,
            search_space_override=search_space_override,
            fixed_params=request.fixed_params,
            tenant_id=request.tenant_id,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "设置节点覆盖失败"))

        return HPONodeOverrideResponse(
            success=True,
            message=result.get("message", "操作成功"),
            study_id=study_id,
            node_id=request.node_id,
            search_space_override=search_space_override,
            fixed_params=request.fixed_params,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置HPO节点覆盖失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/hpo/studies/{study_id}/node-overrides",
    response_model=Dict[str, Any],
    tags=["超参优化"],
    summary="获取研究的节点超参覆盖列表"
)
async def list_hpo_node_overrides(study_id: str):
    """获取指定研究的所有节点超参覆盖配置"""
    try:
        service = get_hpo_service()
        overrides = service.storage_service.list_node_overrides(study_id)

        return {
            "success": True,
            "total": len(overrides),
            "study_id": study_id,
            "overrides": [
                HPONodeOverrideSchema(**o) for o in overrides
            ],
        }

    except Exception as e:
        logger.error(f"获取HPO节点覆盖列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/hpo/studies/{study_id}",
    tags=["超参优化"],
    summary="删除HPO研究"
)
async def delete_hpo_study(study_id: str):
    """
    删除指定的HPO研究

    注意：这将同时删除关联的所有试验记录和节点覆盖配置。
    """
    try:
        service = get_hpo_service()

        study = service.storage_service.get_study(study_id)
        if not study:
            raise HTTPException(status_code=404, detail="研究不存在")

        if study.get("status") == "running":
            raise HTTPException(status_code=400, detail="研究正在运行中，请先停止")

        success = service.storage_service.delete_study(study_id)

        if not success:
            raise HTTPException(status_code=500, detail="删除研究失败")

        return {
            "success": True,
            "message": f"研究 {study_id} 已删除",
            "study_id": study_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除HPO研究失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 风险热力图与传播可视化
# ============================================================


@router.get(
    "/risk/visualization/graph",
    response_model=PropagationGraphResponse,
    tags=["风险可视化"],
    summary="获取风险传播图（nodes/edges）"
)
async def get_propagation_graph(
    tenant_id: int = Query(..., description="租户ID"),
    graph_type: str = Query("composite", description="图类型"),
):
    """
    获取风险传播图，包含节点和边

    - **graph_type**: 图类型，如 co_fault / physical / granger / composite
    """
    try:
        service = get_risk_visualization_service()
        graph = service.get_propagation_graph(
            tenant_id=tenant_id,
            graph_type=graph_type,
        )

        if not graph:
            raise HTTPException(status_code=404, detail="未找到传播图数据")

        return PropagationGraphResponse(**graph)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取传播图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/heatmap/geojson",
    tags=["风险可视化"],
    summary="获取热力图 GeoJSON"
)
async def get_heatmap_geojson(
    tenant_id: int = Query(..., description="租户ID"),
    node_type: str = Query("all", description="节点类型: all/bolt/flange/unit"),
    value_field: str = Query("risk_score", description="热力值字段"),
    aggregate_level: str = Query(None, description="聚合层级"),
):
    """
    获取热力图 GeoJSON 格式数据，支持 GIS 和地图可视化

    - **node_type**: 节点类型过滤
    - **value_field**: 热力值使用的字段
    - **aggregate_level**: 聚合层级，如 group/factory/unit
    """
    try:
        service = get_risk_visualization_service()
        geojson = service.get_heatmap_geojson(
            tenant_id=tenant_id,
            node_type=node_type,
            value_field=value_field,
            aggregate_level=aggregate_level,
        )

        if not geojson:
            raise HTTPException(status_code=404, detail="未找到热力图数据")

        return geojson

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取热力图GeoJSON失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/echarts",
    response_model=EChartsGraphResponse,
    tags=["风险可视化"],
    summary="获取 ECharts 图结构数据"
)
async def get_echarts_graph(
    tenant_id: int = Query(..., description="租户ID"),
    graph_type: str = Query("composite", description="图类型"),
    layout: str = Query("force", description="布局类型: force/circular/none"),
):
    """
    获取 ECharts graph 组件所需的数据结构

    - **layout**: 布局类型 force 力导向 / circular 环形
    - **graph_type**: 图类型
    """
    try:
        service = get_risk_visualization_service()
        echarts_data = service.get_echarts_graph(
            tenant_id=tenant_id,
            graph_type=graph_type,
            layout=layout,
        )

        if not echarts_data:
            raise HTTPException(status_code=404, detail="未找到图数据")

        return EChartsGraphResponse(**echarts_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取ECharts图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/timeseries",
    response_model=TimeSeriesResponse,
    tags=["风险可视化"],
    summary="获取时间切片序列（24小时风险演化）"
)
async def get_time_series_slices(
    tenant_id: int = Query(..., description="租户ID"),
    history_hours: int = Query(24, description="历史时长（小时）", ge=1, le=168),
    interval_minutes: int = Query(60, description="时间间隔（分钟）", ge=5, le=360),
    include_edges: bool = Query(False, description="是否包含边"),
    use_mock: bool = Query(True, description="是否使用模拟数据"),
):
    """
    获取历史时间切片序列，支持风险演化动画回放

    - **history_hours**: 历史时长，默认24小时
    - **interval_minutes**: 时间间隔，默认60分钟
    - **include_edges**: 是否包含边的时间序列
    - **use_mock**: 是否使用模拟数据（无真实数据时）
    """
    try:
        service = get_risk_visualization_service()
        result = service.get_time_series_slices(
            tenant_id=tenant_id,
            history_hours=history_hours,
            interval_minutes=interval_minutes,
            include_edges=include_edges,
            use_mock=use_mock,
        )

        if not result:
            raise HTTPException(status_code=404, detail="未找到时间序列数据")

        return TimeSeriesResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取时间切片序列失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/timeslice/{slice_index}/geojson",
    tags=["风险可视化"],
    summary="获取指定时间切片的 GeoJSON"
)
async def get_time_slice_geojson(
    slice_index: int,
    tenant_id: int = Query(..., description="租户ID"),
    history_hours: int = Query(24, description="历史时长（小时）"),
    interval_minutes: int = Query(60, description="时间间隔（分钟）"),
    use_mock: bool = Query(True, description="是否使用模拟数据"),
):
    """
    获取指定时间切片的 GeoJSON 数据

    - **slice_index**: 时间切片索引
    """
    try:
        service = get_risk_visualization_service()
        geojson = service.get_time_slice_geojson(
            tenant_id=tenant_id,
            slice_index=slice_index,
            history_hours=history_hours,
            interval_minutes=interval_minutes,
            use_mock=use_mock,
        )

        if not geojson:
            raise HTTPException(status_code=404, detail="未找到该时间切片")

        return geojson

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取时间切片GeoJSON失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/propagation-paths",
    response_model=PropagationPathListResponse,
    tags=["风险可视化"],
    summary="获取风险传播路径"
)
async def get_propagation_paths(
    source_node: str = Query(..., description="源节点ID"),
    tenant_id: int = Query(..., description="租户ID"),
    top_k: int = Query(10, description="返回前k条路径", ge=1, le=100),
    max_depth: int = Query(3, description="最大路径深度", ge=1, le=10),
):
    """
    获取从指定节点出发的 top-k 风险传播路径

    - **source_node**: 源节点ID
    - **top_k**: 返回前 k 条路径
    - **max_depth**: 路径最大深度
    """
    try:
        service = get_risk_visualization_service()
        result = service.get_propagation_paths(
            tenant_id=tenant_id,
            source_node=source_node,
            top_k=top_k,
            max_depth=max_depth,
        )

        if not result:
            raise HTTPException(status_code=404, detail="未找到传播路径")

        return PropagationPathListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取传播路径失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/summary",
    response_model=RiskSummaryResponse,
    tags=["风险可视化"],
    summary="获取风险汇总统计"
)
async def get_risk_summary(
    tenant_id: int = Query(..., description="租户ID"),
    graph_type: str = Query("composite", description="图类型"),
):
    """
    获取风险汇总统计信息

    - 总节点数、总边数
    - 平均/最大/最小风险评分
    - 风险等级分布
    - 高风险节点列表
    """
    try:
        service = get_risk_visualization_service()
        result = service.get_risk_summary(
            tenant_id=tenant_id,
            graph_type=graph_type,
        )

        if not result:
            raise HTTPException(status_code=404, detail="未找到风险汇总数据")

        return RiskSummaryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取风险汇总失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/risk/visualization/edge-weights/config",
    response_model=EdgeWeightConfigResponse,
    tags=["风险可视化"],
    summary="更新边权重配置"
)
async def update_edge_weights_config(
    request: EdgeWeightConfigRequest,
    tenant_id: int = Query(..., description="租户ID"),
):
    """
    动态更新三种边权重的比例系数

    - **co_fault_weight**: 共故障权重 (0-1)
    - **physical_weight**: 物理邻接权重 (0-1)
    - **granger_weight**: Granger因果权重 (0-1)
    """
    try:
        service = get_risk_visualization_service()
        result = service.update_edge_weights_config(
            tenant_id=tenant_id,
            co_fault_weight=request.co_fault_weight,
            physical_weight=request.physical_weight,
            granger_weight=request.granger_weight,
        )

        return EdgeWeightConfigResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新边权重配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/edge-weights/config",
    response_model=EdgeWeightConfigResponse,
    tags=["风险可视化"],
    summary="获取边权重配置"
)
async def get_edge_weights_config(
    tenant_id: int = Query(..., description="租户ID"),
):
    """获取当前边权重配置"""
    try:
        service = get_risk_visualization_service()
        result = service.get_edge_weights_config(tenant_id=tenant_id)

        return EdgeWeightConfigResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取边权重配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/risk/visualization/significant-changes",
    response_model=SignificantChangeListResponse,
    tags=["风险可视化"],
    summary="检测风险显著变化点"
)
async def detect_significant_changes(
    tenant_id: int = Query(..., description="租户ID"),
    threshold: float = Query(2.0, description="变化阈值", gt=0, le=10),
    history_hours: int = Query(24, description="历史时长（小时）"),
    use_mock: bool = Query(True, description="是否使用模拟数据"),
):
    """
    检测历史时间序列中风险显著变化的时间点

    - **threshold**: 风险评分变化阈值
    - 返回风险变化超过阈值的所有时间切片
    """
    try:
        service = get_risk_visualization_service()
        result = service.detect_significant_changes(
            tenant_id=tenant_id,
            threshold=threshold,
            history_hours=history_hours,
            use_mock=use_mock,
        )

        return SignificantChangeListResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检测显著变化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/simulation/what-if",
    response_model=WhatIfSimulationResponse,
    tags=["情景仿真"],
    summary="What-if 情景仿真引擎"
)
async def run_what_if_simulation(
    request: WhatIfSimulationRequest,
):
    """
    What-if 情景仿真引擎

    基于历史HI/预紧力序列，在不同情景假设下模拟未来劣化轨迹。

    **输入**:
    - 节点信息(node_id/node_type)
    - 历史序列(HI或预紧力)
    - 多情景列表(斜率调整、阶跃变化、噪声、温湿度/振动场景、维护策略)

    **输出**:
    - 模拟未来轨迹(含HI、风险、上下界、维护标记)
    - 首次触阈时间(干预/预警/故障三个阈值)
    - 风险等级时间线
    - 建议干预时间点(预防性/纠正性/紧急三级)
    - 批量情景对比(综合排名+推荐结论)

    **口径对齐**:
    - HI 0-100，等级与 /health/calculate 完全一致
    - 劣化模型(linear/exponential/polynomial)与 /rul/predict 完全一致
    - 风险评分体系一（BayesianRiskModel）：risk_score 1-10分（越高越安全），risk_level「低/中/高」（中文），与 /risk/assess 完全一致
    - 风险评分体系二（复检排程）：risk_score_100 0-100分（越高越危险），risk_status normal/warning/critical（英文），与 /alert/retest 完全一致
    - 双向映射：risk_score_100 = (10 - risk_score) / 9 × 100，risk_status = _risk_level_to_status(risk_level)
    - RUL天数定义为首次穿越failure_threshold的天数，与RUL模块一致
    - 推荐措施与 /alert/retest/schedule 风格一致
    """
    try:
        simulator = get_what_if_simulator()
        request_dict = request.model_dump()
        result = simulator.run_simulation(request_dict)
        return WhatIfSimulationResponse(**result)

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning(f"What-if仿真参数错误: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"What-if仿真执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 时序数据历史分析（兼容层：切到时序分析服务）
# ============================================================

@router.get(
    "/bolt/{sensor_id}/trend",
    tags=["时序历史分析"],
    summary="获取螺栓预紧力趋势（优先时序库）"
)
async def get_bolt_trend_compat(
    sensor_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    days: Optional[int] = Query(7, description="回溯天数（未指定start/end时使用）"),
    aggregation: Optional[str] = Query("auto", description="聚合级别: auto/raw/minute/hour"),
):
    """
    获取螺栓预紧力趋势（兼容旧接口，优先从时序库读取）

    - 若启用了时序库：使用时序分析服务读取（自动按时间范围选择聚合级别）
    - 否则：回退到 MySQL 读取原始数据

    返回格式与旧接口一致，可直接替换原有前端调用。
    """
    try:
        from app.timeseries.factory import is_timeseries_enabled, create_timeseries_repository
        from app.services.timeseries_service import get_timeseries_analysis_service
        from datetime import timedelta

        if is_timeseries_enabled():
            service = get_timeseries_analysis_service()
            # 默认回溯天数
            if start_time is None and end_time is None:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days or 7)

            result = service.get_trend(
                sensor_id=str(sensor_id),
                start_time=start_time,
                end_time=end_time,
                aggregation_level=aggregation,
            )

            # 兼容旧格式输出
            data_list = [
                {
                    'time': p['timestamp'],
                    'value': p.get('mean', p.get('value')),
                    'open': p.get('open'),
                    'high': p.get('high'),
                    'low': p.get('low'),
                    'close': p.get('close'),
                    'count': p.get('count'),
                }
                for p in result.get('points', [])
            ]

            return {
                'sensor_id': sensor_id,
                'datasource': 'timeseries',
                'aggregation': result.get('aggregation_level', aggregation),
                'total_points': len(data_list),
                'start_time': result.get('start_time'),
                'end_time': result.get('end_time'),
                'data': data_list,
                'statistics': result.get('statistics'),
            }

        # 回退：MySQL 读取原始数据
        from app.utils.database import get_bolt_recent_data
        limit = 5000
        recent = get_bolt_recent_data(
            sensor_id=int(sensor_id) if sensor_id.isdigit() else sensor_id,
            limit=limit
        )

        data_list = []
        for d in recent:
            data_list.append({
                'time': d.create_time.isoformat() if hasattr(d.create_time, 'isoformat') else str(d.create_time),
                'value': float(d.ptf),
            })

        return {
            'sensor_id': sensor_id,
            'datasource': 'mysql',
            'aggregation': 'raw',
            'total_points': len(data_list),
            'data': list(reversed(data_list)),  # 升序
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取螺栓趋势数据失败 [{sensor_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/bolt/{sensor_id}/statistics",
    tags=["时序历史分析"],
    summary="获取螺栓统计分析（优先时序库）"
)
async def get_bolt_statistics_compat(
    sensor_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    days: Optional[int] = Query(30, description="回溯天数"),
):
    """
    获取螺栓统计分析（均值、标准差、极值、趋势斜率等）

    - 时序库启用时：使用时序分析服务完整计算
    - 否则：使用 MySQL 数据计算基础统计
    """
    try:
        from app.timeseries.factory import is_timeseries_enabled
        from app.services.timeseries_service import get_timeseries_analysis_service
        from datetime import timedelta

        if is_timeseries_enabled():
            service = get_timeseries_analysis_service()
            if start_time is None and end_time is None:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days or 30)

            result = service.get_statistics(
                sensor_id=str(sensor_id),
                start_time=start_time,
                end_time=end_time,
            )
            result['datasource'] = 'timeseries'
            return result

        # 回退：MySQL 基础统计
        from app.utils.database import get_bolt_recent_data
        import numpy as np

        recent = get_bolt_recent_data(
            sensor_id=int(sensor_id) if sensor_id.isdigit() else sensor_id,
            limit=5000
        )
        if not recent:
            raise HTTPException(status_code=404, detail=f"无传感器 {sensor_id} 的数据")

        values = np.array([float(d.ptf) for d in recent])
        return {
            'sensor_id': sensor_id,
            'datasource': 'mysql',
            'count': int(len(values)),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'range': float(np.max(values) - np.min(values)),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取螺栓统计分析失败 [{sensor_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/bolt/{sensor_id}/compare-periods",
    tags=["时序历史分析"],
    summary="螺栓周期对比（同比/环比，优先时序库）"
)
async def get_bolt_period_compare_compat(
    sensor_id: str,
    request: dict,
):
    """
    螺栓周期对比（同比/环比）

    请求体:
        compare_type: "yoy"（同比）/ "mom"（环比）/ "custom"（自定义）
        start_time: 本期开始时间
        end_time: 本期结束时间
        baseline_start: 对比期开始时间（custom时必填）
        baseline_end: 对比期结束时间（custom时必填）
    """
    try:
        from app.timeseries.factory import is_timeseries_enabled
        from app.services.timeseries_service import get_timeseries_analysis_service

        if is_timeseries_enabled():
            service = get_timeseries_analysis_service()
            result = service.get_period_compare(
                sensor_id=str(sensor_id),
                compare_type=request.get('compare_type', 'mom'),
                current_start=request.get('start_time'),
                current_end=request.get('end_time'),
                baseline_start=request.get('baseline_start'),
                baseline_end=request.get('baseline_end'),
            )
            result['datasource'] = 'timeseries'
            return result

        raise HTTPException(
            status_code=400,
            detail="周期对比功能需要启用时序数据库"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"螺栓周期对比失败 [{sensor_id}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/timeseries/sql-query",
    tags=["时序历史分析"],
    summary="时序库原生 SQL 查询（历史分析，仅 TimescaleDB 支持）"
)
async def timeseries_sql_query_compat(
    sql: str = Query(..., description="SQL 查询语句"),
    timeout_seconds: int = Query(30, description="超时秒数"),
):
    """
    直接执行时序库 SQL 查询（用于复杂历史分析）

    **仅在启用 TimescaleDB 后端时可用**。
    可使用 time_bucket、continuous aggregate 等 Timescale 特性。
    """
    try:
        from app.timeseries.factory import is_timeseries_enabled, create_timeseries_repository
        from app.utils.config import config

        if not is_timeseries_enabled():
            raise HTTPException(
                status_code=400,
                detail="时序数据库未启用，无法执行 SQL 查询"
            )

        backend = config.get('timeseries.backend', '')
        if backend != 'timescaledb':
            raise HTTPException(
                status_code=400,
                detail=f"当前后端为 {backend}，仅 TimescaleDB 支持 SQL 查询"
            )

        repo = create_timeseries_repository()
        if repo is None:
            raise HTTPException(status_code=503, detail="时序数据库不可用")

        result = repo.execute_sql(sql, params={}, timeout_seconds=timeout_seconds)
        return {
            'success': True,
            'datasource': 'timescaledb',
            'row_count': len(result),
            'columns': list(result[0].keys()) if result else [],
            'rows': result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"时序 SQL 查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
