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

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger

from app.models.bolt_lstm import BoltLSTMModel, STATUS_LABELS
from app.models.flange_attention import FlangeAttentionModel
from app.models.risk_model import BayesianRiskModel, RiskAssessment
from app.models.prophet_forecaster import ProphetForecaster
from app.services.preprocessing import DataPreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.services.prediction.rule_classifier import RuleBasedClassifier
from app.services.prediction.warning_strategy import WarningStrategyPolicy
from app.services.prediction.repository import PredictionRepository
from app.core.model_version import version_manager
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

        # 模型缓存
        self.bolt_models: Dict[str, BoltLSTMModel] = {}
        self.flange_models: Dict[str, FlangeAttentionModel] = {}

        logger.info("预测编排器初始化完成")

    # ---------- 模型管理 ----------

    def get_bolt_model(self, bolt_id: str) -> BoltLSTMModel:
        """
        获取或创建螺栓 LSTM 模型（带缓存）
        """
        if bolt_id not in self.bolt_models:
            self.bolt_models[bolt_id] = BoltLSTMModel.load_or_create(bolt_id)
        return self.bolt_models[bolt_id]

    def get_flange_model(self, flange_id: str) -> FlangeAttentionModel:
        """
        获取或创建法兰面 Attention 模型（带缓存）
        """
        if flange_id not in self.flange_models:
            self.flange_models[flange_id] = FlangeAttentionModel.load_or_create(flange_id)
        return self.flange_models[flange_id]

    # ---------- 螺栓预测 ----------

    def predict_bolt(
        self,
        bolt_id: str,
        data: np.ndarray,
        timestamps: Optional[List[str]] = None,
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        螺栓状态预测（完整流水线）

        流程: 预处理 → 模型/规则 → 风险评估 → 预警策略 → 审计快照 → 持久化

        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据
            timestamps: 时间戳列表
            save_to_db: 是否保存到数据库

        Returns:
            预测结果字典
        """
        logger.info(f"开始螺栓预测: {bolt_id}, 数据点数: {len(data)}")

        original_status_code = 0
        original_status = ''
        model_type = 'rule'
        probs = None

        # Step 1: 数据预处理
        processed = self.preprocessor.process(
            data,
            remove_anomalies=True,
            normalize=True,
            smooth=True,
        )

        # Step 2: 模型推断（模型未训练则规则兜底）
        model = self.get_bolt_model(bolt_id)
        model_version = 'unknown'
        if model.is_trained:
            model_version = self._get_model_version('bolt', bolt_id)
            original_status_code, confidence, probs = model.predict(
                processed.data,
                return_proba=True,
            )
            model_type = 'lstm'
        else:
            original_status_code, confidence, probs = self.rule_classifier.predict(data)
            model_type = 'rule'

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

        # Step 4: 风险评估
        risk_assessment = self.risk_model.assess_risk(
            data,
            lstm_probs=probs,
            lstm_class=original_status_code,
        )

        # Step 5: 应用预警策略
        final_status_code, final_status = self.warning_policy.apply(
            original_status_code, original_status, confidence
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
        }

        # Step 5: 审计快照
        try:
            self._record_audit_snapshot(
                node_type='bolt',
                node_id=bolt_id,
                input_data=data,
                processed_data=processed.data,
                model_version=model_version,
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

        # Step 6: 持久化
        if save_to_db:
            self.repository.save_bolt_prediction(bolt_id, result)

        # Step 7: 告警评估
        try:
            self._evaluate_alert(
                node_type='bolt',
                node_id=bolt_id,
                result=result,
            )
        except Exception as e:
            logger.warning(f"螺栓 {bolt_id} 告警评估异常: {e}")

        logger.info(f"螺栓预测完成: {bolt_id} -> {final_status}")
        return result

    # ---------- 法兰面预测 ----------

    def predict_flange(
        self,
        flange_id: str,
        multi_bolt_data: List[np.ndarray],
        save_to_db: bool = True,
    ) -> Dict[str, Any]:
        """
        法兰面状态预测（完整流水线）

        流程: 预处理 → 模型/规则 → 风险评估 → 预警策略 → 审计快照 → 持久化

        Args:
            flange_id: 法兰面ID
            multi_bolt_data: 多螺栓数据列表
            save_to_db: 是否保存到数据库

        Returns:
            预测结果字典
        """
        logger.info(f"开始法兰面预测: {flange_id}, 螺栓数: {len(multi_bolt_data)}")

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
        model = self.get_flange_model(flange_id)
        model_version = 'unknown'
        if model.is_trained:
            model_version = self._get_model_version('flange', flange_id)
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
            all_data, lstm_class=original_status_code
        )

        # Step 4: 应用预警策略
        final_status_code, final_status = self.warning_policy.apply(
            original_status_code, original_status, confidence
        )

        # 推荐措施
        recommendations = model.get_recommendation(final_status_code, confidence)

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

        result = {
            'flange_id': flange_id,
            'status': final_status,
            'status_code': final_status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'attention_weights': attention.tolist() if attention is not None else None,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations,
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
        }

        # Step 5: 审计快照
        try:
            self._record_audit_snapshot(
                node_type='flange',
                node_id=flange_id,
                input_data=all_data,
                processed_data=None,
                model_version=model_version,
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

        # Step 6: 持久化
        if save_to_db:
            self.repository.save_flange_prediction(flange_id, result)

        # Step 7: 告警评估
        try:
            self._evaluate_alert(
                node_type='flange',
                node_id=flange_id,
                result=result,
            )
        except Exception as e:
            logger.warning(f"法兰面 {flange_id} 告警评估异常: {e}")

        logger.info(f"法兰面预测完成: {flange_id} -> {final_status}")
        return result

    # ---------- 风险评估（独立接口） ----------

    def assess_risk(
        self,
        node_id: str,
        node_type: str,
        data: np.ndarray,
    ) -> Dict[str, Any]:
        """
        单独的风险评估接口（不经过模型和策略）
        """
        assessment = self.risk_model.assess_risk(data)
        return {
            'node_id': node_id,
            'node_type': node_type,
            'risk_score': float(assessment.score),
            'risk_level': assessment.level.value,
            'factors': assessment.factors,
            'diagnosis': assessment.diagnosis,
            'recommendations': assessment.recommendations,
            'confidence': float(assessment.confidence),
        }

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

    def batch_predict_from_db(self, node_type: str) -> None:
        """
        从数据库批量拉取数据并预测（调度任务入口）

        Args:
            node_type: 'bolt' 或 'flange'
        """
        logger.info(f"开始批量预测: {node_type}")
        try:
            if node_type == 'bolt':
                self._batch_predict_bolts()
            elif node_type == 'flange':
                self._batch_predict_flanges()
            else:
                logger.error(f"未知节点类型: {node_type}")
        except Exception as e:
            logger.error(f"批量预测失败: {e}")

    def _batch_predict_bolts(self) -> None:
        """批量预测所有螺栓"""
        bolt_data = self.repository.fetch_batch_bolt_data(per_bolt_limit=100)

        for bolt_id, data_dict in bolt_data.items():
            try:
                self.predict_bolt(
                    bolt_id=bolt_id,
                    data=np.array(data_dict['data']),
                    timestamps=data_dict['timestamps'],
                    save_to_db=True,
                )
            except Exception as e:
                logger.error(f"螺栓 {bolt_id} 预测失败: {e}")

        logger.info(f"批量螺栓预测完成，共 {len(bolt_data)} 个")

    def _batch_predict_flanges(self) -> None:
        """批量预测所有法兰面"""
        flange_ids = self.repository.fetch_all_flange_ids()

        for flange_id in flange_ids:
            try:
                bolt_series = self.repository.fetch_flange_bolt_data(flange_id)
                if not bolt_series:
                    continue

                multi_bolt_data = [np.array(v) for v in bolt_series.values()]

                self.predict_flange(
                    flange_id=flange_id,
                    multi_bolt_data=multi_bolt_data,
                    save_to_db=True,
                )
            except Exception as e:
                logger.error(f"法兰面 {flange_id} 预测失败: {e}")

        logger.info(f"批量法兰面预测完成，共 {len(flange_ids)} 个")

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
