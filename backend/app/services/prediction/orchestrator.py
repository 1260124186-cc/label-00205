"""
预测编排器模块

按流水线方式组织预测流程：
    数据预处理 → 模型推断 → 风险评估 → 预警策略 → 结果持久化

编排器本身不包含具体实现，而是通过组合以下组件完成：
- DataPreprocessor / FeatureEngineer: 数据预处理
- BoltLSTMModel / FlangeAttentionModel: 机器学习模型
- RuleBasedClassifier: 规则兜底
- BayesianRiskModel: 风险评估
- ProphetForecaster: 月度趋势预测
- WarningStrategyPolicy: 预警策略
- PredictionRepository: DB 读写
"""

import numpy as np
from typing import Dict, List, Optional, Any
from loguru import logger

from app.models.bolt_lstm import BoltLSTMModel, STATUS_LABELS
from app.models.flange_attention import FlangeAttentionModel
from app.models.risk_model import BayesianRiskModel
from app.models.prophet_forecaster import ProphetForecaster
from app.services.preprocessing import DataPreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.services.prediction.rule_classifier import RuleBasedClassifier
from app.services.prediction.warning_strategy import WarningStrategyPolicy
from app.services.prediction.repository import PredictionRepository


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

        流程: 预处理 → 模型/规则 → 风险评估 → 预警策略 → 持久化

        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据
            timestamps: 时间戳列表
            save_to_db: 是否保存到数据库

        Returns:
            预测结果字典
        """
        logger.info(f"开始螺栓预测: {bolt_id}, 数据点数: {len(data)}")

        # Step 1: 数据预处理
        processed = self.preprocessor.process(
            data,
            remove_anomalies=True,
            normalize=True,
            smooth=True,
        )

        # Step 2: 模型推断（模型未训练则规则兜底）
        model = self.get_bolt_model(bolt_id)
        if model.is_trained:
            status_code, confidence, probs = model.predict(
                processed.data,
                return_proba=True,
            )
        else:
            status_code, confidence, probs = self.rule_classifier.predict(data)

        status = STATUS_LABELS.get(status_code, '未知')

        # Step 3: 风险评估
        risk_assessment = self.risk_model.assess_risk(
            data,
            lstm_probs=probs,
            lstm_class=status_code,
        )

        # Step 4: 应用预警策略
        status_code, status = self.warning_policy.apply(
            status_code, status, confidence
        )

        # 推荐措施（优先用模型建议，兜底使用风险评估建议）
        recommendations = model.get_recommendation(status_code, confidence)

        result = {
            'bolt_id': bolt_id,
            'status': status,
            'status_code': status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations,
            'recent_time': timestamps[-1] if timestamps else None,
        }

        # Step 5: 持久化
        if save_to_db:
            self.repository.save_bolt_prediction(bolt_id, result)

        logger.info(f"螺栓预测完成: {bolt_id} -> {status}")
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

        Args:
            flange_id: 法兰面ID
            multi_bolt_data: 多螺栓数据列表
            save_to_db: 是否保存到数据库

        Returns:
            预测结果字典
        """
        logger.info(f"开始法兰面预测: {flange_id}, 螺栓数: {len(multi_bolt_data)}")

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
        if model.is_trained:
            status_code, confidence, attention = model.predict(
                processed_bolts,
                return_attention=True,
            )
        else:
            status_code, confidence = self.rule_classifier.aggregate_predictions(
                multi_bolt_data
            )
            attention = None

        status = STATUS_LABELS.get(status_code, '未知')

        # Step 3: 风险评估（使用所有螺栓数据拼接）
        all_data = np.concatenate(multi_bolt_data)
        risk_assessment = self.risk_model.assess_risk(all_data, lstm_class=status_code)

        # Step 4: 应用预警策略
        status_code, status = self.warning_policy.apply(
            status_code, status, confidence
        )

        # 推荐措施
        recommendations = model.get_recommendation(status_code, confidence)

        result = {
            'flange_id': flange_id,
            'status': status,
            'status_code': status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'attention_weights': attention.tolist() if attention is not None else None,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations,
        }

        # Step 5: 持久化
        if save_to_db:
            self.repository.save_flange_prediction(flange_id, result)

        logger.info(f"法兰面预测完成: {flange_id} -> {status}")
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
