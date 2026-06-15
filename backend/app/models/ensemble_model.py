"""
集成学习模型模块

使用多种模型集成提高预测准确性。

集成策略:
1. 硬投票 (Hard Voting)
2. 软投票 (Soft Voting)
3. 加权投票 (Weighted Voting)

使用示例:
    from app.models.ensemble_model import BoltEnsemblePredictor

    ensemble = BoltEnsemblePredictor(bolt_id="B001")
    result = ensemble.predict(data)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import defaultdict
from loguru import logger

from app.utils.config import config


@dataclass
class EnsemblePrediction:
    """
    集成预测结果

    Attributes:
        final_prediction: 最终预测类别
        final_confidence: 最终置信度
        final_probs: 最终概率分布
        individual_predictions: 各模型预测类别
        individual_confidences: 各模型置信度
        individual_probs: 各模型概率分布
        weights: 模型权重
        method: 集成方法
        prediction_source: 预测来源 (lstm / ensemble / rule)
    """
    final_prediction: int
    final_confidence: float
    final_probs: Optional[np.ndarray] = None
    individual_predictions: Dict[str, int] = field(default_factory=dict)
    individual_confidences: Dict[str, float] = field(default_factory=dict)
    individual_probs: Dict[str, np.ndarray] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    method: str = "weighted_voting"
    prediction_source: str = "ensemble"


class BasePredictor(ABC):
    """预测器基类"""

    @abstractmethod
    def predict(self, data: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """
        预测

        Args:
            data: 输入数据

        Returns:
            Tuple: (预测类别, 置信度, 类别概率)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称"""
        pass


class LSTMPredictorAdapter(BasePredictor):
    """
    LSTM 预测器适配器

    将 BoltLSTMModel 包装为 BasePredictor 接口。
    """

    def __init__(self, bolt_id: str, version: Optional[str] = None):
        """
        初始化 LSTM 预测器适配器

        Args:
            bolt_id: 螺栓ID
            version: 模型版本号，None 表示当前活动版本
        """
        from app.models.bolt_lstm import BoltLSTMModel

        self._bolt_id = bolt_id
        self._version = version
        self._model: Optional[BoltLSTMModel] = None
        self._is_trained = False

    @property
    def name(self) -> str:
        return "lstm"

    @property
    def is_trained(self) -> bool:
        """模型是否已训练"""
        if self._model is None:
            self._load_model()
        return self._is_trained

    def _load_model(self) -> None:
        """懒加载模型"""
        from app.models.bolt_lstm import BoltLSTMModel

        try:
            if self._version is None:
                self._model = BoltLSTMModel.load_or_create(self._bolt_id)
            else:
                self._model = BoltLSTMModel(bolt_id=self._bolt_id)
                from app.services.model_version_service import get_model_version_service
                service = get_model_version_service()
                model_path = service.get_model_file_path('bolt', self._bolt_id, self._version)
                if model_path and __import__('os').path.exists(model_path):
                    self._model.load(model_path)
                else:
                    self._is_trained = False
                    return
            self._is_trained = self._model.is_trained
        except Exception as e:
            logger.warning(f"LSTM 模型加载失败: {e}")
            self._is_trained = False

    def predict(self, data: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """
        使用 LSTM 模型预测

        Args:
            data: 输入数据

        Returns:
            Tuple: (预测类别, 置信度, 类别概率)
        """
        if self._model is None:
            self._load_model()

        if not self._is_trained or self._model is None:
            probs = np.zeros(5)
            probs[0] = 0.5
            probs[1] = 0.3
            probs[2] = 0.2
            return 0, 0.5, probs

        try:
            pred_class, confidence, probs = self._model.predict(data, return_proba=True)
            if probs is None:
                probs = np.zeros(5)
                probs[pred_class] = confidence
            return int(pred_class), float(confidence), probs
        except Exception as e:
            logger.warning(f"LSTM 预测失败: {e}")
            probs = np.zeros(5)
            probs[0] = 0.5
            return 0, 0.5, probs


class RuleClassifierAdapter(BasePredictor):
    """
    规则分类器适配器

    将 RuleBasedClassifier 包装为 BasePredictor 接口。
    """

    def __init__(self):
        """初始化规则分类器适配器"""
        from app.services.prediction.rule_classifier import RuleBasedClassifier
        self._classifier = RuleBasedClassifier()

    @property
    def name(self) -> str:
        return "rule"

    def predict(self, data: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """
        使用规则分类器预测

        Args:
            data: 输入数据

        Returns:
            Tuple: (预测类别, 置信度, 类别概率)
        """
        pred_class, confidence, _ = self._classifier.predict(data)

        probs = np.zeros(5)
        probs[pred_class] = confidence
        remaining = 1.0 - confidence

        if pred_class > 0:
            probs[pred_class - 1] = remaining * 0.6
            if pred_class < 4:
                probs[pred_class + 1] = remaining * 0.4
            else:
                probs[pred_class - 1] += remaining * 0.4
        else:
            probs[1] = remaining * 0.7
            probs[2] = remaining * 0.3

        probs = probs / (probs.sum() + 1e-8)
        return int(pred_class), float(confidence), probs


class StatisticalPredictor(BasePredictor):
    """
    统计预测器

    基于统计特征进行预测。
    """

    @property
    def name(self) -> str:
        return "statistical"

    def predict(self, data: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """基于统计特征预测"""
        mean_val = np.mean(data)
        std_val = np.std(data)
        cv = std_val / (mean_val + 1e-8)

        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]

        probs = np.zeros(5)

        if cv < 0.03:
            probs[0] += 0.3
        elif cv < 0.1:
            probs[1] += 0.2
            probs[0] += 0.1
        else:
            probs[2] += 0.2
            probs[3] += 0.1

        if abs(slope) < 0.1:
            probs[0] += 0.2
        elif slope < -0.5:
            probs[2] += 0.2
            probs[3] += 0.1
        elif slope > 0.5:
            probs[1] += 0.2
        else:
            probs[1] += 0.1

        probs = probs / (probs.sum() + 1e-8)

        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])

        return pred_class, confidence, probs


class TrendPredictor(BasePredictor):
    """
    趋势预测器

    基于时间序列趋势进行预测。
    """

    @property
    def name(self) -> str:
        return "trend"

    def predict(self, data: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """基于趋势预测"""
        probs = np.zeros(5)

        if len(data) < 10:
            probs[0] = 1.0
            return 0, 1.0, probs

        n = len(data)
        segments = 3
        seg_len = n // segments

        slopes = []
        for i in range(segments):
            start = i * seg_len
            end = (i + 1) * seg_len if i < segments - 1 else n
            seg = data[start:end]
            x = np.arange(len(seg))
            slope = np.polyfit(x, seg, 1)[0]
            slopes.append(slope)

        avg_slope = np.mean(slopes)
        slope_trend = slopes[-1] - slopes[0]

        if avg_slope < -0.5 and slope_trend < 0:
            probs[3] = 0.5
            probs[4] = 0.3
            probs[2] = 0.2
        elif avg_slope > 0.5:
            probs[1] = 0.4
            probs[2] = 0.3
            probs[0] = 0.3
        elif abs(avg_slope) < 0.2:
            probs[0] = 0.6
            probs[1] = 0.3
            probs[2] = 0.1
        else:
            probs[1] = 0.4
            probs[0] = 0.3
            probs[2] = 0.3

        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])

        return pred_class, confidence, probs


class BoltEnsemblePredictor:
    """
    螺栓集成预测器

    整合 LSTM、规则、统计、趋势等多个预测器的结果。
    支持 hard/soft/weighted 三种投票策略。
    支持基于历史表现的动态权重调整。
    """

    STATUS_LABELS = ['正常', '关注级预警', '检查级预警', '紧急级预警', '故障']

    def __init__(
        self,
        bolt_id: str,
        method: str = None,
        weights: Optional[Dict[str, float]] = None,
        version: Optional[str] = None,
    ):
        """
        初始化螺栓集成预测器

        Args:
            bolt_id: 螺栓ID
            method: 集成方法 ('hard' / 'soft' / 'weighted')
            weights: 模型权重 {predictor_name: weight}
            version: LSTM 模型版本号
        """
        self.bolt_id = bolt_id
        self.method = method or config.get('ensemble.default_method', 'weighted')
        self.version = version

        self.predictors: List[BasePredictor] = []
        self.weights: Dict[str, float] = {}

        self._init_predictors()
        self._init_weights(weights)

        self._performance_history: Dict[str, List[float]] = defaultdict(list)
        self._ema_accuracy: Dict[str, float] = {}
        self._ema_alpha = config.get('ensemble.dynamic_weighting.ema_alpha', 0.3)

        logger.info(
            f"螺栓集成预测器初始化: bolt_id={bolt_id}, "
            f"method={self.method}, predictors={len(self.predictors)}"
        )

    def _init_predictors(self) -> None:
        """初始化预测器列表"""
        enabled_predictors = config.get(
            'ensemble.enabled_predictors',
            ['lstm', 'rule', 'statistical', 'trend']
        )

        if 'lstm' in enabled_predictors:
            lstm_predictor = LSTMPredictorAdapter(self.bolt_id, version=self.version)
            if lstm_predictor.is_trained:
                self.predictors.append(lstm_predictor)
            else:
                logger.debug(f"LSTM 模型未训练，跳过: {self.bolt_id}")

        if 'rule' in enabled_predictors:
            self.predictors.append(RuleClassifierAdapter())

        if 'statistical' in enabled_predictors:
            self.predictors.append(StatisticalPredictor())

        if 'trend' in enabled_predictors:
            self.predictors.append(TrendPredictor())

        if not self.predictors:
            self.predictors.append(RuleClassifierAdapter())
            logger.warning("无可用预测器，降级为仅规则预测")

    def _init_weights(self, weights: Optional[Dict[str, float]] = None) -> None:
        """初始化权重"""
        if weights is not None:
            self.weights = {k: v for k, v in weights.items() if k in [p.name for p in self.predictors]}
        else:
            config_weights = config.get('ensemble.default_weights', {})
            for p in self.predictors:
                if p.name in config_weights:
                    self.weights[p.name] = config_weights[p.name]
                else:
                    self.weights[p.name] = 1.0

        self._normalize_weights()

    def _normalize_weights(self) -> None:
        """归一化权重"""
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
        else:
            n = len(self.predictors)
            self.weights = {p.name: 1.0 / n for p in self.predictors}

    def add_predictor(self, predictor: BasePredictor, weight: float = 1.0) -> None:
        """
        添加预测器

        Args:
            predictor: 预测器实例
            weight: 初始权重
        """
        self.predictors.append(predictor)
        self.weights[predictor.name] = weight
        self._normalize_weights()
        logger.info(f"已添加预测器: {predictor.name}, 权重={weight}")

    def set_method(self, method: str) -> None:
        """
        设置投票策略

        Args:
            method: 'hard' / 'soft' / 'weighted'
        """
        valid_methods = ['hard', 'soft', 'weighted']
        if method not in valid_methods:
            raise ValueError(f"无效的投票策略: {method}, 有效值: {valid_methods}")
        self.method = method
        logger.info(f"投票策略已切换为: {method}")

    def set_weights(self, weights: Dict[str, float]) -> None:
        """
        设置预测器权重

        Args:
            weights: {predictor_name: weight}
        """
        for name, weight in weights.items():
            if name in self.weights:
                self.weights[name] = weight
        self._normalize_weights()
        logger.info(f"权重已更新: {self.weights}")

    def predict(self, data: np.ndarray) -> EnsemblePrediction:
        """
        集成预测

        Args:
            data: 输入数据

        Returns:
            EnsemblePrediction: 集成预测结果
        """
        individual_preds: Dict[str, int] = {}
        individual_confs: Dict[str, float] = {}
        individual_probs: Dict[str, np.ndarray] = {}

        for predictor in self.predictors:
            try:
                pred, conf, probs = predictor.predict(data)
                individual_preds[predictor.name] = int(pred)
                individual_confs[predictor.name] = float(conf)
                individual_probs[predictor.name] = probs
            except Exception as e:
                logger.warning(f"预测器 {predictor.name} 失败: {e}")

        if not individual_preds:
            logger.error("所有预测器均失败，返回默认结果")
            return EnsemblePrediction(
                final_prediction=0,
                final_confidence=0.5,
                final_probs=np.array([0.5, 0.3, 0.1, 0.05, 0.05]),
                method=self.method,
                prediction_source="rule",
            )

        if self.method == 'hard':
            final_pred, final_conf = self._hard_voting(individual_preds)
            final_probs = None
        elif self.method == 'soft':
            final_pred, final_conf, final_probs = self._soft_voting(individual_probs)
        elif self.method == 'weighted':
            final_pred, final_conf, final_probs = self._weighted_voting(
                individual_preds, individual_confs, individual_probs
            )
        else:
            final_pred, final_conf, final_probs = self._weighted_voting(
                individual_preds, individual_confs, individual_probs
            )

        prediction_source = self._determine_source(individual_preds, final_pred)

        return EnsemblePrediction(
            final_prediction=int(final_pred),
            final_confidence=float(final_conf),
            final_probs=final_probs,
            individual_predictions=individual_preds,
            individual_confidences=individual_confs,
            individual_probs=individual_probs,
            weights=dict(self.weights),
            method=self.method,
            prediction_source=prediction_source,
        )

    def _hard_voting(self, predictions: Dict[str, int]) -> Tuple[int, float]:
        """
        硬投票（多数表决）

        Args:
            predictions: {predictor_name: prediction_class}

        Returns:
            Tuple: (final_class, confidence)
        """
        if not predictions:
            return 0, 0.0

        votes: Dict[int, int] = defaultdict(int)
        for pred in predictions.values():
            votes[pred] += 1

        final_pred = max(votes.keys(), key=lambda x: votes[x])
        total_votes = len(predictions)
        final_conf = votes[final_pred] / total_votes

        return int(final_pred), float(final_conf)

    def _soft_voting(self, all_probs: Dict[str, np.ndarray]) -> Tuple[int, float, np.ndarray]:
        """
        软投票（概率平均）

        Args:
            all_probs: {predictor_name: probability_array}

        Returns:
            Tuple: (final_class, confidence, final_probabilities)
        """
        if not all_probs:
            probs = np.zeros(5)
            probs[0] = 0.5
            return 0, 0.5, probs

        avg_probs = np.zeros(5)
        count = 0

        for probs in all_probs.values():
            avg_probs += probs
            count += 1

        if count > 0:
            avg_probs /= count

        final_pred = int(np.argmax(avg_probs))
        final_conf = float(avg_probs[final_pred])

        return final_pred, final_conf, avg_probs

    def _weighted_voting(
        self,
        predictions: Dict[str, int],
        confidences: Dict[str, float],
        all_probs: Dict[str, np.ndarray],
    ) -> Tuple[int, float, np.ndarray]:
        """
        加权投票（综合权重 + 置信度 + 概率）

        加权方式:
        - 使用权重 × 置信度 作为投票权重
        - 对概率进行加权平均

        Args:
            predictions: {predictor_name: prediction_class}
            confidences: {predictor_name: confidence}
            all_probs: {predictor_name: probability_array}

        Returns:
            Tuple: (final_class, confidence, final_probabilities)
        """
        if not all_probs:
            probs = np.zeros(5)
            probs[0] = 0.5
            return 0, 0.5, probs

        weighted_probs = np.zeros(5)
        total_weight = 0.0

        for name, probs in all_probs.items():
            weight = self.weights.get(name, 1.0)
            conf = confidences.get(name, 0.5)
            adjusted_weight = weight * (0.5 + 0.5 * conf)
            weighted_probs += adjusted_weight * probs
            total_weight += adjusted_weight

        if total_weight > 0:
            weighted_probs /= total_weight

        final_pred = int(np.argmax(weighted_probs))
        final_conf = float(weighted_probs[final_pred])

        return final_pred, final_conf, weighted_probs

    def _determine_source(
        self, individual_preds: Dict[str, int], final_pred: int
    ) -> str:
        """
        确定预测来源

        Args:
            individual_preds: 各预测器结果
            final_pred: 最终结果

        Returns:
            str: 'lstm' / 'ensemble' / 'rule'
        """
        if len(individual_preds) <= 1:
            if 'lstm' in individual_preds:
                return 'lstm'
            elif 'rule' in individual_preds:
                return 'rule'
            return 'ensemble'

        lstm_pred = individual_preds.get('lstm')
        if lstm_pred is not None and lstm_pred == final_pred:
            if self.method == 'hard' and list(individual_preds.values()).count(final_pred) == 1:
                return 'lstm'

        return 'ensemble'

    def predict_with_details(self, data: np.ndarray) -> Dict[str, Any]:
        """
        带详细信息的预测

        Args:
            data: 输入数据

        Returns:
            Dict: 详细预测结果
        """
        result = self.predict(data)

        return {
            'status': self.STATUS_LABELS[result.final_prediction],
            'status_code': result.final_prediction,
            'confidence': result.final_confidence,
            'ensemble_method': result.method,
            'prediction_source': result.prediction_source,
            'individual_results': {
                name: {
                    'prediction': self.STATUS_LABELS[pred],
                    'prediction_code': pred,
                    'confidence': result.individual_confidences.get(name, 0),
                    'weight': result.weights.get(name, 0),
                }
                for name, pred in result.individual_predictions.items()
            },
            'weights': result.weights,
        }

    def update_weights(
        self,
        performance_metrics: Dict[str, float],
        use_ema: bool = True,
    ) -> Dict[str, float]:
        """
        根据性能指标动态更新权重

        支持 EMA (指数移动平均) 平滑权重更新，防止波动过大。

        Args:
            performance_metrics: {predictor_name: accuracy_score}
            use_ema: 是否使用 EMA 平滑

        Returns:
            Dict: 更新后的权重
        """
        if not performance_metrics:
            logger.warning("性能指标为空，跳过权重更新")
            return self.weights

        for name, score in performance_metrics.items():
            if name not in self.weights:
                continue

            self._performance_history[name].append(score)

            if use_ema:
                if name in self._ema_accuracy:
                    self._ema_accuracy[name] = (
                        self._ema_alpha * score
                        + (1 - self._ema_alpha) * self._ema_accuracy[name]
                    )
                else:
                    self._ema_accuracy[name] = score
            else:
                self._ema_accuracy[name] = score

        valid_scores = {
            name: self._ema_accuracy.get(name, score)
            for name, score in performance_metrics.items()
            if name in self.weights
        }

        if not valid_scores:
            return self.weights

        total_score = sum(valid_scores.values())
        if total_score > 0:
            new_weights = {}
            for name in self.weights:
                if name in valid_scores:
                    new_weights[name] = valid_scores[name] / total_score
                else:
                    new_weights[name] = self.weights[name] * 0.5

            self.weights = new_weights
            self._normalize_weights()

        logger.info(
            f"权重已更新: {self.weights}, "
            f"EMA准确率: {self._ema_accuracy}"
        )

        return dict(self.weights)

    def get_weights(self) -> Dict[str, float]:
        """获取当前权重"""
        return dict(self.weights)

    def get_performance_history(self) -> Dict[str, List[float]]:
        """获取性能历史记录"""
        return {k: list(v) for k, v in self._performance_history.items()}

    def get_ema_accuracy(self) -> Dict[str, float]:
        """获取 EMA 平滑后的准确率"""
        return dict(self._ema_accuracy)
