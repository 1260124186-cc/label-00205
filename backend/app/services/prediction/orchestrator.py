"""
预测编排器模块

按流水线方式组织预测流程：
    数据预处理 → 模型推断 → 风险评估 → 预警策略 → 审计快照 → 结果持久化

编排器本身不包含具体实现，而是通过组合以下组件完成：
- DataPreprocessor / FeatureEngineer: 数据预处理
- BoltLSTMModel / FlangeAttentionModel: 机器学习模型
- RuleBasedClassifier: 规则兜底
- BayesianRiskModel: 风险评估
- ProphetForecaster: 月度趋势预测
- WarningStrategyPolicy: 预警策略
- PredictionRepository: DB 读写
- AuditService / ExplainabilityService: 合规审计与可解释性
"""

import time
import os
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger

from app.models.bolt_lstm import BoltLSTMModel, STATUS_LABELS
from app.models.flange_attention import FlangeAttentionModel
from app.models.risk_model import BayesianRiskModel, RiskAssessment
from app.models.prophet_forecaster import ProphetForecaster
from app.models.fault_classifier import FaultClassifier, FaultType, FaultClassificationResult
from app.models.ensemble_model import BoltEnsemblePredictor, EnsemblePrediction
from app.models.working_condition_classifier import (
    WorkingCondition,
    WorkingConditionClassifier,
    WORKING_CONDITION_LABELS,
)
from app.models.condition_baseline import ConditionBaselineManager
from app.models.condition_adaptive_predictor import ConditionAdaptivePredictor
from app.services.preprocessing import DataPreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.services.prediction.rule_classifier import RuleBasedClassifier
from app.services.prediction.warning_strategy import WarningStrategyPolicy
from app.services.prediction.repository import PredictionRepository
from app.core.model_version import version_manager
from app.core.prometheus import metrics
from app.middleware import set_bolt_id
from app.utils.config import config

_data_quality_engine = None


def get_data_quality_engine():
    """获取数据质量引擎实例（懒加载）"""
    global _data_quality_engine
    if _data_quality_engine is None:
        from app.services.data_quality import DataQualityEngine
        _data_quality_engine = DataQualityEngine()
    return _data_quality_engine


class PredictionOrchestrator:
    """
    预测编排器（Orchestrator Pattern）

    以流水线方式协调各个子组件，完成完整的预测流程。
    不包含具体的业务逻辑实现，仅负责调用顺序与数据传递。

    Attributes:
        preprocessor: 数据预处理器
        feature_engineer: 特征工程师
        risk_model: 风险评估模型
        prophet: Prophet 月度预测器
        rule_classifier: 规则分类器（兜底）
        warning_policy: 预警策略
        repository: 数据仓库
        bolt_models: 螺栓模型缓存 {bolt_id: model}
        flange_models: 法兰面模型缓存 {flange_id: model}
    """

    def __init__(
        self,
        preprocessor: DataPreprocessor = None,
        feature_engineer: FeatureEngineer = None,
        risk_model: BayesianRiskModel = None,
        prophet: ProphetForecaster = None,
        rule_classifier: RuleBasedClassifier = None,
        warning_policy: WarningStrategyPolicy = None,
        repository: PredictionRepository = None,
        working_condition_classifier: WorkingConditionClassifier = None,
        condition_baseline_manager: ConditionBaselineManager = None,
        condition_adaptive_predictor: ConditionAdaptivePredictor = None,
    ):
        """
        初始化编排器，可注入依赖（便于测试）

        未提供的依赖会按默认构造。
        """
        self.preprocessor = preprocessor or DataPreprocessor()
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.risk_model = risk_model or BayesianRiskModel()
        self.prophet = prophet or ProphetForecaster()
        self.rule_classifier = rule_classifier or RuleBasedClassifier()
        self.warning_policy = warning_policy or WarningStrategyPolicy()
        self.repository = repository or PredictionRepository()
        self.fault_classifier = FaultClassifier()

        self.working_condition_classifier = working_condition_classifier or WorkingConditionClassifier()
        self.condition_baseline_manager = condition_baseline_manager or ConditionBaselineManager()
        self.condition_adaptive_predictor = condition_adaptive_predictor or ConditionAdaptivePredictor(
            classifier=self.working_condition_classifier,
            baseline_manager=self.condition_baseline_manager,
            prophet=self.prophet,
        )

        self.enable_working_condition = config.get('working_condition.enabled', True)
        self.condition_confidence_threshold = config.get(
            'working_condition.min_confidence_for_adjustment', 0.6
        )

        # 模型缓存：按版本缓存 {node_id: {version: model}}
        self.bolt_models: Dict[str, Dict[str, BoltLSTMModel]] = {}
        self.flange_models: Dict[str, Dict[str, FlangeAttentionModel]] = {}

        # 集成学习模型缓存 {bolt_id: {version: BoltEnsemblePredictor}}
        self.bolt_ensembles: Dict[str, Dict[str, BoltEnsemblePredictor]] = {}

        # Ensemble 配置
        self.ensemble_enabled = config.get('ensemble.enabled', True)
        self.ensemble_confidence_threshold = config.get(
            'ensemble.confidence_threshold', 0.7
        )

        logger.info("预测编排器初始化完成")

    # ---------- 模型管理 ----------

    def get_bolt_model(self, bolt_id: str, version: Optional[str] = None) -> BoltLSTMModel:
        """
        获取或创建螺栓 LSTM 模型（带版本缓存）

        Args:
            bolt_id: 螺栓ID
            version: 版本号，None 表示使用当前活动版本（默认路径）

        Returns:
            BoltLSTMModel 实例
        """
        cache_key = version or 'active'
        if bolt_id not in self.bolt_models:
            self.bolt_models[bolt_id] = {}

        if cache_key not in self.bolt_models[bolt_id]:
            if version is None:
                model = BoltLSTMModel.load_or_create(bolt_id)
            else:
                model = self._load_versioned_bolt_model(bolt_id, version)
            self.bolt_models[bolt_id][cache_key] = model

        return self.bolt_models[bolt_id][cache_key]

    def get_flange_model(self, flange_id: str, version: Optional[str] = None) -> FlangeAttentionModel:
        """
        获取或创建法兰面 Attention 模型（带版本缓存）

        Args:
            flange_id: 法兰面ID
            version: 版本号，None 表示使用当前活动版本（默认路径）

        Returns:
            FlangeAttentionModel 实例
        """
        cache_key = version or 'active'
        if flange_id not in self.flange_models:
            self.flange_models[flange_id] = {}

        if cache_key not in self.flange_models[flange_id]:
            if version is None:
                model = FlangeAttentionModel.load_or_create(flange_id)
            else:
                model = self._load_versioned_flange_model(flange_id, version)
            self.flange_models[flange_id][cache_key] = model

        return self.flange_models[flange_id][cache_key]

    def get_bolt_ensemble(
        self, bolt_id: str, version: Optional[str] = None
    ) -> BoltEnsemblePredictor:
        """
        获取或创建螺栓集成学习预测器（带版本缓存）

        Args:
            bolt_id: 螺栓ID
            version: 版本号，None 表示使用当前活动版本

        Returns:
            BoltEnsemblePredictor 实例
        """
        cache_key = version or 'active'
        if bolt_id not in self.bolt_ensembles:
            self.bolt_ensembles[bolt_id] = {}

        if cache_key not in self.bolt_ensembles[bolt_id]:
            ensemble = BoltEnsemblePredictor(
                bolt_id=bolt_id,
                version=version,
            )
            self.bolt_ensembles[bolt_id][cache_key] = ensemble

        return self.bolt_ensembles[bolt_id][cache_key]

    def _load_versioned_bolt_model(self, bolt_id: str, version: str) -> BoltLSTMModel:
        """
        加载指定版本的螺栓模型

        Args:
            bolt_id: 螺栓ID
            version: 版本号

        Returns:
            BoltLSTMModel 实例
        """
        from app.services.model_version_service import get_model_version_service

        service = get_model_version_service()
        model_path = service.get_model_file_path('bolt', bolt_id, version)

        if model_path is None or not os.path.exists(model_path):
            raise FileNotFoundError(f"未找到版本 {version} 的螺栓模型: {bolt_id}")

        model = BoltLSTMModel(bolt_id=bolt_id)
        model.load(model_path)
        logger.info(f"已加载螺栓模型版本: {bolt_id} v{version}")
        return model

    def _load_versioned_flange_model(self, flange_id: str, version: str) -> FlangeAttentionModel:
        """
        加载指定版本的法兰面模型

        Args:
            flange_id: 法兰面ID
            version: 版本号

        Returns:
            FlangeAttentionModel 实例
        """
        from app.services.model_version_service import get_model_version_service

        service = get_model_version_service()
        model_path = service.get_model_file_path('flange', flange_id, version)

        if model_path is None or not os.path.exists(model_path):
            raise FileNotFoundError(f"未找到版本 {version} 的法兰面模型: {flange_id}")

        model = FlangeAttentionModel(flange_id=flange_id)
        model.load(model_path)
        logger.info(f"已加载法兰面模型版本: {flange_id} v{version}")
        return model

    def reload_model(self, model_type: str, node_id: str, version: Optional[str] = None) -> None:
        """
        重新加载模型（清除缓存）

        Args:
            model_type: 模型类型 bolt/flange
            node_id: 节点ID
            version: 版本号，None 表示活动版本
        """
        cache_key = version or 'active'
        if model_type == 'bolt':
            if node_id in self.bolt_models and cache_key in self.bolt_models[node_id]:
                del self.bolt_models[node_id][cache_key]
                logger.info(f"已清除螺栓模型缓存: {node_id} v{cache_key}")
            if node_id in self.bolt_ensembles and cache_key in self.bolt_ensembles[node_id]:
                del self.bolt_ensembles[node_id][cache_key]
                logger.info(f"已清除螺栓Ensemble缓存: {node_id} v{cache_key}")
        elif model_type == 'flange':
            if node_id in self.flange_models and cache_key in self.flange_models[node_id]:
                del self.flange_models[node_id][cache_key]
                logger.info(f"已清除法兰面模型缓存: {node_id} v{cache_key}")

    # ---------- 螺栓预测 ----------

    def predict_bolt(
        self,
        bolt_id: str,
        data: np.ndarray,
        timestamps: Optional[List[str]] = None,
        save_to_db: bool = True,
        version: Optional[str] = None,
        shadow_version: Optional[str] = None,
        generate_diagnosis: bool = False,
    ) -> Dict[str, Any]:
        """
        螺栓状态预测（完整流水线）

        流程: 预处理 → 模型/规则 → 风险评估 → 预警策略 → 审计快照 → 持久化

        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据
            timestamps: 时间戳列表
            save_to_db: 是否保存到数据库
            version: 使用指定版本的模型（None 表示当前活动版本）
            shadow_version: 影子版本号（Shadow Mode），仅运行预测不写库，用于A/B对比
            generate_diagnosis: 是否生成 LLM 智能诊断报告（默认 False）

        Returns:
            预测结果字典，包含 shadow_result（如果指定了 shadow_version）和 diagnosis_report（如果启用）
        """
        start_time = time.time()
        set_bolt_id(str(bolt_id))

        logger.info(f"开始螺栓预测: {bolt_id}, 数据点数: {len(data)}, version={version or 'active'}, shadow_version={shadow_version}, generate_diagnosis={generate_diagnosis}")

        # 主版本预测
        main_result = self._run_bolt_prediction(
            bolt_id=bolt_id,
            data=data,
            timestamps=timestamps,
            version=version,
            save_to_db=save_to_db,
            is_shadow=False,
            generate_diagnosis=generate_diagnosis,
        )

        # Shadow Mode：副版本仅预测，不写库，不触发告警
        if shadow_version and shadow_version != version:
            try:
                shadow_result = self._run_bolt_prediction(
                    bolt_id=bolt_id,
                    data=data,
                    timestamps=timestamps,
                    version=shadow_version,
                    save_to_db=False,
                    is_shadow=True,
                    generate_diagnosis=False,
                )
                main_result['shadow_result'] = shadow_result
                main_result['shadow_version'] = shadow_version

                logger.info(
                    f"Shadow模式预测完成: 螺栓 {bolt_id}, "
                    f"主版本={version or 'active'} -> {main_result['status']}, "
                    f"影子版本={shadow_version} -> {shadow_result['status']}"
                )
            except Exception as e:
                logger.warning(f"Shadow版本预测失败: {e}")
                main_result['shadow_error'] = str(e)

        duration = time.time() - start_time
        logger.info(f"螺栓预测完成: {bolt_id} -> {main_result['status']}, 耗时: {duration*1000:.2f}ms")
        return main_result

    def predict_bolt_ensemble(
        self,
        bolt_id: str,
        data: np.ndarray,
        version: Optional[str] = None,
        method: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        螺栓集成学习预测调试接口

        返回各子模型分项结果与最终融合结论，用于调试和分析。

        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据
            version: 模型版本号
            method: 投票策略 (hard/soft/weighted)，None 使用配置默认值
            weights: 自定义权重 {predictor_name: weight}

        Returns:
            Dict: 包含各子模型结果和最终融合结果的详细信息
        """
        start_time = time.time()
        set_bolt_id(str(bolt_id))

        logger.info(
            f"开始螺栓Ensemble调试预测: {bolt_id}, "
            f"数据点数: {len(data)}, method={method}, version={version or 'active'}"
        )

        processed = self.preprocessor.process(
            data,
            remove_anomalies=True,
            normalize=True,
            smooth=True,
        )

        ensemble = self.get_bolt_ensemble(bolt_id, version=version)

        if method is not None:
            try:
                ensemble.set_method(method)
            except ValueError as e:
                logger.warning(f"设置投票策略失败: {e}")

        if weights is not None:
            ensemble.set_weights(weights)

        ensemble_result = ensemble.predict(processed.data)
        detail_result = ensemble.predict_with_details(processed.data)

        duration = time.time() - start_time

        individual_probs_list = {}
        for name, probs in ensemble_result.individual_probs.items():
            individual_probs_list[name] = probs.tolist() if probs is not None else None

        result = {
            'bolt_id': bolt_id,
            'prediction_source': ensemble_result.prediction_source,
            'ensemble_method': ensemble_result.method,
            'final_status': detail_result['status'],
            'final_status_code': detail_result['status_code'],
            'final_confidence': float(ensemble_result.final_confidence),
            'final_probs': (
                ensemble_result.final_probs.tolist()
                if ensemble_result.final_probs is not None
                else None
            ),
            'weights': ensemble_result.weights,
            'individual_results': detail_result['individual_results'],
            'individual_probs': individual_probs_list,
            'model_version': version or 'active',
            'duration_ms': duration * 1000,
            'ema_accuracy': ensemble.get_ema_accuracy(),
            'performance_history': ensemble.get_performance_history(),
        }

        logger.info(
            f"螺栓Ensemble调试预测完成: {bolt_id} -> {result['final_status']}, "
            f"耗时: {duration*1000:.2f}ms"
        )

        return result

    def update_ensemble_weights(
        self,
        bolt_id: str,
        performance_metrics: Dict[str, float],
        version: Optional[str] = None,
        use_ema: bool = True,
    ) -> Dict[str, float]:
        """
        更新集成学习预测器权重（基于历史表现动态调权）

        Args:
            bolt_id: 螺栓ID
            performance_metrics: {predictor_name: accuracy_score}
            version: 模型版本号
            use_ema: 是否使用 EMA 平滑

        Returns:
            Dict: 更新后的权重
        """
        ensemble = self.get_bolt_ensemble(bolt_id, version=version)
        new_weights = ensemble.update_weights(
            performance_metrics, use_ema=use_ema
        )

        logger.info(
            f"Ensemble权重已更新: 螺栓 {bolt_id}, "
            f"新权重: {new_weights}"
        )

        return new_weights

    def get_ensemble_weights(
        self,
        bolt_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        获取集成学习预测器当前权重

        Args:
            bolt_id: 螺栓ID
            version: 模型版本号

        Returns:
            Dict: 当前权重 {predictor_name: weight}
        """
        ensemble = self.get_bolt_ensemble(bolt_id, version=version)
        return ensemble.get_weights()

    def _run_bolt_prediction(
        self,
        bolt_id: str,
        data: np.ndarray,
        timestamps: Optional[List[str]],
        version: Optional[str],
        save_to_db: bool,
        is_shadow: bool = False,
        generate_diagnosis: bool = False,
    ) -> Dict[str, Any]:
        """
        执行单次螺栓预测（核心预测流水线）

        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据
            timestamps: 时间戳列表
            version: 模型版本号
            save_to_db: 是否保存到数据库
            is_shadow: 是否为影子模式（仅记录日志，不触发告警）
            generate_diagnosis: 是否生成 LLM 智能诊断报告

        Returns:
            预测结果字典
        """
        original_status_code = 0
        original_status = ''
        model_type = 'rule'
        probs = None
        prediction_source = 'rule'
        ensemble_result: Optional[EnsemblePrediction] = None

        # Step 1: 数据预处理
        processed = self.preprocessor.process(
            data,
            remove_anomalies=True,
            normalize=True,
            smooth=True,
        )

        # Step 2: 加载模型
        model = self.get_bolt_model(bolt_id, version=version)
        model_version_str = version or 'unknown'

        # Step 1.5: 特征工程（可选，配置开关控制）
        fe_cfg = config.get('feature_engineering', {})
        fe_enabled = fe_cfg.get('enabled', True)
        feature_vector = None
        if fe_enabled and model.is_trained:
            try:
                raw_feature = self.feature_engineer.extract_features(processed.data)
                if raw_feature.size > 0:
                    scaler_state = getattr(model, '_feature_scaler_state', None)
                    if scaler_state is not None:
                        self.feature_engineer.set_scaler_state(scaler_state)
                    feature_vector = self.feature_engineer.transform_features(raw_feature)
            except Exception as e:
                logger.warning(f"螺栓 {bolt_id} 特征提取失败，跳过特征辅助: {e}")
                feature_vector = None

        # Step 2: 模型推断（模型未训练则规则兜底）
        if model.is_trained:
            if version is None:
                model_version_str = self._get_model_version('bolt', bolt_id)

            original_status_code, confidence, probs = model.predict(
                processed.data,
                return_proba=True,
                features=feature_vector,
            )
            model_type = 'lstm'
            prediction_source = 'lstm'
        else:
            original_status_code, confidence, probs = self.rule_classifier.predict(data)
            model_type = 'rule'
            prediction_source = 'rule'

        original_status = STATUS_LABELS.get(original_status_code, '未知')

        # Step 3: 数据质量评估与置信度调整
        dq_enabled = config.get('data_quality.enabled', True)
        auto_adjust = config.get(
            'data_quality.integration.auto_adjust_prediction_confidence', True
        )

        quality_info = {}
        if dq_enabled and auto_adjust:
            try:
                ts_array = None
                if timestamps:
                    from datetime import datetime
                    ts_array = np.array([
                        datetime.fromisoformat(t.replace('Z', '+00:00'))
                        if isinstance(t, str) else t
                        for t in timestamps
                    ])

                dq_engine = get_data_quality_engine()
                check_result, quality_score = dq_engine.evaluate_quality_only(
                    sensor_id=bolt_id,
                    values=data,
                    timestamps=ts_array,
                )

                filter_result = dq_engine.data_filter.filter_for_prediction(
                    data=data,
                    timestamps=ts_array,
                    check_result=check_result,
                    quality_score=quality_score,
                )

                adjusted_confidence = dq_engine.data_filter.adjust_prediction_confidence(
                    original_confidence=confidence,
                    quality_score=quality_score,
                    filter_result=filter_result,
                )

                quality_info = {
                    'quality_score': quality_score.overall_score,
                    'quality_level': quality_score.overall_level.value,
                    'original_confidence': float(confidence),
                    'adjusted_confidence': float(adjusted_confidence),
                    'adjustment_factor': adjusted_confidence / max(confidence, 0.0001),
                    'valid_for_training': quality_score.valid_for_training,
                    'confidence_adjustment': quality_score.confidence_adjustment,
                }

                if adjusted_confidence != confidence:
                    logger.info(
                        f"置信度调整: 螺栓 {bolt_id}, "
                        f"原始 {confidence:.3f} → 调整后 {adjusted_confidence:.3f}, "
                        f"质量评分 {quality_score.overall_score:.1f}"
                    )

                confidence = adjusted_confidence
            except Exception as e:
                logger.warning(f"数据质量置信度调整失败，使用原始置信度: {e}")
                quality_info = {'error': str(e)}

        # Step 3.5: Ensemble 二次裁决（LSTM 置信度低于阈值时触发）
        if (
            self.ensemble_enabled
            and model_type == 'lstm'
            and confidence < self.ensemble_confidence_threshold
        ):
            try:
                ensemble = self.get_bolt_ensemble(bolt_id, version=version)
                ensemble_result = ensemble.predict(processed.data)

                logger.info(
                    f"Ensemble 二次裁决: 螺栓 {bolt_id}, "
                    f"LSTM置信度 {confidence:.3f} < 阈值 {self.ensemble_confidence_threshold}, "
                    f"LSTM状态 {original_status} ({original_status_code}) → "
                    f"Ensemble状态 {STATUS_LABELS[ensemble_result.final_prediction]} ({ensemble_result.final_prediction}), "
                    f"Ensemble置信度 {ensemble_result.final_confidence:.3f}, "
                    f"策略={ensemble_result.method}"
                )

                if ensemble_result.final_confidence >= confidence:
                    original_status_code = ensemble_result.final_prediction
                    confidence = ensemble_result.final_confidence
                    if ensemble_result.final_probs is not None:
                        probs = ensemble_result.final_probs
                    original_status = STATUS_LABELS.get(
                        ensemble_result.final_prediction, '未知'
                    )
                    prediction_source = 'ensemble'

            except Exception as e:
                logger.warning(f"Ensemble 二次裁决失败，使用原始结果: {e}")

        # Step 3.6: 工况识别与自适应调整
        working_condition_info = {}
        condition_prediction = None
        if self.enable_working_condition and len(data) >= 50:
            try:
                condition_prediction = self.condition_adaptive_predictor.predict(
                    node_id=str(bolt_id),
                    data=data,
                    forecast_days=1,
                    node_type='bolt',
                )

                condition = condition_prediction.condition
                condition_label = condition_prediction.condition_label
                condition_conf = condition_prediction.condition_confidence

                working_condition_info = {
                    'condition': condition.value,
                    'condition_label': condition_label,
                    'confidence': condition_conf,
                    'is_transition': condition_prediction.is_transition,
                    'condition_changed': condition_prediction.condition_changed,
                    'previous_condition': (
                        condition_prediction.previous_condition.value
                        if condition_prediction.previous_condition else None
                    ),
                    'probabilities': {
                        cond.value: prob
                        for cond, prob in condition_prediction.condition_probabilities.items()
                    },
                    'baseline_anomaly': {
                        'status': condition_prediction.overall_status,
                        'anomaly_count': condition_prediction.anomaly_summary.get('anomaly_count', 0),
                        'warning_count': condition_prediction.anomaly_summary.get('warning_count', 0),
                        'anomaly_ratio': condition_prediction.anomaly_summary.get('anomaly_ratio', 0.0),
                    },
                    'baseline': condition_prediction.baseline,
                }

                # ---- 3.6a: 基线异常检测修正状态码 ----
                if condition_conf >= self.condition_confidence_threshold:
                    baseline_anomaly_count = condition_prediction.anomaly_summary.get('anomaly_count', 0)
                    baseline_warning_count = condition_prediction.anomaly_summary.get('warning_count', 0)
                    total_points = len(data) if len(data) > 0 else 1
                    anomaly_ratio = baseline_anomaly_count / total_points
                    warning_ratio = baseline_warning_count / total_points

                    condition_status_override = None

                    if anomaly_ratio >= 0.3:
                        condition_status_override = max(original_status_code, 3)
                        logger.info(
                            f"工况基线异常升级: 螺栓 {bolt_id}, "
                            f"工况={condition_label}, 异常率={anomaly_ratio:.1%}, "
                            f"状态码 {original_status_code} → {condition_status_override}"
                        )
                    elif anomaly_ratio >= 0.1:
                        condition_status_override = max(original_status_code, 2)
                        logger.info(
                            f"工况基线异常升级: 螺栓 {bolt_id}, "
                            f"工况={condition_label}, 异常率={anomaly_ratio:.1%}, "
                            f"状态码 {original_status_code} → {condition_status_override}"
                        )
                    elif warning_ratio >= 0.3 and original_status_code == 0:
                        condition_status_override = 1
                        logger.info(
                            f"工况基线预警升级: 螺栓 {bolt_id}, "
                            f"工况={condition_label}, 预警率={warning_ratio:.1%}, "
                            f"状态码 0 → 1"
                        )

                    if condition_status_override is not None:
                        original_status_code = condition_status_override
                        original_status = STATUS_LABELS.get(original_status_code, '未知')

                    # ---- 3.6b: 工况自适应置信度调整 ----
                    adjusted_confidence = self._adjust_confidence_by_condition(
                        confidence, condition, original_status_code
                    )
                    if abs(adjusted_confidence - confidence) > 0.001:
                        logger.info(
                            f"工况置信度调整: 螺栓 {bolt_id}, "
                            f"工况={condition_label}, "
                            f"原始置信度 {confidence:.3f} → 调整后 {adjusted_confidence:.3f}"
                        )
                        confidence = adjusted_confidence

                # ---- 3.6c: 增量更新基线 ----
                self.condition_baseline_manager.update_baseline(
                    condition, data, incremental=True
                )

                # ---- 3.6d: 工况变更审计 ----
                if condition_prediction.condition_changed:
                    self._record_condition_change_audit(
                        bolt_id=str(bolt_id),
                        condition_result=condition_prediction,
                        node_type='bolt',
                    )

            except Exception as e:
                logger.warning(f"工况识别失败，跳过: {e}")
                working_condition_info = {'error': str(e)}

        # Step 4: 风险评估（融合工况信息）
        condition_for_risk = (
            condition_prediction.condition
            if condition_prediction else None
        )
        risk_assessment = self._assess_risk_with_condition(
            data=data,
            lstm_probs=probs,
            lstm_class=original_status_code,
            node_type='bolt',
            node_id=bolt_id,
            condition=condition_for_risk,
        )

        # Step 5: 应用预警策略（融合工况信息）
        final_status_code, final_status = self._apply_warning_with_condition(
            original_status_code=original_status_code,
            original_status=original_status,
            confidence=confidence,
            risk_assessment=risk_assessment,
            condition=condition_for_risk,
            bolt_id=bolt_id,
        )

        # 推荐措施（优先用模型建议，兜底使用风险评估建议）
        recommendations = model.get_recommendation(final_status_code, confidence)

        # Step 5.5: CBR 知识库检索（相似案例与推荐措施增强）
        similar_cases = []
        rag_context = ''
        cbr_enabled = config.get('cbr.enabled', True)
        cbr_in_prediction = config.get('cbr.integration.in_prediction', True)

        if cbr_enabled and cbr_in_prediction and final_status_code > 0:
            try:
                from app.services.knowledge import KnowledgeService
                from app.services.feature_engineering import FeatureEngineer

                cbr_service = KnowledgeService()
                fe = FeatureEngineer()

                # 提取特征用于相似度检索
                try:
                    feature_set = fe.extract_features(data)
                    feature_vector = feature_set.combined_features.tolist()
                except Exception:
                    feature_vector = None

                fault_type_mapping = {
                    1: 'loosening',
                    2: 'preload_decrease',
                    3: 'severe_anomaly',
                    4: 'failure',
                }
                fault_type = fault_type_mapping.get(final_status_code)

                cbr_result = cbr_service.get_case_recommendations(
                    node_type='bolt',
                    node_id=bolt_id,
                    fault_type=fault_type,
                    fault_level=final_status_code if final_status_code > 0 else None,
                    feature_vector=feature_vector,
                    top_k=config.get('cbr.integration.top_k', 3),
                    min_similarity=config.get('cbr.integration.min_similarity', 0.4),
                    only_approved=True,
                )

                similar_cases = cbr_result.get('cases', [])
                rag_context = cbr_result.get('rag_context', '')

                # 合并推荐措施（知识库推荐 + 原推荐）
                cbr_recommendations = cbr_result.get('aggregated_recommendations', [])
                if cbr_recommendations:
                    combined_recs = []
                    seen = set()
                    # 优先加入知识库推荐
                    for rec in cbr_recommendations:
                        if rec and rec not in seen:
                            seen.add(rec)
                            combined_recs.append(rec)
                    # 再加入原推荐
                    for rec in risk_assessment.recommendations:
                        if rec and rec not in seen:
                            seen.add(rec)
                            combined_recs.append(rec)
                    risk_assessment.recommendations = combined_recs[:10]
                    logger.info(
                        f"CBR推荐已合并: 螺栓 {bolt_id}, "
                        f"找到 {len(similar_cases)} 个相似案例, "
                        f"推荐措施 {len(combined_recs)} 条"
                    )
            except Exception as e:
                logger.warning(f"CBR知识库检索失败，跳过: {e}")

        fault_detail = None
        if final_status_code >= 3 and not is_shadow:
            try:
                fault_result = self.fault_classifier.classify(data)
                fault_detail = self._build_fault_detail(fault_result)
                if fault_result.fault_type != FaultType.NORMAL and fault_result.fault_type != FaultType.UNKNOWN:
                    fault_recs = fault_result.recommendations
                    existing_recs = set(risk_assessment.recommendations)
                    for rec in fault_recs:
                        if rec and rec not in existing_recs:
                            risk_assessment.recommendations.append(rec)
                    logger.info(
                        f"故障分类完成: 螺栓 {bolt_id}, "
                        f"fault_type={fault_result.fault_type.value}, "
                        f"confidence={fault_result.confidence:.3f}"
                    )
            except Exception as e:
                logger.warning(f"故障分类失败，跳过: {e}")

        ensemble_detail = None
        if ensemble_result is not None:
            ensemble_detail = {
                'method': ensemble_result.method,
                'triggered': True,
                'final_prediction': ensemble_result.final_prediction,
                'final_confidence': float(ensemble_result.final_confidence),
                'individual_predictions': ensemble_result.individual_predictions,
                'individual_confidences': {
                    k: float(v) for k, v in ensemble_result.individual_confidences.items()
                },
                'weights': ensemble_result.weights,
            }

        result = {
            'bolt_id': bolt_id,
            'status': final_status,
            'status_code': final_status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations,
            'recent_time': timestamps[-1] if timestamps else None,
            'model_version': model_version_str,
            'model_type': model_type,
            'prediction_source': prediction_source,
            'is_shadow': is_shadow,
            'data_quality': quality_info if quality_info else None,
            'similar_cases': [
                {
                    'id': c.id,
                    'case_no': c.case_no,
                    'case_title': c.case_title,
                    'fault_type': c.fault_type,
                    'effectiveness_score': c.effectiveness_score,
                    'similarity_score': getattr(c, 'similarity_score', None),
                }
                for c in similar_cases
            ] if similar_cases else [],
            'rag_context': rag_context,
            'fault_detail': fault_detail,
            'ensemble': ensemble_detail,
            'working_condition': working_condition_info if working_condition_info else None,
        }

        # Step 5: 审计快照
        try:
            self._record_audit_snapshot(
                node_type='bolt',
                node_id=bolt_id,
                input_data=data,
                processed_data=processed.data,
                model_version=model_version_str,
                model_type=model_type,
                original_status_code=original_status_code,
                confidence=float(confidence),
                probs=probs,
                risk_assessment=risk_assessment,
                final_status_code=final_status_code,
                final_status=final_status,
                recommendations=risk_assessment.recommendations,
                working_condition=working_condition_info if working_condition_info else None,
            )
        except Exception as e:
            logger.warning(f"螺栓 {bolt_id} 审计快照记录异常: {e}")

        # Step 6: 持久化（Shadow 模式不写库）
        if save_to_db and not is_shadow:
            self.repository.save_bolt_prediction(bolt_id, result)

        # Step 7: 告警评估（Shadow 模式不触发告警）
        if not is_shadow:
            try:
                self._evaluate_alert(
                    node_type='bolt',
                    node_id=bolt_id,
                    result=result,
                )
            except Exception as e:
                logger.warning(f"螺栓 {bolt_id} 告警评估异常: {e}")

        # 记录预测指标
        metrics.record_prediction(
            node_type='bolt',
            status_code=final_status_code,
            status_label=final_status,
            duration=0,
            model_type=model_type
        )

        # Step 8: LLM 智能诊断报告（可选）
        if generate_diagnosis and not is_shadow:
            try:
                from app.services.report import get_diagnosis_report_service
                diagnosis_service = get_diagnosis_report_service()

                fault_type_mapping = {
                    1: 'loosening',
                    2: 'preload_decrease',
                    3: 'severe_anomaly',
                    4: 'failure',
                }
                fault_type = fault_type_mapping.get(final_status_code)

                recent_values = None
                if data is not None and len(data) > 0:
                    recent_values = [float(v) for v in data[-20:]]

                diagnosis_report = diagnosis_service.generate_single_report(
                    status=final_status,
                    risk_score=float(risk_assessment.score),
                    node_type='bolt',
                    node_id=str(bolt_id),
                    fault_type=fault_type,
                    trend=None,
                    recent_values=recent_values,
                    historical_incidents=None,
                )

                result['diagnosis_report'] = {
                    'diagnosis_summary': diagnosis_report.diagnosis_summary,
                    'recommended_actions': diagnosis_report.recommended_actions,
                    'urgency_level': diagnosis_report.urgency_level.value if hasattr(diagnosis_report.urgency_level, 'value') else diagnosis_report.urgency_level,
                    'model': diagnosis_report.model,
                    'tokens_used': diagnosis_report.tokens_used,
                    'latency_ms': diagnosis_report.latency_ms,
                    'is_fallback': diagnosis_report.is_fallback,
                }

                logger.info(
                    f"LLM诊断报告生成完成: 螺栓 {bolt_id}, "
                    f"紧急程度={result['diagnosis_report']['urgency_level']}, "
                    f"模型={diagnosis_report.model}, "
                    f"耗时={diagnosis_report.latency_ms:.2f}ms"
                )
            except Exception as e:
                logger.warning(f"LLM诊断报告生成失败，跳过: {e}")
                result['diagnosis_report'] = None

        return result

    # ---------- 多变量螺栓预测 ----------

    def predict_bolt_multivariate(
        self,
        bolt_id: str,
        channels_data: Optional[Dict[str, Tuple[np.ndarray, np.ndarray]]] = None,
        aligned_array: Optional[np.ndarray] = None,
        aligned_channel_names: Optional[List[str]] = None,
        target_timestamps: Optional[np.ndarray] = None,
        apply_temp_compensation: bool = True,
        enable_degradation: bool = True,
        version: Optional[str] = None,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        螺栓多变量耦合预测（完整流水线）

        支持两种输入方式：
        1. channels_data: 分通道提供（各通道时间戳可不同，服务端自动对齐插值）
        2. aligned_array + aligned_channel_names: 已对齐的 (N, C) 数组 + 通道名

        流水线:
            请求解析 → 多通道对齐/插值 → 降级判断 → 温度耦合补偿 → 模型推断
            → 特征重要性 → 风险评估 → 预警策略 → 审计快照 → 持久化

        Args:
            bolt_id: 螺栓ID
            channels_data: 分通道数据 {channel_name: (timestamps, values)}，推荐使用
            aligned_array: 形状 (N, C)，已对齐的多通道数据
            aligned_channel_names: 对应列的通道名，长度 = C
            target_timestamps: 可选的统一目标时间网格
            apply_temp_compensation: 是否执行温度耦合补偿（默认 True）
            enable_degradation: 缺失严重时是否降级为单变量预测（默认 True）
            version: 模型版本号
            save_to_db: 是否保存结果到数据库

        Returns:
            Dict: 包含标准预测字段 + 多变量扩展字段（data_quality / feature_importance / temp_compensation 等）
        """
        from datetime import datetime as _dt
        from app.services.preprocessing import (
            MultivariatePreprocessor,
            MultivariatePreprocessingResult,
        )
        from app.models.multivariate_model import (
            MultivariatePredictor,
            MultivariateInput,
            TemperatureCouplingModel,
        )

        start_time = time.time()
        set_bolt_id(str(bolt_id))

        logger.info(
            f"开始多变量螺栓预测: {bolt_id}, "
            f"channels方式={'是' if channels_data else '否'}, "
            f"aligned方式={'是(C=' + str(aligned_array.shape[1]) + ')' if aligned_array is not None else '否'}, "
            f"version={version or 'active'}"
        )

        # ============== Step 1: 多变量预处理（对齐 + 插值 + 降级） ==============
        mv_preprocessor = MultivariatePreprocessor(
            interpolation_method='linear',
            normalize_mode='channel_wise',
            smooth_each_channel=True,
            min_complete_ratio=0.5,
            allow_degraded=enable_degradation,
            fallback_channel='preload',
        )

        mv_result: MultivariatePreprocessingResult
        if channels_data is not None and len(channels_data) > 0:
            # 分通道对齐模式
            mv_result = mv_preprocessor.process(
                channels_data,
                target_timestamps=target_timestamps,
                normalize=False,
                smooth=True,
            )
        elif aligned_array is not None and aligned_channel_names is not None:
            # 已对齐数组模式
            mv_result = mv_preprocessor.process_from_arrays(
                aligned_array,
                aligned_channel_names,
                timestamps=target_timestamps,
            )
            # 补做平滑
            mv_result = mv_preprocessor.smooth_multivariate(mv_result)
        else:
            raise ValueError(
                "必须提供 channels_data 或 aligned_array+aligned_channel_names"
            )

        # 归一化（独立于对齐步骤）
        mv_result = mv_preprocessor.normalize_multivariate(mv_result, fit=True)

        actual_channels = mv_result.channels
        input_dim_actual = len(actual_channels)
        is_degraded = mv_result.data_quality == 'degraded'
        prediction_source = (
            'degraded_univariate' if is_degraded else 'multivariate_lstm'
        )

        # ============== Step 2: 温度耦合补偿（可选） ==============
        temp_comp_info = None
        data_for_model = mv_result.data.copy()  # (N, C)
        preload_col_idx = None
        temp_col_idx = None

        try:
            if 'preload' in actual_channels:
                preload_col_idx = actual_channels.index('preload')
            if 'temperature' in actual_channels:
                temp_col_idx = actual_channels.index('temperature')
        except Exception:
            pass

        if (
            apply_temp_compensation
            and preload_col_idx is not None
            and temp_col_idx is not None
        ):
            try:
                temp_model = TemperatureCouplingModel()
                preload_raw = mv_result.data[:, preload_col_idx]
                temp_raw = mv_result.data[:, temp_col_idx]
                temp_analysis = temp_model.analyze_effect(preload_raw, temp_raw)
                compensated = temp_model.compensate(preload_raw, temp_raw)
                data_for_model[:, preload_col_idx] = compensated

                temp_comp_info = {
                    'applied': True,
                    'temperature_coefficient': float(temp_analysis.get('coefficient', 0.0)),
                    'correlation': float(temp_analysis.get('correlation', 0.0)),
                    'original_mean_preload': float(np.nanmean(preload_raw)),
                    'compensated_mean_preload': float(np.nanmean(compensated)),
                    'delta_t_mean': float(np.nanmean(np.abs(temp_raw - np.nanmean(temp_raw)))),
                }
                logger.info(
                    f"温度耦合补偿完成: 螺栓 {bolt_id}, "
                    f"系数α={temp_comp_info['temperature_coefficient']:.4f} kN/°C, "
                    f"相关系数={temp_comp_info['correlation']:.3f}"
                )
            except Exception as e:
                logger.warning(f"温度耦合补偿失败，跳过: {e}")
                temp_comp_info = {'applied': False, 'error': str(e)}
        else:
            temp_comp_info = {'applied': False}

        # ============== Step 3: 模型推断 ==============
        # 从补偿后数据中抽取 preload 用于风险评估和规则兜底
        preload_for_risk = (
            data_for_model[:, preload_col_idx]
            if preload_col_idx is not None
            else data_for_model[:, 0]
        )

        original_status_code = 0
        confidence = 0.0
        probs = None
        model_version_str = version or 'unknown'
        feature_importance = None

        # 尝试使用多变量模型；若缺失通道则回退到单变量 BoltLSTMModel
        if not is_degraded and input_dim_actual >= 2:
            try:
                mv_predictor = MultivariatePredictor(
                    bolt_id=bolt_id,
                    input_dim=input_dim_actual,
                )
                # 组装 MultivariateInput
                mv_input = self._build_multivariate_input(
                    mv_result, data_for_model
                )
                pred_output = mv_predictor.predict(
                    mv_input,
                    apply_temp_compensation=False,
                )
                original_status_code = int(pred_output.status_code)
                confidence = float(pred_output.confidence)
                if hasattr(pred_output, 'probs') and pred_output.probs is not None:
                    probs = np.asarray(pred_output.probs, dtype=np.float32)
                if hasattr(pred_output, 'feature_importance'):
                    feature_importance = pred_output.feature_importance
                prediction_source = 'multivariate_lstm'
                logger.info(
                    f"多变量LSTM预测: 螺栓 {bolt_id}, "
                    f"input_dim={input_dim_actual}, "
                    f"status={original_status_code}, confidence={confidence:.3f}"
                )
            except Exception as e:
                logger.warning(
                    f"多变量LSTM预测失败，回退到单变量BoltLSTMModel: {e}"
                )
                original_status_code, confidence, probs = self._fallback_predict_bolt(
                    bolt_id, preload_for_risk, version
                )
                prediction_source = 'fallback'
        else:
            # 降级或单通道模式：直接用 BoltLSTMModel
            original_status_code, confidence, probs = self._fallback_predict_bolt(
                bolt_id, preload_for_risk, version
            )
            if version is None:
                model_version_str = self._get_model_version('bolt', bolt_id)
            logger.info(
                f"单变量BoltLSTM预测(降级或单通道): 螺栓 {bolt_id}, "
                f"status={original_status_code}, confidence={confidence:.3f}"
            )

        original_status = STATUS_LABELS.get(original_status_code, '未知')

        # ============== Step 4: 风险评估 ==============
        risk_assessment = self.risk_model.assess_risk(
            preload_for_risk,
            lstm_probs=probs,
            lstm_class=original_status_code,
            node_type='bolt',
            node_id=bolt_id,
        )

        # ============== Step 5: 预警策略 ==============
        final_status_code, final_status = self.warning_policy.apply(
            original_status_code, original_status, confidence,
            risk_level=risk_assessment.level.value,
            lstm_confidence=float(confidence),
        )

        # 获取推荐措施
        try:
            bolt_model = self.get_bolt_model(bolt_id, version=version)
            recommendations = bolt_model.get_recommendation(
                final_status_code, confidence
            )
        except Exception:
            recommendations = risk_assessment.recommendations

        # 合并风险评估推荐
        all_recs = list(recommendations) if isinstance(recommendations, list) else [recommendations]
        for r in risk_assessment.recommendations:
            if r and r not in all_recs:
                all_recs.append(r)

        # ============== Step 6: 特征重要性标准化 ==============
        if feature_importance is None:
            feature_importance = self._estimate_feature_importance(
                mv_result, final_status_code
            )

        # 通道元数据信息
        default_units = {
            'preload': 'kN',
            'temperature': '°C',
            'humidity': '%',
            'vibration': 'g',
            'vibration_x': 'g',
            'vibration_y': 'g',
            'vibration_z': 'g',
            'torque': 'N·m',
            'pressure': 'MPa',
            'axial_force': 'kN',
            'strain': 'με',
            'rpm': 'RPM',
        }
        default_desc = {
            'preload': '预紧力',
            'temperature': '环境温度',
            'humidity': '环境湿度',
            'vibration': '振动加速度',
            'vibration_x': 'X轴振动',
            'vibration_y': 'Y轴振动',
            'vibration_z': 'Z轴振动',
            'torque': '拧紧扭矩',
            'pressure': '介质压力',
            'axial_force': '轴向力',
            'strain': '应变',
            'rpm': '转速',
        }
        channels_info = [
            {
                'name': ch,
                'unit': default_units.get(ch),
                'description': default_desc.get(ch),
            }
            for ch in actual_channels
        ]

        # ============== Step 7: 组装响应 ==============
        result = {
            'bolt_id': bolt_id,
            'status': final_status,
            'status_code': final_status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': all_recs[:10],
            'prediction_time': _dt.now(),
            'model_version': model_version_str,
            'input_dim_actual': input_dim_actual,
            'channels_info': channels_info,
            'data_quality': {
                'level': mv_result.data_quality,
                'complete_ratio': mv_result.complete_ratio,
                'missing_channels': mv_result.missing_channels,
                'interpolation_count': mv_result.interpolation_count,
                'degradation_applied': is_degraded,
                'actual_channels_used': actual_channels,
            },
            'temp_compensation': temp_comp_info,
            'feature_importance': feature_importance,
            'sequence_length_used': len(data_for_model),
            'prediction_source': prediction_source,
        }

        # ============== Step 8: 审计 + 持久化 ==============
        try:
            self._record_audit_snapshot(
                node_type='bolt',
                node_id=bolt_id,
                input_data=preload_for_risk,
                processed_data=preload_for_risk,
                model_version=model_version_str,
                model_type=prediction_source,
                original_status_code=original_status_code,
                confidence=float(confidence),
                probs=probs,
                risk_assessment=risk_assessment,
                final_status_code=final_status_code,
                final_status=final_status,
                recommendations=all_recs[:10],
                extra={
                    'input_dim': input_dim_actual,
                    'channels': actual_channels,
                    'data_quality': mv_result.data_quality,
                    'degraded': is_degraded,
                },
            )
        except Exception as e:
            logger.warning(f"多变量预测审计快照异常: {e}")

        if save_to_db:
            try:
                self.repository.save_bolt_prediction(bolt_id, result)
            except Exception as e:
                logger.warning(f"多变量预测持久化失败: {e}")

        # 告警评估
        try:
            self._evaluate_alert(node_type='bolt', node_id=bolt_id, result=result)
        except Exception as e:
            logger.warning(f"多变量预测告警评估异常: {e}")

        duration = time.time() - start_time
        logger.info(
            f"多变量螺栓预测完成: {bolt_id} -> {final_status}, "
            f"channels={actual_channels}, "
            f"degraded={is_degraded}, "
            f"耗时: {duration*1000:.2f}ms"
        )
        return result

    # ---------- 多变量预测内部工具方法 ----------

    def _build_multivariate_input(
        self,
        mv_result: 'MultivariatePreprocessingResult',
        model_ready_data: np.ndarray,
    ) -> 'MultivariateInput':
        """
        将预处理结果转换为 MultivariateInput（供 MultivariatePredictor 使用）
        """
        from app.models.multivariate_model import MultivariateInput

        def _get_channel(ch: str) -> Optional[np.ndarray]:
            if ch in mv_result.channels:
                idx = mv_result.channels.index(ch)
                return model_ready_data[:, idx].astype(np.float32)
            return None

        return MultivariateInput(
            preload=_get_channel('preload') or model_ready_data[:, 0].astype(np.float32),
            temperature=_get_channel('temperature'),
            timestamps=mv_result.timestamps,
            humidity=_get_channel('humidity'),
            vibration=(
                _get_channel('vibration')
                if 'vibration' in mv_result.channels
                else _get_channel('vibration_x')
            ),
        )

    def _fallback_predict_bolt(
        self,
        bolt_id: str,
        preload_data: np.ndarray,
        version: Optional[str],
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """
        回退到单变量 BoltLSTMModel 进行预测

        Returns:
            (status_code, confidence, probs)
        """
        processed = self.preprocessor.process(
            preload_data,
            remove_anomalies=True,
            normalize=True,
            smooth=True,
        )
        model = self.get_bolt_model(bolt_id, version=version)
        if model.is_trained:
            status_code, confidence, probs = model.predict(
                processed.data, return_proba=True
            )
            return int(status_code), float(confidence), probs
        else:
            status_code, confidence, probs = self.rule_classifier.predict(
                preload_data
            )
            return int(status_code), float(confidence), probs

    def _estimate_feature_importance(
        self,
        mv_result: 'MultivariatePreprocessingResult',
        status_code: int,
    ) -> Dict[str, float]:
        """
        基于统计方法估算各通道特征重要性（当模型未输出时的兜底方案）

        方法：
        - preload 始终作为最重要通道（基础权重 = 0.5 + 异常程度 * 0.3）
        - 温度：与预紧力的相关系数绝对值 * 0.2
        - 其他通道：方差贡献率 * 剩余权重
        """
        channels = mv_result.channels
        n = len(channels)
        importance = {ch: 0.0 for ch in channels}

        if n == 0:
            return {
                'preload': 1.0, 'temperature': 0.0, 'humidity': 0.0,
                'vibration': 0.0, 'torque': 0.0, 'others': {},
            }

        # 各通道归一化方差
        variances = {}
        for c, ch in enumerate(channels):
            col = mv_result.data[:, c]
            valid = ~np.isnan(col)
            if valid.any():
                variances[ch] = float(np.nanvar(col))
            else:
                variances[ch] = 0.0

        total_var = sum(variances.values()) + 1e-9

        # preload 基础权重
        base_preload = 0.55
        severity = status_code / 4.0  # 0 ~ 1
        importance['preload'] = base_preload + 0.25 * severity

        # 温度相关度
        if 'preload' in channels and 'temperature' in channels:
            try:
                p_idx = channels.index('preload')
                t_idx = channels.index('temperature')
                p_col = mv_result.data[:, p_idx]
                t_col = mv_result.data[:, t_idx]
                valid = ~np.isnan(p_col) & ~np.isnan(t_col)
                if valid.sum() >= 5:
                    corr = abs(np.corrcoef(p_col[valid], t_col[valid])[0, 1])
                    if not np.isnan(corr):
                        importance['temperature'] = 0.2 * corr
            except Exception:
                pass

        # 剩余权重按方差分配
        assigned = sum(v for k, v in importance.items() if k in channels)
        remaining = max(0.0, 1.0 - assigned)

        for ch in channels:
            if importance.get(ch, 0.0) > 0:
                continue
            importance[ch] = remaining * (variances.get(ch, 0.0) / total_var)

        # 归一化并输出规范格式
        total = sum(importance.values()) + 1e-9
        normalized = {k: v / total for k, v in importance.items()}

        output = {
            'preload': float(normalized.get('preload', 0.0)),
            'temperature': float(normalized.get('temperature', 0.0)),
            'humidity': float(normalized.get('humidity', 0.0)),
            'vibration': float(
                normalized.get('vibration', 0.0)
                + normalized.get('vibration_x', 0.0)
                + normalized.get('vibration_y', 0.0)
                + normalized.get('vibration_z', 0.0)
            ),
            'torque': float(normalized.get('torque', 0.0)),
            'others': {
                k: float(v) for k, v in normalized.items()
                if k not in {
                    'preload', 'temperature', 'humidity',
                    'vibration', 'vibration_x', 'vibration_y', 'vibration_z', 'torque'
                }
            },
        }
        return output

    # ---------- 工况查询与管理 ----------

    def get_current_condition(
        self,
        node_id: str,
        node_type: str = 'bolt',
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定节点的当前工况

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange

        Returns:
            工况信息字典，包含 condition, confidence, change_time, is_transition 等
        """
        if not self.condition_adaptive_predictor:
            return None

        condition_key = str(node_id)
        current_condition = self.condition_adaptive_predictor.current_conditions.get(
            condition_key
        )

        if current_condition is None:
            return None

        return {
            'node_id': node_id,
            'node_type': node_type,
            'condition': current_condition,
            'condition_name': (
                current_condition.value
                if hasattr(current_condition, 'value')
                else str(current_condition)
            ),
            'confidence': self.condition_adaptive_predictor.current_condition_confidences.get(
                condition_key, 0.0
            ),
        }

    def get_condition_baseline(
        self,
        condition,
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定工况的基线信息

        Args:
            condition: 工况类型

        Returns:
            基线信息字典
        """
        if not self.condition_baseline_manager:
            return None

        baseline = self.condition_baseline_manager.get_baseline(condition)
        if baseline is None:
            return None

        return baseline.to_dict()

    def get_condition_change_history(
        self,
        node_id: str,
        node_type: str = 'bolt',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取工况变更历史记录

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            工况变更记录列表
        """
        try:
            from app.services.audit.working_condition_audit_service import (
                get_working_condition_audit_service,
            )

            audit_service = get_working_condition_audit_service()
            records = audit_service.query_condition_changes(
                node_type=node_type,
                node_id=node_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
            return [r.to_dict() if hasattr(r, 'to_dict') else r for r in records]

        except Exception as e:
            logger.warning(f"获取工况变更历史失败: {e}")
            return []

    def get_all_condition_baselines(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有工况的基线配置

        Returns:
            所有工况的基线配置字典
        """
        if not self.condition_baseline_manager:
            return {}

        baselines = {}
        for condition in WorkingCondition:
            if condition == WorkingCondition.UNKNOWN:
                continue
            baseline = self.condition_baseline_manager.get_baseline(condition)
            if baseline is not None:
                baselines[condition.value] = baseline.to_dict()

        return baselines

    # ---------- 法兰面预测 ----------

    def predict_flange(
        self,
        flange_id: str,
        multi_bolt_data: List[np.ndarray],
        save_to_db: bool = True,
        bolt_ids: Optional[List[str]] = None,
        bolt_data_dict: Optional[Dict[str, np.ndarray]] = None,
        enable_correlation_analysis: bool = True,
        version: Optional[str] = None,
        shadow_version: Optional[str] = None,
        generate_diagnosis: bool = False,
    ) -> Dict[str, Any]:
        """
        法兰面状态预测（完整流水线）

        流程: 预处理 → 模型/规则 → 风险评估 → 关联分析 → 预警策略 → 审计快照 → 持久化

        Args:
            flange_id: 法兰面ID
            multi_bolt_data: 多螺栓数据列表
            save_to_db: 是否保存到数据库
            bolt_ids: 螺栓ID列表（与multi_bolt_data对应）
            bolt_data_dict: 螺栓数据字典 {bolt_id: data}，优先于multi_bolt_data+bolt_ids
            enable_correlation_analysis: 是否启用关联分析（Granger因果、根因定位等）
            version: 使用指定版本的模型（None 表示当前活动版本）
            shadow_version: 影子版本号（Shadow Mode），仅运行预测不写库，用于A/B对比
            generate_diagnosis: 是否生成 LLM 智能诊断报告（默认 False）

        Returns:
            预测结果字典，包含 shadow_result（如果指定了 shadow_version）和 diagnosis_report（如果启用）
        """
        start_time = time.time()
        set_bolt_id(str(flange_id))

        logger.info(
            f"开始法兰面预测: {flange_id}, 螺栓数: {len(multi_bolt_data) if multi_bolt_data else (len(bolt_data_dict) if bolt_data_dict else 0)}, "
            f"version={version or 'active'}, shadow_version={shadow_version}, generate_diagnosis={generate_diagnosis}"
        )

        # 主版本预测
        main_result = self._run_flange_prediction(
            flange_id=flange_id,
            multi_bolt_data=multi_bolt_data,
            bolt_ids=bolt_ids,
            bolt_data_dict=bolt_data_dict,
            enable_correlation_analysis=enable_correlation_analysis,
            version=version,
            save_to_db=save_to_db,
            is_shadow=False,
            generate_diagnosis=generate_diagnosis,
        )

        # Shadow Mode：副版本仅预测，不写库，不触发告警
        if shadow_version and shadow_version != version:
            try:
                shadow_result = self._run_flange_prediction(
                    flange_id=flange_id,
                    multi_bolt_data=multi_bolt_data,
                    bolt_ids=bolt_ids,
                    bolt_data_dict=bolt_data_dict,
                    enable_correlation_analysis=enable_correlation_analysis,
                    version=shadow_version,
                    save_to_db=False,
                    is_shadow=True,
                    generate_diagnosis=False,
                )
                main_result['shadow_result'] = shadow_result
                main_result['shadow_version'] = shadow_version

                logger.info(
                    f"Shadow模式预测完成: 法兰面 {flange_id}, "
                    f"主版本={version or 'active'} -> {main_result['status']}, "
                    f"影子版本={shadow_version} -> {shadow_result['status']}"
                )
            except Exception as e:
                logger.warning(f"Shadow版本预测失败: {e}")
                main_result['shadow_error'] = str(e)

        duration = time.time() - start_time
        logger.info(f"法兰面预测完成: {flange_id} -> {main_result['status']}, 耗时: {duration*1000:.2f}ms")
        return main_result

    def _run_flange_prediction(
        self,
        flange_id: str,
        multi_bolt_data: List[np.ndarray],
        bolt_ids: Optional[List[str]],
        bolt_data_dict: Optional[Dict[str, np.ndarray]],
        enable_correlation_analysis: bool,
        version: Optional[str],
        save_to_db: bool,
        is_shadow: bool = False,
        generate_diagnosis: bool = False,
    ) -> Dict[str, Any]:
        """
        执行单次法兰面预测（核心预测流水线）

        Args:
            flange_id: 法兰面ID
            multi_bolt_data: 多螺栓数据列表
            bolt_ids: 螺栓ID列表
            bolt_data_dict: 螺栓数据字典
            enable_correlation_analysis: 是否启用关联分析
            version: 模型版本号
            save_to_db: 是否保存到数据库
            is_shadow: 是否为影子模式
            generate_diagnosis: 是否生成 LLM 智能诊断报告
            is_shadow: 是否为影子模式

        Returns:
            预测结果字典
        """
        if bolt_data_dict is not None:
            bolt_ids = list(bolt_data_dict.keys())
            multi_bolt_data = list(bolt_data_dict.values())
        elif bolt_ids is None:
            bolt_ids = [f"bolt_{i}" for i in range(len(multi_bolt_data))]

        model_type = 'rule'
        attention = None

        # Step 1: 预处理每个螺栓
        processed_bolts = []
        for bolt_data in multi_bolt_data:
            processed = self.preprocessor.process(
                bolt_data,
                remove_anomalies=True,
                normalize=True,
                smooth=True,
            )
            processed_bolts.append(processed.data)

        # Step 2: 加载模型
        model = self.get_flange_model(flange_id, version=version)
        model_version_str = version or 'unknown'

        # Step 1.5: 特征工程（可选，配置开关控制）
        fe_cfg = config.get('feature_engineering', {})
        fe_enabled = fe_cfg.get('enabled', True)
        bolt_features_list = None
        global_feature_vec = None
        if fe_enabled and model.is_trained:
            try:
                # 每螺栓特征
                bolt_feats: List[np.ndarray] = []
                bolt_scaler_state = getattr(model, '_bolt_feature_scaler_state', None)
                if bolt_scaler_state is not None:
                    self.feature_engineer.set_scaler_state(bolt_scaler_state)
                for pdata in processed_bolts:
                    raw_feat = self.feature_engineer.extract_features(pdata)
                    if raw_feat.size > 0:
                        bolt_feats.append(
                            self.feature_engineer.transform_features(raw_feat)
                        )
                    else:
                        bolt_feats.append(np.array([], dtype=np.float32))
                bolt_features_list = bolt_feats if all(bf.size > 0 for bf in bolt_feats) else None

                # 全局特征：所有螺栓拼接后整体提取
                global_scaler_state = getattr(model, '_global_feature_scaler_state', None)
                if global_scaler_state is not None:
                    self.feature_engineer.set_scaler_state(global_scaler_state)
                concatenated = np.concatenate(processed_bolts)
                raw_global = self.feature_engineer.extract_features(concatenated)
                if raw_global.size > 0:
                    global_feature_vec = self.feature_engineer.transform_features(raw_global)
            except Exception as e:
                logger.warning(f"法兰面 {flange_id} 特征提取失败，跳过特征辅助: {e}")
                bolt_features_list = None
                global_feature_vec = None

        # Step 2: 模型推断（模型未训练则规则聚合兜底）
        if model.is_trained:
            if version is None:
                model_version_str = self._get_model_version('flange', flange_id)
            original_status_code, confidence, attention = model.predict(
                processed_bolts,
                return_attention=True,
                bolt_features=bolt_features_list,
                global_features=global_feature_vec,
            )
            model_type = 'attention'
        else:
            original_status_code, confidence = self.rule_classifier.aggregate_predictions(
                multi_bolt_data
            )
            attention = None

        original_status = STATUS_LABELS.get(original_status_code, '未知')

        # Step 2.5: 工况识别与自适应调整
        flange_condition_info = {}
        flange_condition_prediction = None
        if self.enable_working_condition and len(all_data) >= 50:
            try:
                flange_condition_prediction = self.condition_adaptive_predictor.predict(
                    node_id=str(flange_id),
                    data=all_data,
                    forecast_days=1,
                    node_type='flange',
                )

                flange_condition = flange_condition_prediction.condition
                flange_condition_info = {
                    'condition': flange_condition.value,
                    'condition_label': flange_condition_prediction.condition_label,
                    'confidence': flange_condition_prediction.condition_confidence,
                    'is_transition': flange_condition_prediction.is_transition,
                    'condition_changed': flange_condition_prediction.condition_changed,
                    'baseline_anomaly': {
                        'status': flange_condition_prediction.overall_status,
                        'anomaly_count': flange_condition_prediction.anomaly_summary.get('anomaly_count', 0),
                        'warning_count': flange_condition_prediction.anomaly_summary.get('warning_count', 0),
                    },
                }

                if flange_condition_prediction.condition_confidence >= self.condition_confidence_threshold:
                    anomaly_ratio = flange_condition_prediction.anomaly_summary.get('anomaly_ratio', 0.0)
                    if anomaly_ratio >= 0.3:
                        original_status_code = max(original_status_code, 3)
                        original_status = STATUS_LABELS.get(original_status_code, '未知')
                    elif anomaly_ratio >= 0.1:
                        original_status_code = max(original_status_code, 2)
                        original_status = STATUS_LABELS.get(original_status_code, '未知')

                    adjusted = self._adjust_confidence_by_condition(
                        confidence, flange_condition, original_status_code
                    )
                    if abs(adjusted - confidence) > 0.001:
                        confidence = adjusted

                self.condition_baseline_manager.update_baseline(
                    flange_condition, all_data, incremental=True
                )

                if flange_condition_prediction.condition_changed:
                    self._record_condition_change_audit(
                        bolt_id=str(flange_id),
                        condition_result=flange_condition_prediction,
                        node_type='flange',
                    )

            except Exception as e:
                logger.warning(f"法兰面工况识别失败，跳过: {e}")

        flange_condition = flange_condition_prediction.condition if flange_condition_prediction else None

        # Step 3: 风险评估（使用所有螺栓数据拼接）
        all_data = np.concatenate(multi_bolt_data)
        risk_assessment = self._assess_risk_with_condition(
            all_data,
            lstm_class=original_status_code,
            node_type='flange',
            node_id=flange_id,
            condition=flange_condition,
            lstm_probs=None,
        )

        # Step 4: 应用预警策略
        final_status_code, final_status = self._apply_warning_with_condition(
            original_status_code=original_status_code,
            original_status=original_status,
            confidence=confidence,
            risk_assessment=risk_assessment,
            condition=flange_condition,
            bolt_id=flange_id,
        )

        # 推荐措施
        recommendations = model.get_recommendation(final_status_code, confidence)

        # Step 4.3: 关联分析（Granger因果、领先螺栓、根因定位）
        correlation_analysis = None
        root_cause_measures = ''
        if enable_correlation_analysis and len(multi_bolt_data) >= 2:
            try:
                bolt_data_dict_analysis = {
                    bid: data for bid, data in zip(bolt_ids, multi_bolt_data)
                }

                bolt_statuses = {}
                for i, bid in enumerate(bolt_ids):
                    bolt_status = self._estimate_single_bolt_status(multi_bolt_data[i])
                    bolt_statuses[bid] = bolt_status

                correlation_analysis = model.comprehensive_correlation_analysis(
                    bolt_data=bolt_data_dict_analysis,
                    bolt_ids=bolt_ids,
                    bolt_statuses=bolt_statuses,
                    bolt_health_indices=None,
                    max_lag=5,
                    significance_level=0.05,
                    min_correlation=0.3
                )

                root_cause_measures = correlation_analysis.get('root_cause_measures', '')

                if root_cause_measures:
                    risk_assessment.recommendations.append(root_cause_measures)

                logger.info(
                    f"关联分析完成: 法兰面 {flange_id}, "
                    f"因果边数={len(correlation_analysis['causal_graph']['edges']) if correlation_analysis.get('causal_graph') else 0}, "
                    f"根因螺栓={correlation_analysis['root_cause_analysis']['root_cause_bolt']['bolt_id'] if correlation_analysis.get('root_cause_analysis', {}).get('root_cause_bolt') else 'N/A'}"
                )
            except Exception as e:
                logger.warning(f"关联分析失败，跳过: {e}")
                correlation_analysis = None

        # Step 4.5: CBR 知识库检索（相似案例与推荐措施增强）
        similar_cases = []
        rag_context = ''
        cbr_enabled = config.get('cbr.enabled', True)
        cbr_in_prediction = config.get('cbr.integration.in_prediction', True)

        if cbr_enabled and cbr_in_prediction and final_status_code > 0:
            try:
                from app.services.knowledge import KnowledgeService

                cbr_service = KnowledgeService()

                # 使用所有螺栓拼接的数据提取特征
                try:
                    feature_set = self.feature_engineer.extract_features(all_data)
                    feature_vector = feature_set.combined_features.tolist()
                except Exception:
                    feature_vector = None

                fault_type_mapping = {
                    1: 'loosening',
                    2: 'preload_decrease',
                    3: 'severe_anomaly',
                    4: 'failure',
                }
                fault_type = fault_type_mapping.get(final_status_code)

                cbr_result = cbr_service.get_case_recommendations(
                    node_type='flange',
                    node_id=flange_id,
                    fault_type=fault_type,
                    fault_level=final_status_code if final_status_code > 0 else None,
                    feature_vector=feature_vector,
                    top_k=config.get('cbr.integration.top_k', 3),
                    min_similarity=config.get('cbr.integration.min_similarity', 0.4),
                    only_approved=True,
                )

                similar_cases = cbr_result.get('cases', [])
                rag_context = cbr_result.get('rag_context', '')

                # 合并推荐措施
                cbr_recommendations = cbr_result.get('aggregated_recommendations', [])
                if cbr_recommendations:
                    combined_recs = []
                    seen = set()
                    for rec in cbr_recommendations:
                        if rec and rec not in seen:
                            seen.add(rec)
                            combined_recs.append(rec)
                    for rec in risk_assessment.recommendations:
                        if rec and rec not in seen:
                            seen.add(rec)
                            combined_recs.append(rec)
                    risk_assessment.recommendations = combined_recs[:10]
                    logger.info(
                        f"CBR推荐已合并: 法兰面 {flange_id}, "
                        f"找到 {len(similar_cases)} 个相似案例, "
                        f"推荐措施 {len(combined_recs)} 条"
                    )
            except Exception as e:
                logger.warning(f"CBR知识库检索失败，跳过: {e}")

        fault_detail = None
        if final_status_code >= 3 and not is_shadow:
            try:
                fault_result = self.fault_classifier.classify(all_data)
                fault_detail = self._build_fault_detail(fault_result)
                if fault_result.fault_type != FaultType.NORMAL and fault_result.fault_type != FaultType.UNKNOWN:
                    fault_recs = fault_result.recommendations
                    existing_recs = set(risk_assessment.recommendations)
                    for rec in fault_recs:
                        if rec and rec not in existing_recs:
                            risk_assessment.recommendations.append(rec)
                    logger.info(
                        f"故障分类完成: 法兰面 {flange_id}, "
                        f"fault_type={fault_result.fault_type.value}, "
                        f"confidence={fault_result.confidence:.3f}"
                    )
            except Exception as e:
                logger.warning(f"故障分类失败，跳过: {e}")

        result = {
            'flange_id': flange_id,
            'status': final_status,
            'status_code': final_status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'bolt_count': len(multi_bolt_data),
            'bolt_ids': bolt_ids,
            'attention_weights': attention.tolist() if attention is not None else None,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations,
            'model_version': model_version_str,
            'model_type': model_type,
            'is_shadow': is_shadow,
            'similar_cases': [
                {
                    'id': c.id,
                    'case_no': c.case_no,
                    'case_title': c.case_title,
                    'fault_type': c.fault_type,
                    'effectiveness_score': c.effectiveness_score,
                    'similarity_score': getattr(c, 'similarity_score', None),
                }
                for c in similar_cases
            ] if similar_cases else [],
            'rag_context': rag_context,
            'correlation_matrix': (
                correlation_analysis.get('correlation_matrix')
                if correlation_analysis else None
            ),
            'causal_graph': (
                correlation_analysis.get('causal_graph')
                if correlation_analysis else None
            ),
            'leading_bolts': (
                correlation_analysis.get('leading_bolts')
                if correlation_analysis else None
            ),
            'propagation_paths': (
                correlation_analysis.get('propagation_paths')
                if correlation_analysis else None
            ),
            'root_cause_analysis': (
                correlation_analysis.get('root_cause_analysis')
                if correlation_analysis else None
            ),
            'root_cause_measures': root_cause_measures if root_cause_measures else None,
            'fault_detail': fault_detail,
            'working_condition': flange_condition_info if flange_condition_info else None,
        }

        # Step 5: 审计快照
        try:
            self._record_audit_snapshot(
                node_type='flange',
                node_id=flange_id,
                input_data=all_data,
                processed_data=None,
                model_version=model_version_str,
                model_type=model_type,
                original_status_code=original_status_code,
                confidence=float(confidence),
                probs=None,
                risk_assessment=risk_assessment,
                final_status_code=final_status_code,
                final_status=final_status,
                recommendations=risk_assessment.recommendations,
                attention_weights=attention,
                multi_bolt_data=multi_bolt_data,
                working_condition=flange_condition_info if flange_condition_info else None,
            )
        except Exception as e:
            logger.warning(f"法兰面 {flange_id} 审计快照记录异常: {e}")

        # Step 6: 持久化（Shadow 模式不写库）
        if save_to_db and not is_shadow:
            self.repository.save_flange_prediction(flange_id, result)

        # Step 7: 告警评估（Shadow 模式不触发告警）
        if not is_shadow:
            try:
                self._evaluate_alert(
                    node_type='flange',
                    node_id=flange_id,
                    result=result,
                )
            except Exception as e:
                logger.warning(f"法兰面 {flange_id} 告警评估异常: {e}")

        # 记录预测指标
        metrics.record_prediction(
            node_type='flange',
            status_code=final_status_code,
            status_label=final_status,
            duration=0,
            model_type=model_type
        )

        # Step 8: LLM 智能诊断报告（可选）
        if generate_diagnosis and not is_shadow:
            try:
                from app.services.report import get_diagnosis_report_service
                diagnosis_service = get_diagnosis_report_service()

                fault_type_mapping = {
                    1: 'loosening',
                    2: 'preload_decrease',
                    3: 'severe_anomaly',
                    4: 'failure',
                }
                fault_type = fault_type_mapping.get(final_status_code)

                recent_values = None
                if multi_bolt_data is not None and len(multi_bolt_data) > 0:
                    all_values = []
                    for bolt_data in multi_bolt_data:
                        if bolt_data is not None and len(bolt_data) > 0:
                            all_values.extend([float(v) for v in bolt_data[-10:]])
                    recent_values = all_values[:30]

                diagnosis_report = diagnosis_service.generate_single_report(
                    status=final_status,
                    risk_score=float(risk_assessment.score),
                    node_type='flange',
                    node_id=str(flange_id),
                    fault_type=fault_type,
                    trend=None,
                    recent_values=recent_values,
                    historical_incidents=None,
                )

                result['diagnosis_report'] = {
                    'diagnosis_summary': diagnosis_report.diagnosis_summary,
                    'recommended_actions': diagnosis_report.recommended_actions,
                    'urgency_level': diagnosis_report.urgency_level.value if hasattr(diagnosis_report.urgency_level, 'value') else diagnosis_report.urgency_level,
                    'model': diagnosis_report.model,
                    'tokens_used': diagnosis_report.tokens_used,
                    'latency_ms': diagnosis_report.latency_ms,
                    'is_fallback': diagnosis_report.is_fallback,
                }

                logger.info(
                    f"LLM诊断报告生成完成: 法兰面 {flange_id}, "
                    f"紧急程度={result['diagnosis_report']['urgency_level']}, "
                    f"模型={diagnosis_report.model}, "
                    f"耗时={diagnosis_report.latency_ms:.2f}ms"
                )
            except Exception as e:
                logger.warning(f"LLM诊断报告生成失败，跳过: {e}")
                result['diagnosis_report'] = None

        return result

    def _estimate_single_bolt_status(self, data: np.ndarray) -> int:
        """
        估算单个螺栓的状态等级

        用于根因分析时为每个螺栓提供状态参考。

        Args:
            data: 螺栓预紧力数据

        Returns:
            int: 状态代码 0-4
        """
        try:
            if len(data) < 10:
                return 0

            mean_val = np.mean(data)
            std_val = np.std(data)
            cv = std_val / (mean_val + 1e-6)

            nominal = config.get('preload.nominal', 600)
            deviation = abs(mean_val - nominal) / nominal

            status_code = 0
            if deviation > 0.30 or cv > 0.15:
                status_code = 3
            elif deviation > 0.20 or cv > 0.10:
                status_code = 2
            elif deviation > 0.10 or cv > 0.05:
                status_code = 1
            else:
                status_code = 0

            return status_code
        except Exception:
            return 0

    def _build_fault_detail(self, fault_result: FaultClassificationResult) -> Dict[str, Any]:
        """
        构建故障详情对象，用于API响应

        Args:
            fault_result: FaultClassifier 分类结果

        Returns:
            Dict: 包含 fault_type、fault_confidence、evidence 和 pattern 数据
        """
        pattern = fault_result.pattern
        return {
            'fault_type': fault_result.fault_type.value,
            'fault_confidence': float(fault_result.confidence),
            'fault_name': fault_result.fault_name,
            'severity': fault_result.severity,
            'evidence': fault_result.evidence,
            'recommendations': fault_result.recommendations,
            'pattern': {
                'trend_slope': pattern.trend_slope,
                'volatility': pattern.volatility,
                'sudden_changes': pattern.sudden_changes,
                'min_value': pattern.min_value,
                'max_value': pattern.max_value,
                'mean_value': pattern.mean_value,
            },
        }

    # ---------- 风险评估（独立接口） ----------

    def assess_risk(
        self,
        node_id: str,
        node_type: str,
        data: np.ndarray,
        generate_diagnosis: bool = False,
    ) -> Dict[str, Any]:
        """
        单独的风险评估接口（不经过模型和策略）

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            data: 预紧力数据
            generate_diagnosis: 是否生成 LLM 智能诊断报告（默认 False）
        """
        assessment = self.risk_model.assess_risk(
            data,
            node_type=node_type,
            node_id=node_id,
        )
        result = {
            'node_id': node_id,
            'node_type': node_type,
            'risk_score': float(assessment.score),
            'risk_level': assessment.level.value,
            'factors': assessment.factors,
            'diagnosis': assessment.diagnosis,
            'recommendations': assessment.recommendations,
            'confidence': float(assessment.confidence),
        }

        if assessment.probability_distribution is not None:
            result['probability_distribution'] = assessment.probability_distribution.to_dict()

        if assessment.factor_contributions is not None:
            result['factor_contributions'] = [
                {
                    'name': fc.name,
                    'display_name': fc.display_name,
                    'raw_score': fc.raw_score,
                    'weight': fc.weight,
                    'weighted_score': fc.weighted_score,
                    'contribution_ratio': fc.contribution_ratio,
                    'direction': fc.direction,
                }
                for fc in assessment.factor_contributions
            ]

        if generate_diagnosis:
            try:
                from app.services.report import get_diagnosis_report_service
                diagnosis_service = get_diagnosis_report_service()

                recent_values = None
                if data is not None and len(data) > 0:
                    recent_values = [float(v) for v in data[-20:]]

                diagnosis_report = diagnosis_service.generate_single_report(
                    status=assessment.level.value,
                    risk_score=float(assessment.score),
                    node_type=node_type,
                    node_id=str(node_id),
                    fault_type=None,
                    trend=None,
                    recent_values=recent_values,
                    historical_incidents=None,
                )

                result['diagnosis_report'] = {
                    'diagnosis_summary': diagnosis_report.diagnosis_summary,
                    'recommended_actions': diagnosis_report.recommended_actions,
                    'urgency_level': diagnosis_report.urgency_level.value if hasattr(diagnosis_report.urgency_level, 'value') else diagnosis_report.urgency_level,
                    'model': diagnosis_report.model,
                    'tokens_used': diagnosis_report.tokens_used,
                    'latency_ms': diagnosis_report.latency_ms,
                    'is_fallback': diagnosis_report.is_fallback,
                }

                logger.info(
                    f"LLM诊断报告生成完成: {node_type} {node_id}, "
                    f"紧急程度={result['diagnosis_report']['urgency_level']}, "
                    f"模型={diagnosis_report.model}, "
                    f"耗时={diagnosis_report.latency_ms:.2f}ms"
                )
            except Exception as e:
                logger.warning(f"LLM诊断报告生成失败，跳过: {e}")
                result['diagnosis_report'] = None

        return result

    def explain_risk(
        self,
        node_id: str,
        node_type: str,
        data: np.ndarray,
    ) -> Dict[str, Any]:
        """
        风险评估可解释性分析接口

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            data: 预紧力数据

        Returns:
            Dict: 可解释性分析结果
        """
        explanation = self.risk_model.explain_risk(
            data,
            node_type=node_type,
            node_id=node_id,
        )
        return explanation.to_dict()

    # ---------- 月度趋势预测 ----------

    def forecast_monthly(
        self,
        node_id: str,
        node_type: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        月度 Prophet 趋势预测

        流程: 读取 30 天历史 → Prophet 预测 → 持久化
        """
        logger.info(f"开始月度预测: {node_id}, 类型: {node_type}, 天数: {days}")

        # Step 1: 读取历史数据
        if node_type == 'bolt':
            historical = self.repository.get_bolt_history(node_id)
        else:
            historical = self.repository.get_flange_history(node_id)

        if historical is None or len(historical['data']) < 10:
            logger.warning(f"历史数据不足: {node_id}")
            return {
                'pw_type': '正常',
                'fault_type': None,
                'begin_time': None,
                'end_time': None,
                'confidence': 0.5,
                'rec_measures': '历史数据不足，无法进行可靠预测。',
                'forecast_dates': [],
                'forecast_values': [],
            }

        # Step 2: Prophet 预测
        result = self.prophet.predict_status(
            historical_data=historical['data'],
            historical_timestamps=historical['timestamps'],
            days=days,
        )

        # Step 3: 持久化
        self.repository.save_monthly_prediction(node_id, node_type, result)

        return result

    # ---------- 批量预测（调度器用） ----------

    def batch_predict_from_db(self, node_type: str, specific_bolt_id: Optional[str] = None) -> None:
        """
        从数据库批量拉取数据并预测（调度任务入口）

        Args:
            node_type: 'bolt' 或 'flange'
            specific_bolt_id: 可选，指定要预测的单个螺栓ID（用于分片执行）
        """
        task_type = f"batch_{node_type}"
        logger.info(f"开始批量预测: {node_type}" + (f" (指定螺栓: {specific_bolt_id})" if specific_bolt_id else ""))
        try:
            if node_type == 'bolt':
                if specific_bolt_id:
                    self._predict_single_bolt(specific_bolt_id)
                else:
                    self._batch_predict_bolts()
            elif node_type == 'flange':
                self._batch_predict_flanges()
            else:
                logger.error(f"未知节点类型: {node_type}")
                metrics.record_prediction_task(task_type, success=False, error_type="unknown_node_type")
                return

            # 记录任务成功
            if not specific_bolt_id:
                metrics.record_prediction_task(task_type, success=True)
        except Exception as e:
            logger.error(f"批量预测失败: {e}")
            if not specific_bolt_id:
                metrics.record_prediction_task(task_type, success=False, error_type=str(type(e).__name__))
            raise

    def _predict_single_bolt(self, bolt_id: str) -> None:
        """预测单个螺栓（用于分片执行）"""
        bolt_data = self.repository.fetch_batch_bolt_data(per_bolt_limit=100, bolt_ids=[bolt_id])

        if bolt_id not in bolt_data:
            raise RuntimeError(f"未找到螺栓 {bolt_id} 的数据")

        data_dict = bolt_data[bolt_id]
        self.predict_bolt(
            bolt_id=bolt_id,
            data=np.array(data_dict['data']),
            timestamps=data_dict['timestamps'],
            save_to_db=True,
        )

    def _batch_predict_bolts(self) -> None:
        """批量预测所有螺栓"""
        bolt_data = self.repository.fetch_batch_bolt_data(per_bolt_limit=100)

        success_count = 0
        fail_count = 0

        for bolt_id, data_dict in bolt_data.items():
            try:
                self.predict_bolt(
                    bolt_id=bolt_id,
                    data=np.array(data_dict['data']),
                    timestamps=data_dict['timestamps'],
                    save_to_db=True,
                )
                success_count += 1
            except Exception as e:
                logger.error(f"螺栓 {bolt_id} 预测失败: {e}")
                fail_count += 1

        # 更新模型加载数
        metrics.update_model_count('bolt_lstm', len(self.bolt_models))

        logger.info(f"批量螺栓预测完成，共 {len(bolt_data)} 个，成功 {success_count} 个，失败 {fail_count} 个")

    def _batch_predict_flanges(self) -> None:
        """批量预测所有法兰面"""
        flange_ids = self.repository.fetch_all_flange_ids()

        success_count = 0
        fail_count = 0

        for flange_id in flange_ids:
            try:
                bolt_series = self.repository.fetch_flange_bolt_data(flange_id)
                if not bolt_series:
                    continue

                bolt_data_dict = {
                    str(bid): np.array(data)
                    for bid, data in bolt_series.items()
                }

                self.predict_flange(
                    flange_id=flange_id,
                    multi_bolt_data=[],
                    bolt_data_dict=bolt_data_dict,
                    save_to_db=True,
                    enable_correlation_analysis=True,
                )
                success_count += 1
            except Exception as e:
                logger.error(f"法兰面 {flange_id} 预测失败: {e}")
                fail_count += 1

        # 更新模型加载数
        metrics.update_model_count('flange_attention', len(self.flange_models))

        logger.info(f"批量法兰面预测完成，共 {len(flange_ids)} 个，成功 {success_count} 个，失败 {fail_count} 个")

    # ---------- 审计快照 ----------

    @staticmethod
    def _get_model_version(model_type: str, node_id: str) -> str:
        """
        获取当前活动模型版本号
        """
        try:
            version = version_manager.get_version(
                f"{model_type}_{node_id}"
            )
            if version:
                return version.version
        except Exception:
            pass
        return 'unversioned'

    def _record_audit_snapshot(
        self,
        node_type: str,
        node_id: str,
        input_data: np.ndarray,
        processed_data: Optional[np.ndarray],
        model_version: str,
        model_type: str,
        original_status_code: int,
        confidence: float,
        probs: Optional[np.ndarray],
        risk_assessment: RiskAssessment,
        final_status_code: int,
        final_status: str,
        recommendations: List[str],
        attention_weights: Optional[np.ndarray] = None,
        multi_bolt_data: Optional[List[np.ndarray]] = None,
        working_condition: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录预测审计快照

        收集完整的预测上下文，包括输入哈希、模型版本、
        特征摘要、中间结果、最终决策、策略版本、可解释性报告。
        """
        from app.services.audit import AuditService, ExplainabilityService

        audit_service = AuditService()
        explain_service = ExplainabilityService()

        strategy_result = (final_status_code, final_status)
        if node_type == 'bolt':
            explain_report = explain_service.generate_bolt_explainability(
                data=input_data,
                processed_data=processed_data,
                model_output=None,
                risk_assessment=risk_assessment,
                status_code=original_status_code,
                confidence=confidence,
                probs=probs,
                strategy_result=strategy_result,
            )
        else:
            explain_report = explain_service.generate_flange_explainability(
                multi_bolt_data=multi_bolt_data or [input_data],
                attention_weights=attention_weights,
                model_output=None,
                risk_assessment=risk_assessment,
                status_code=original_status_code,
                confidence=confidence,
                strategy_result=strategy_result,
            )

        intermediate_results = {
            'preprocessing': {
                'original_count': int(len(input_data)),
                'processed_count': (
                    int(len(processed_data)) if processed_data is not None else None
                ),
            },
            'model_raw_output': {
                'original_status_code': original_status_code,
                'original_status': STATUS_LABELS.get(original_status_code, '未知'),
                'model_type': model_type,
            },
            'risk_assessment': {
                'score': float(risk_assessment.score),
                'level': risk_assessment.level.value,
                'factors': risk_assessment.factors,
                'confidence': float(risk_assessment.confidence),
            },
            'working_condition': working_condition or {},
        }

        if extra:
            intermediate_results['extra'] = extra

        final_decision = {
            'status_code': final_status_code,
            'status': final_status,
            'confidence': confidence,
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': recommendations,
        }

        strategy_version = f"v{self.warning_policy.strategy_type}"
        if self.warning_policy.strategy_type == 1:
            strategy_version += f"_threshold_{self.warning_policy.strategy_1_threshold}"
        else:
            strategy_version += f"_threshold_{self.warning_policy.strategy_2_threshold}"

        audit_service.record_prediction(
            node_type=node_type,
            node_id=node_id,
            input_data=input_data,
            model_version=model_version,
            model_type=model_type,
            intermediate_results=intermediate_results,
            final_decision=final_decision,
            strategy_version=strategy_version,
            strategy_type=self.warning_policy.strategy_type,
            explainability=explain_report,
        )

    def _adjust_confidence_by_condition(
        self,
        original_confidence: float,
        condition: WorkingCondition,
        status_code: int,
    ) -> float:
        """
        根据工况调整预测置信度

        不同工况下，预测的可靠性不同：
        - 稳态运行：置信度提升（数据稳定，预测更可靠）
        - 升/降负荷：置信度微调（趋势变化时预测有一定不确定性）
        - 停机冷却：异常检测置信度提升（状态明显）
        - 检修后恢复：置信度降低（数据不稳定）

        Args:
            original_confidence: 原始置信度
            condition: 当前工况
            status_code: 状态码（0=正常, >0=异常）

        Returns:
            调整后的置信度
        """
        adjustment_factors = {
            WorkingCondition.STEADY_STATE: {
                'normal': 1.05,
                'anomaly': 1.0,
            },
            WorkingCondition.LOAD_INCREASE: {
                'normal': 0.95,
                'anomaly': 0.9,
            },
            WorkingCondition.LOAD_DECREASE: {
                'normal': 0.95,
                'anomaly': 0.9,
            },
            WorkingCondition.SHUTDOWN_COOLING: {
                'normal': 1.0,
                'anomaly': 1.1,
            },
            WorkingCondition.POST_MAINTENANCE_RECOVERY: {
                'normal': 0.85,
                'anomaly': 0.8,
            },
            WorkingCondition.UNKNOWN: {
                'normal': 0.95,
                'anomaly': 0.9,
            },
        }

        condition_factors = adjustment_factors.get(
            condition,
            adjustment_factors[WorkingCondition.UNKNOWN],
        )

        status_type = 'anomaly' if status_code > 0 else 'normal'
        factor = condition_factors.get(status_type, 1.0)

        adjusted = original_confidence * factor
        adjusted = max(0.0, min(1.0, adjusted))

        return float(adjusted)

    def _record_condition_change_audit(
        self,
        bolt_id: str,
        condition_result,
        node_type: str = 'bolt',
    ) -> Optional[str]:
        """
        记录工况变更审计

        Args:
            bolt_id: 螺栓ID
            condition_result: 工况自适应预测结果（ConditionAdaptivePrediction）
            node_type: 节点类型

        Returns:
            事件ID（失败返回None）
        """
        try:
            from app.services.audit.working_condition_audit_service import (
                get_working_condition_audit_service,
            )

            audit_service = get_working_condition_audit_service()

            previous_condition = condition_result.previous_condition
            to_condition = condition_result.condition
            to_confidence = condition_result.condition_confidence
            from_confidence = 0.0

            baseline_info = self.condition_baseline_manager.get_baseline(to_condition)
            baseline_dict = baseline_info.to_dict() if baseline_info else None

            condition_probs = {}
            if condition_result.condition_probabilities:
                condition_probs = {
                    k.value if hasattr(k, 'value') else str(k): v
                    for k, v in condition_result.condition_probabilities.items()
                }

            event_id = audit_service.record_condition_change(
                node_type=node_type,
                node_id=bolt_id,
                from_condition=previous_condition,
                to_condition=to_condition,
                from_confidence=from_confidence,
                to_confidence=to_confidence,
                is_transition=condition_result.is_transition,
                trigger_data_points=0,
                feature_evidence=condition_probs,
                condition_probabilities=condition_probs,
                baseline_info=baseline_dict,
                anomaly_summary=condition_result.anomaly_summary if condition_result.anomaly_summary else None,
            )

            return event_id

        except Exception as e:
            logger.warning(f"记录工况变更审计失败: {e}")
            return None

    def _assess_risk_with_condition(
        self,
        data: np.ndarray,
        lstm_probs: Optional[np.ndarray],
        lstm_class: int,
        node_type: str,
        node_id: str,
        condition: Optional[WorkingCondition] = None,
    ) -> RiskAssessment:
        """
        带工况感知的风险评估

        根据工况动态调整风险评估权重：
        - 稳态运行：标准权重
        - 升/降负荷：降低趋势因子权重（趋势变化是预期的），提高LSTM因子权重
        - 停机冷却：提高均值偏移因子权重，降低趋势因子权重
        - 检修后恢复：降低LSTM因子权重（模型对恢复期预测不准），提高波动性因子权重
        """
        risk_assessment = self.risk_model.assess_risk(
            data,
            lstm_probs=lstm_probs,
            lstm_class=lstm_class,
            node_type=node_type,
            node_id=node_id,
        )

        if condition is None or condition == WorkingCondition.UNKNOWN:
            return risk_assessment

        condition_weight_overrides = {
            WorkingCondition.STEADY_STATE: None,
            WorkingCondition.LOAD_INCREASE: {
                'mean_deviation': 0.20,
                'volatility': 0.15,
                'trend': 0.10,
                'extreme_values': 0.20,
                'lstm_prediction': 0.35,
            },
            WorkingCondition.LOAD_DECREASE: {
                'mean_deviation': 0.20,
                'volatility': 0.15,
                'trend': 0.10,
                'extreme_values': 0.20,
                'lstm_prediction': 0.35,
            },
            WorkingCondition.SHUTDOWN_COOLING: {
                'mean_deviation': 0.35,
                'volatility': 0.25,
                'trend': 0.05,
                'extreme_values': 0.20,
                'lstm_prediction': 0.15,
            },
            WorkingCondition.POST_MAINTENANCE_RECOVERY: {
                'mean_deviation': 0.20,
                'volatility': 0.30,
                'trend': 0.15,
                'extreme_values': 0.25,
                'lstm_prediction': 0.10,
            },
        }

        weight_override = condition_weight_overrides.get(condition)
        if weight_override is not None:
            effective_weights = self.risk_model.get_effective_weights(node_type, node_id)
            original_score = risk_assessment.score

            scores = {
                'mean_deviation': self.risk_model.calculate_deviation_score(data),
                'volatility': self.risk_model.calculate_volatility_score(data),
                'trend': self.risk_model.calculate_trend_score(data),
                'extreme_values': self.risk_model.calculate_extreme_score(data),
                'lstm_prediction': self.risk_model.calculate_lstm_score(lstm_probs),
            }

            weighted_score = sum(
                weight_override.get(k, 0) * v for k, v in scores.items()
            )
            condition_risk_score = round(weighted_score * 9 + 1, 1)
            condition_risk_score = float(np.clip(condition_risk_score, 1, 10))

            blend_factor = 0.4
            blended_score = original_score * (1 - blend_factor) + condition_risk_score * blend_factor
            blended_score = round(float(blended_score), 1)

            if abs(blended_score - original_score) > 0.5:
                from app.models.risk_model import RiskLevel
                if blended_score <= 3:
                    new_level = RiskLevel.HIGH
                elif blended_score <= 7:
                    new_level = RiskLevel.MEDIUM
                else:
                    new_level = RiskLevel.LOW

                logger.info(
                    f"工况风险调整: {node_type} {node_id}, "
                    f"工况={condition.value}, "
                    f"风险分 {original_score} → {blended_score}, "
                    f"等级 {risk_assessment.level.value} → {new_level.value}"
                )

                risk_assessment.score = blended_score
                risk_assessment.level = new_level

                if hasattr(risk_assessment, 'factors') and risk_assessment.factors:
                    risk_assessment.factors['condition_adjustment'] = {
                        'condition': condition.value,
                        'original_score': original_score,
                        'adjusted_score': blended_score,
                        'weight_override': weight_override,
                    }

        return risk_assessment

    def _apply_warning_with_condition(
        self,
        original_status_code: int,
        original_status: str,
        confidence: float,
        risk_assessment: RiskAssessment,
        condition: Optional[WorkingCondition] = None,
        bolt_id: str = '',
    ) -> Tuple[int, str]:
        """
        带工况感知的预警策略应用

        根据工况调整预警灵敏度：
        - 稳态运行：标准策略
        - 升/降负荷：提高报警门槛（变化是预期的，减少误报）
        - 停机冷却：提高灵敏度（异常可能意味着冷却异常）
        - 检修后恢复：提高报警门槛（恢复期波动是正常的）
        """
        final_code, final_status = self.warning_policy.apply(
            original_status_code,
            original_status,
            confidence,
            risk_level=risk_assessment.level.value,
            lstm_confidence=float(confidence),
        )

        if condition is None or condition == WorkingCondition.UNKNOWN:
            return final_code, final_status

        condition_sensitivity = {
            WorkingCondition.STEADY_STATE: 0.0,
            WorkingCondition.LOAD_INCREASE: -0.1,
            WorkingCondition.LOAD_DECREASE: -0.1,
            WorkingCondition.SHUTDOWN_COOLING: 0.15,
            WorkingCondition.POST_MAINTENANCE_RECOVERY: -0.15,
        }

        sensitivity_delta = condition_sensitivity.get(condition, 0.0)

        if sensitivity_delta > 0 and final_code < original_status_code:
            restored_code = original_status_code
            restored_status = STATUS_LABELS.get(restored_code, '未知')
            logger.info(
                f"工况预警升级: 螺栓 {bolt_id}, "
                f"工况={condition.value}, "
                f"策略降级 {final_code} → 恢复为 {restored_code}（高灵敏度工况）"
            )
            return restored_code, restored_status

        if sensitivity_delta < 0 and final_code > 0 and final_code == original_status_code:
            effective_confidence = confidence + abs(sensitivity_delta)
            if effective_confidence < self.warning_policy.strategy_1_threshold:
                demoted_code = max(0, final_code - 1)
                demoted_status = STATUS_LABELS.get(demoted_code, '正常')
                logger.info(
                    f"工况预警降级: 螺栓 {bolt_id}, "
                    f"工况={condition.value}, "
                    f"状态码 {final_code} → {demoted_code}（低灵敏度工况）"
                )
                return demoted_code, demoted_status

        return final_code, final_status

    # ---------- 告警评估 ----------

    def _evaluate_alert(
        self,
        node_type: str,
        node_id: str,
        result: Dict[str, Any],
    ) -> None:
        """
        评估预测结果并触发告警（如有）

        Args:
            node_type: 节点类型 bolt/flange
            node_id: 节点ID
            result: 预测结果字典
        """
        try:
            from app.services.alert import AlertService
        except ImportError:
            logger.debug("告警服务未启用，跳过告警评估")
            return

        status_code = result.get('status_code', 0)
        if status_code <= 0:
            return

        try:
            alert_service = AlertService()
            alert = alert_service.evaluate_prediction(
                node_type=node_type,
                node_id=node_id,
                status_code=status_code,
                confidence=float(result.get('confidence', 0)),
                risk_score=float(result.get('risk_score', 0)),
                diagnosis=str(result.get('diagnosis', '')),
                recommendations=result.get('recommendations', []),
            )
            if alert:
                logger.info(
                    f"预测触发告警: {alert.alert_no}, "
                    f"级别={alert.alert_level}, node={node_type}/{node_id}"
                )
        except Exception as e:
            logger.error(f"告警评估失败 node={node_type}/{node_id}: {e}")
