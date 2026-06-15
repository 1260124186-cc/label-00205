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

        # Step 2: 模型推断（模型未训练则规则兜底）
        model = self.get_bolt_model(bolt_id, version=version)
        model_version_str = version or 'unknown'
        if model.is_trained:
            if version is None:
                model_version_str = self._get_model_version('bolt', bolt_id)
            original_status_code, confidence, probs = model.predict(
                processed.data,
                return_proba=True,
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

        # Step 4: 风险评估
        risk_assessment = self.risk_model.assess_risk(
            data,
            lstm_probs=probs,
            lstm_class=original_status_code,
            node_type='bolt',
            node_id=bolt_id,
        )

        # Step 5: 应用预警策略
        final_status_code, final_status = self.warning_policy.apply(
            original_status_code, original_status, confidence,
            risk_level=risk_assessment.level.value,
            lstm_confidence=float(confidence),
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

        # Step 2: 模型推断（模型未训练则规则聚合兜底）
        model = self.get_flange_model(flange_id, version=version)
        model_version_str = version or 'unknown'
        if model.is_trained:
            if version is None:
                model_version_str = self._get_model_version('flange', flange_id)
            original_status_code, confidence, attention = model.predict(
                processed_bolts,
                return_attention=True,
            )
            model_type = 'attention'
        else:
            original_status_code, confidence = self.rule_classifier.aggregate_predictions(
                multi_bolt_data
            )
            attention = None

        original_status = STATUS_LABELS.get(original_status_code, '未知')

        # Step 3: 风险评估（使用所有螺栓数据拼接）
        all_data = np.concatenate(multi_bolt_data)
        risk_assessment = self.risk_model.assess_risk(
            all_data, lstm_class=original_status_code,
            node_type='flange', node_id=flange_id,
        )

        # Step 4: 应用预警策略
        final_status_code, final_status = self.warning_policy.apply(
            original_status_code, original_status, confidence,
            risk_level=risk_assessment.level.value,
            lstm_confidence=float(confidence),
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
        }

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
