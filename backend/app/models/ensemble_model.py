"""
集成学习模型模块

使用多种模型集成提高预测准确性。

集成策略:
1. 投票法 (Voting)
2. 加权平均 (Weighted Average)
3. 堆叠 (Stacking)
4. 提升 (Boosting)

使用示例:
    from app.models.ensemble_model import EnsemblePredictor
    
    ensemble = EnsemblePredictor()
    result = ensemble.predict(data)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from loguru import logger

from app.utils.config import config


@dataclass
class EnsemblePrediction:
    """
    集成预测结果
    
    Attributes:
        final_prediction: 最终预测类别
        final_confidence: 最终置信度
        individual_predictions: 各模型预测
        weights: 模型权重
        method: 集成方法
    """
    final_prediction: int
    final_confidence: float
    individual_predictions: Dict[str, int]
    individual_confidences: Dict[str, float]
    weights: Dict[str, float]
    method: str


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


class RuleBasedPredictor(BasePredictor):
    """
    规则基预测器
    
    基于阈值规则进行预测。
    """
    
    def __init__(self):
        """初始化规则预测器"""
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        self.min_normal = thresholds.get('min_normal', 400)
        self.max_normal = thresholds.get('max_normal', 800)
        
    @property
    def name(self) -> str:
        return "rule_based"
    
    def predict(self, data: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """基于规则预测"""
        mean_val = np.mean(data)
        std_val = np.std(data)
        min_val = np.min(data)
        max_val = np.max(data)
        
        # 计算各状态概率
        probs = np.zeros(5)
        
        # 正常范围判断
        if self.min_normal <= mean_val <= self.max_normal:
            if std_val < 20:
                probs[0] = 0.8  # 正常
                probs[1] = 0.2
            else:
                probs[0] = 0.5
                probs[1] = 0.3
                probs[2] = 0.2
        elif mean_val < self.min_normal * 0.8:
            probs[3] = 0.4
            probs[4] = 0.4
            probs[2] = 0.2
        elif mean_val > self.max_normal * 1.2:
            probs[2] = 0.4
            probs[3] = 0.4
            probs[1] = 0.2
        else:
            probs[1] = 0.5
            probs[2] = 0.3
            probs[0] = 0.2
        
        pred_class = np.argmax(probs)
        confidence = probs[pred_class]
        
        return pred_class, confidence, probs


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
        # 提取统计特征
        mean_val = np.mean(data)
        std_val = np.std(data)
        cv = std_val / (mean_val + 1e-8)  # 变异系数
        
        # 趋势分析
        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]
        
        # 基于特征计算概率
        probs = np.zeros(5)
        
        # 变异系数评分
        if cv < 0.03:
            probs[0] += 0.3
        elif cv < 0.1:
            probs[1] += 0.2
            probs[0] += 0.1
        else:
            probs[2] += 0.2
            probs[3] += 0.1
        
        # 趋势评分
        if abs(slope) < 0.1:
            probs[0] += 0.2
        elif slope < -0.5:
            probs[2] += 0.2
            probs[3] += 0.1
        elif slope > 0.5:
            probs[1] += 0.2
        else:
            probs[1] += 0.1
        
        # 归一化
        probs = probs / (probs.sum() + 1e-8)
        
        pred_class = np.argmax(probs)
        confidence = probs[pred_class]
        
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
        
        # 分段趋势分析
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
        
        # 分析趋势变化
        avg_slope = np.mean(slopes)
        slope_trend = slopes[-1] - slopes[0]
        
        if avg_slope < -0.5 and slope_trend < 0:
            # 持续下降
            probs[3] = 0.5
            probs[4] = 0.3
            probs[2] = 0.2
        elif avg_slope > 0.5:
            # 上升趋势
            probs[1] = 0.4
            probs[2] = 0.3
            probs[0] = 0.3
        elif abs(avg_slope) < 0.2:
            # 稳定
            probs[0] = 0.6
            probs[1] = 0.3
            probs[2] = 0.1
        else:
            probs[1] = 0.4
            probs[0] = 0.3
            probs[2] = 0.3
        
        pred_class = np.argmax(probs)
        confidence = probs[pred_class]
        
        return pred_class, confidence, probs


class EnsemblePredictor:
    """
    集成预测器
    
    整合多个基础预测器的结果。
    """
    
    STATUS_LABELS = ['正常', '关注级预警', '检查级预警', '紧急级预警', '故障']
    
    def __init__(
        self,
        method: str = 'weighted_voting',
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化集成预测器
        
        Args:
            method: 集成方法 ('voting', 'weighted_voting', 'soft_voting')
            weights: 模型权重
        """
        self.method = method
        
        # 初始化基础预测器
        self.predictors: List[BasePredictor] = [
            RuleBasedPredictor(),
            StatisticalPredictor(),
            TrendPredictor()
        ]
        
        # 设置权重
        if weights is None:
            self.weights = {p.name: 1.0 / len(self.predictors) for p in self.predictors}
        else:
            self.weights = weights
        
        # 归一化权重
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}
        
        logger.info(f"集成预测器初始化: method={method}, predictors={len(self.predictors)}")
    
    def add_predictor(self, predictor: BasePredictor, weight: float = 1.0) -> None:
        """
        添加预测器
        
        Args:
            predictor: 预测器实例
            weight: 权重
        """
        self.predictors.append(predictor)
        self.weights[predictor.name] = weight
        
        # 重新归一化
        total_weight = sum(self.weights.values())
        self.weights = {k: v / total_weight for k, v in self.weights.items()}
    
    def predict(self, data: np.ndarray) -> EnsemblePrediction:
        """
        集成预测
        
        Args:
            data: 输入数据
            
        Returns:
            EnsemblePrediction: 集成预测结果
        """
        individual_preds = {}
        individual_confs = {}
        all_probs = {}
        
        # 收集各预测器结果
        for predictor in self.predictors:
            try:
                pred, conf, probs = predictor.predict(data)
                individual_preds[predictor.name] = pred
                individual_confs[predictor.name] = conf
                all_probs[predictor.name] = probs
            except Exception as e:
                logger.warning(f"预测器 {predictor.name} 失败: {e}")
        
        # 集成
        if self.method == 'voting':
            final_pred, final_conf = self._hard_voting(individual_preds, individual_confs)
        elif self.method == 'weighted_voting':
            final_pred, final_conf = self._weighted_voting(individual_preds, individual_confs)
        elif self.method == 'soft_voting':
            final_pred, final_conf = self._soft_voting(all_probs)
        else:
            final_pred, final_conf = self._weighted_voting(individual_preds, individual_confs)
        
        return EnsemblePrediction(
            final_prediction=final_pred,
            final_confidence=final_conf,
            individual_predictions=individual_preds,
            individual_confidences=individual_confs,
            weights=self.weights,
            method=self.method
        )
    
    def _hard_voting(
        self,
        predictions: Dict[str, int],
        confidences: Dict[str, float]
    ) -> Tuple[int, float]:
        """硬投票"""
        if not predictions:
            return 0, 0.0
        
        # 计票
        votes = {}
        for name, pred in predictions.items():
            votes[pred] = votes.get(pred, 0) + 1
        
        # 选择票数最多的
        final_pred = max(votes.keys(), key=lambda x: votes[x])
        
        # 计算置信度（投票比例）
        total_votes = len(predictions)
        final_conf = votes[final_pred] / total_votes
        
        return final_pred, final_conf
    
    def _weighted_voting(
        self,
        predictions: Dict[str, int],
        confidences: Dict[str, float]
    ) -> Tuple[int, float]:
        """加权投票"""
        if not predictions:
            return 0, 0.0
        
        # 加权计票
        votes = {}
        for name, pred in predictions.items():
            weight = self.weights.get(name, 1.0)
            conf = confidences.get(name, 0.5)
            weighted_vote = weight * conf
            votes[pred] = votes.get(pred, 0) + weighted_vote
        
        # 选择加权票数最多的
        final_pred = max(votes.keys(), key=lambda x: votes[x])
        
        # 计算置信度
        total_weight = sum(votes.values())
        final_conf = votes[final_pred] / total_weight if total_weight > 0 else 0
        
        return final_pred, final_conf
    
    def _soft_voting(
        self,
        all_probs: Dict[str, np.ndarray]
    ) -> Tuple[int, float]:
        """软投票（概率平均）"""
        if not all_probs:
            return 0, 0.0
        
        # 加权平均概率
        avg_probs = np.zeros(5)
        total_weight = 0
        
        for name, probs in all_probs.items():
            weight = self.weights.get(name, 1.0)
            avg_probs += weight * probs
            total_weight += weight
        
        avg_probs /= total_weight
        
        final_pred = np.argmax(avg_probs)
        final_conf = avg_probs[final_pred]
        
        return int(final_pred), float(final_conf)
    
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
            'individual_results': {
                name: {
                    'prediction': self.STATUS_LABELS[pred],
                    'confidence': result.individual_confidences.get(name, 0)
                }
                for name, pred in result.individual_predictions.items()
            },
            'weights': result.weights
        }
    
    def update_weights(self, performance_metrics: Dict[str, float]) -> None:
        """
        根据性能指标更新权重
        
        Args:
            performance_metrics: {predictor_name: accuracy}
        """
        # 基于准确率更新权重
        total = sum(performance_metrics.values())
        
        if total > 0:
            for name in self.weights:
                if name in performance_metrics:
                    self.weights[name] = performance_metrics[name] / total
        
        logger.info(f"权重已更新: {self.weights}")
