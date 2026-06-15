"""
贝叶斯风险评估模型

基于贝叶斯网络的风险评分和等级评估模型。

功能:
1. 风险评分计算 (1-10分)
2. 风险等级评估 (低/中/高)
3. 风险概率分布 P(高/中/低)
4. 因子贡献度分析 (类 SHAP)
5. 诊断建议生成
6. 与LSTM模型输出融合
7. 可配置权重/阈值 + per-node 校准

风险等级:
    - 高风险: 1-3分
    - 中风险: 4-7分
    - 低风险: 8-10分

使用示例:
    from app.models.risk_model import BayesianRiskModel

    model = BayesianRiskModel()
    assessment = model.assess_risk(preload_data, lstm_probs)
    prob = model.compute_probability_distribution(assessment)
    explain = model.explain_risk(data, lstm_probs, lstm_class)
"""

import numpy as np
from typing import Tuple, Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.utils.config import config


class RiskLevel(Enum):
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


DEFAULT_PRIOR_WEIGHTS = {
    'mean_deviation': 0.25,
    'volatility': 0.20,
    'trend': 0.20,
    'extreme_values': 0.15,
    'lstm_prediction': 0.20,
}

DEFAULT_RISK_THRESHOLDS = {
    'high': 3,
    'medium': 7,
}

DEFAULT_PRELOAD_THRESHOLDS = {
    'min_normal': 400,
    'max_normal': 800,
    'warning_deviation': 0.1,
    'critical_deviation': 0.2,
}

_node_calibration_cache: Dict[str, Dict[str, Any]] = {}


def _load_node_calibration(node_type: Optional[str], node_id: Optional[str]) -> Dict[str, Any]:
    cache_key = f"{node_type or ''}:{node_id or ''}"
    if cache_key in _node_calibration_cache:
        return _node_calibration_cache[cache_key]

    cal = {}
    try:
        from app.utils.database import get_db
        with get_db() as db:
            if db is None:
                return cal
            try:
                row = db.execute(
                    "SELECT weights, thresholds FROM sc_risk_calibration "
                    "WHERE node_type = :nt AND node_id = :nid AND is_active = 1 "
                    "ORDER BY version DESC LIMIT 1",
                    {"nt": node_type, "nid": node_id},
                ).first()
                if row is not None:
                    import json
                    if row[0]:
                        cal['prior_weights'] = json.loads(row[0])
                    if row[1]:
                        cal['risk_thresholds'] = json.loads(row[1])
            except Exception:
                pass
    except Exception:
        pass

    _node_calibration_cache[cache_key] = cal
    return cal


def invalidate_node_calibration_cache():
    global _node_calibration_cache
    _node_calibration_cache = {}


@dataclass
class RiskProbabilityDistribution:
    p_high: float
    p_medium: float
    p_low: float

    def to_dict(self) -> Dict[str, float]:
        return {
            'p_high': round(self.p_high, 4),
            'p_medium': round(self.p_medium, 4),
            'p_low': round(self.p_low, 4),
        }


@dataclass
class FactorContribution:
    name: str
    display_name: str
    raw_score: float
    weight: float
    weighted_score: float
    contribution_ratio: float
    direction: str


@dataclass
class RiskExplanation:
    risk_score: float
    risk_level: str
    probability_distribution: RiskProbabilityDistribution
    factor_contributions: List[FactorContribution]
    base_value: float
    total_contribution: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'probability_distribution': self.probability_distribution.to_dict(),
            'factor_contributions': [
                {
                    'name': fc.name,
                    'display_name': fc.display_name,
                    'raw_score': round(fc.raw_score, 4),
                    'weight': round(fc.weight, 4),
                    'weighted_score': round(fc.weighted_score, 4),
                    'contribution_ratio': round(fc.contribution_ratio, 4),
                    'direction': fc.direction,
                }
                for fc in self.factor_contributions
            ],
            'base_value': round(self.base_value, 4),
            'total_contribution': round(self.total_contribution, 4),
            'summary': self.summary,
        }


@dataclass
class RiskAssessment:
    score: float
    level: RiskLevel
    factors: List[str]
    diagnosis: str
    recommendations: List[str]
    confidence: float
    probability_distribution: Optional[RiskProbabilityDistribution] = None
    factor_contributions: Optional[List[FactorContribution]] = None


class BayesianRiskModel:

    def __init__(self):
        self.thresholds = dict(DEFAULT_PRELOAD_THRESHOLDS)
        cfg_thresholds = config.get('risk_assessment.preload_thresholds', {})
        if cfg_thresholds:
            self.thresholds.update(cfg_thresholds)

        self.risk_thresholds = dict(DEFAULT_RISK_THRESHOLDS)
        cfg_risk = config.get('risk_assessment.risk_thresholds', {})
        if cfg_risk:
            self.risk_thresholds.update(cfg_risk)
        else:
            ht = config.get('risk_assessment.high_risk_threshold')
            mt = config.get('risk_assessment.medium_risk_threshold')
            if ht is not None:
                self.risk_thresholds['high'] = ht
            if mt is not None:
                self.risk_thresholds['medium'] = mt

        self.prior_weights = dict(DEFAULT_PRIOR_WEIGHTS)
        cfg_weights = config.get('risk_assessment.prior_weights', {})
        if cfg_weights:
            self.prior_weights.update(cfg_weights)

        self.diagnosis_templates = {
            RiskLevel.LOW: "预紧力数据稳定，处于正常工作范围内。",
            RiskLevel.MEDIUM: "预紧力出现一定波动，需要密切关注变化趋势。",
            RiskLevel.HIGH: "预紧力异常明显，存在潜在故障风险，需要立即采取措施。",
        }

        logger.info("贝叶斯风险评估模型初始化完成")

    def get_effective_weights(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Dict[str, float]:
        weights = dict(self.prior_weights)
        if node_type and node_id:
            cal = _load_node_calibration(node_type, node_id)
            if 'prior_weights' in cal:
                weights.update(cal['prior_weights'])
        return weights

    def get_effective_thresholds(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        thresholds = dict(self.risk_thresholds)
        if node_type and node_id:
            cal = _load_node_calibration(node_type, node_id)
            if 'risk_thresholds' in cal:
                thresholds.update(cal['risk_thresholds'])
        return thresholds

    def calculate_deviation_score(self, data: np.ndarray) -> float:
        mean_val = np.mean(data)
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']

        if min_normal <= mean_val <= max_normal:
            center = (min_normal + max_normal) / 2
            range_half = (max_normal - min_normal) / 2
            deviation = abs(mean_val - center) / range_half
            score = 1.0 - deviation * 0.3
        elif mean_val < min_normal:
            deviation = (min_normal - mean_val) / min_normal
            score = max(0, 1.0 - deviation * 2)
        else:
            deviation = (mean_val - max_normal) / max_normal
            score = max(0, 1.0 - deviation * 2)

        return float(np.clip(score, 0, 1))

    def calculate_volatility_score(self, data: np.ndarray) -> float:
        if len(data) < 2:
            return 1.0

        mean_val = np.mean(data)
        std_val = np.std(data)
        cv = std_val / (mean_val + 1e-6)

        if cv < 0.05:
            score = 1.0
        elif cv < 0.10:
            score = 0.8
        elif cv < 0.20:
            score = 0.5
        else:
            score = max(0, 1.0 - cv)

        return score

    def calculate_trend_score(self, data: np.ndarray) -> float:
        if len(data) < 3:
            return 1.0

        x = np.arange(len(data))
        coeffs = np.polyfit(x, data, 1)
        slope = coeffs[0]

        mean_val = np.mean(data)
        change_rate = abs(slope) / (mean_val + 1e-6)

        if change_rate < 0.001:
            score = 1.0
        elif change_rate < 0.005:
            score = 0.8
        elif change_rate < 0.01:
            score = 0.5
        else:
            score = max(0, 1.0 - change_rate * 10)

        return score

    def calculate_extreme_score(self, data: np.ndarray) -> float:
        min_val = np.min(data)
        max_val = np.max(data)

        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']
        critical_dev = self.thresholds['critical_deviation']

        critical_min = min_normal * (1 - critical_dev)
        critical_max = max_normal * (1 + critical_dev)

        score = 1.0

        if min_val < critical_min:
            score -= 0.5
        elif min_val < min_normal:
            score -= 0.2

        if max_val > critical_max:
            score -= 0.5
        elif max_val > max_normal:
            score -= 0.2

        if len(data) > 1:
            changes = np.diff(data)
            if np.any(changes < -np.mean(data) * 0.5):
                score -= 0.3

        return max(0, score)

    def calculate_lstm_score(self, lstm_probs: Optional[np.ndarray]) -> float:
        if lstm_probs is None:
            return 0.5

        weights = np.array([1.0, 0.7, 0.4, 0.2, 0.0])
        score = np.sum(lstm_probs * weights)

        return float(np.clip(score, 0, 1))

    def compute_probability_distribution(
        self,
        weighted_score: float,
        risk_thresholds: Optional[Dict[str, Any]] = None,
    ) -> RiskProbabilityDistribution:
        """
        基于加权评分计算 P(高/中/低) 概率分布。

        使用 softmax 式映射：将 weighted_score 映射到三个区间的中心，
        然后用高斯核计算各区间概率。
        """
        thresholds = risk_thresholds or self.risk_thresholds

        high_boundary = thresholds['high'] / 10.0
        medium_boundary = thresholds['medium'] / 10.0

        high_center = high_boundary / 2.0
        medium_center = (high_boundary + medium_boundary) / 2.0
        low_center = (medium_boundary + 1.0) / 2.0

        sigma = 0.15

        d_high = weighted_score - high_center
        d_medium = weighted_score - medium_center
        d_low = weighted_score - low_center

        raw_high = np.exp(-0.5 * (d_high / sigma) ** 2)
        raw_medium = np.exp(-0.5 * (d_medium / sigma) ** 2)
        raw_low = np.exp(-0.5 * (d_low / sigma) ** 2)

        total = raw_high + raw_medium + raw_low
        if total < 1e-12:
            return RiskProbabilityDistribution(p_high=0.33, p_medium=0.34, p_low=0.33)

        p_high = raw_high / total
        p_medium = raw_medium / total
        p_low = raw_low / total

        return RiskProbabilityDistribution(
            p_high=float(p_high),
            p_medium=float(p_medium),
            p_low=float(p_low),
        )

    def _compute_factor_contributions(
        self,
        scores: Dict[str, float],
        weights: Dict[str, float],
        weighted_score: float,
        mean_score: float,
    ) -> List[FactorContribution]:
        """
        计算各因子贡献度（类似 SHAP 值）。

        基于加权模型：每个因子的贡献 = weight_i * (score_i - mean_score)，
        其中 mean_score 是所有因子评分的均值，作为基准值 (base value)。
        """
        contributions = []
        name_map = {
            'mean_deviation': '均值偏离',
            'volatility': '波动性',
            'trend': '趋势',
            'extreme_values': '极值',
            'lstm_prediction': 'LSTM预测',
        }

        total_abs_contribution = 0.0
        raw_contributions = []

        for name, weight in weights.items():
            raw_score = scores.get(name, 0.5)
            contribution = weight * (raw_score - mean_score)
            raw_contributions.append((name, raw_score, weight, contribution))
            total_abs_contribution += abs(contribution)

        for name, raw_score, weight, contribution in raw_contributions:
            if total_abs_contribution > 1e-12:
                contribution_ratio = abs(contribution) / total_abs_contribution
            else:
                contribution_ratio = 1.0 / len(weights)

            direction = 'risk_up' if contribution < 0 else 'risk_down'

            contributions.append(FactorContribution(
                name=name,
                display_name=name_map.get(name, name),
                raw_score=raw_score,
                weight=weight,
                weighted_score=weight * raw_score,
                contribution_ratio=contribution_ratio,
                direction=direction,
            ))

        contributions.sort(key=lambda c: c.contribution_ratio, reverse=True)
        return contributions

    def assess_risk(
        self,
        data: np.ndarray,
        lstm_probs: Optional[np.ndarray] = None,
        lstm_class: Optional[int] = None,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> RiskAssessment:
        effective_weights = self.get_effective_weights(node_type, node_id)
        effective_thresholds = self.get_effective_thresholds(node_type, node_id)

        deviation_score = self.calculate_deviation_score(data)
        volatility_score = self.calculate_volatility_score(data)
        trend_score = self.calculate_trend_score(data)
        extreme_score = self.calculate_extreme_score(data)
        lstm_score = self.calculate_lstm_score(lstm_probs)

        scores = {
            'mean_deviation': deviation_score,
            'volatility': volatility_score,
            'trend': trend_score,
            'extreme_values': extreme_score,
            'lstm_prediction': lstm_score,
        }

        weighted_score = sum(
            effective_weights.get(k, 0) * v for k, v in scores.items()
        )

        risk_score = round(weighted_score * 9 + 1, 1)
        risk_score = float(np.clip(risk_score, 1, 10))

        if risk_score <= effective_thresholds.get('high', 3):
            level = RiskLevel.HIGH
        elif risk_score <= effective_thresholds.get('medium', 7):
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        factors = self._identify_risk_factors(
            deviation_score, volatility_score, trend_score, extreme_score, lstm_class
        )

        diagnosis = self._generate_diagnosis(level, factors, data)
        recommendations = self._generate_recommendations(level, factors)

        confidence = self._calculate_confidence(
            deviation_score, volatility_score, trend_score, extreme_score, lstm_probs
        )

        prob_dist = self.compute_probability_distribution(weighted_score, effective_thresholds)

        mean_score = float(np.mean(list(scores.values())))
        factor_contributions = self._compute_factor_contributions(
            scores, effective_weights, weighted_score, mean_score
        )

        return RiskAssessment(
            score=risk_score,
            level=level,
            factors=factors,
            diagnosis=diagnosis,
            recommendations=recommendations,
            confidence=confidence,
            probability_distribution=prob_dist,
            factor_contributions=factor_contributions,
        )

    def explain_risk(
        self,
        data: np.ndarray,
        lstm_probs: Optional[np.ndarray] = None,
        lstm_class: Optional[int] = None,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> RiskExplanation:
        effective_weights = self.get_effective_weights(node_type, node_id)
        effective_thresholds = self.get_effective_thresholds(node_type, node_id)

        deviation_score = self.calculate_deviation_score(data)
        volatility_score = self.calculate_volatility_score(data)
        trend_score = self.calculate_trend_score(data)
        extreme_score = self.calculate_extreme_score(data)
        lstm_score = self.calculate_lstm_score(lstm_probs)

        scores = {
            'mean_deviation': deviation_score,
            'volatility': volatility_score,
            'trend': trend_score,
            'extreme_values': extreme_score,
            'lstm_prediction': lstm_score,
        }

        weighted_score = sum(
            effective_weights.get(k, 0) * v for k, v in scores.items()
        )

        risk_score = round(weighted_score * 9 + 1, 1)
        risk_score = float(np.clip(risk_score, 1, 10))

        if risk_score <= effective_thresholds.get('high', 3):
            level = RiskLevel.HIGH
            level_str = "高"
        elif risk_score <= effective_thresholds.get('medium', 7):
            level = RiskLevel.MEDIUM
            level_str = "中"
        else:
            level = RiskLevel.LOW
            level_str = "低"

        prob_dist = self.compute_probability_distribution(weighted_score, effective_thresholds)

        mean_score = float(np.mean(list(scores.values())))
        factor_contributions = self._compute_factor_contributions(
            scores, effective_weights, weighted_score, mean_score
        )

        base_value = mean_score
        total_contribution = weighted_score - mean_score

        top_factors = factor_contributions[:3]
        summary_parts = []
        for fc in top_factors:
            if fc.direction == 'risk_up':
                summary_parts.append(
                    f"{fc.display_name}推高风险(贡献度{fc.contribution_ratio:.1%})"
                )
            else:
                summary_parts.append(
                    f"{fc.display_name}降低风险(贡献度{fc.contribution_ratio:.1%})"
                )
        summary = f"风险评分{risk_score}({level_str}风险)。" + "；".join(summary_parts)

        return RiskExplanation(
            risk_score=risk_score,
            risk_level=level_str,
            probability_distribution=prob_dist,
            factor_contributions=factor_contributions,
            base_value=base_value,
            total_contribution=total_contribution,
            summary=summary,
        )

    def _identify_risk_factors(
        self,
        deviation_score: float,
        volatility_score: float,
        trend_score: float,
        extreme_score: float,
        lstm_class: Optional[int],
    ) -> List[str]:
        factors = []

        if deviation_score < 0.5:
            factors.append("预紧力均值偏离正常范围")

        if volatility_score < 0.5:
            factors.append("预紧力波动过大")

        if trend_score < 0.5:
            factors.append("预紧力呈现异常变化趋势")

        if extreme_score < 0.5:
            factors.append("存在极端预紧力值")

        if lstm_class is not None:
            if lstm_class == 3:
                factors.append("LSTM模型预测存在紧急风险")
            elif lstm_class == 4:
                factors.append("LSTM模型预测已发生故障")

        return factors if factors else ["未发现明显风险因素"]

    def _generate_diagnosis(
        self,
        level: RiskLevel,
        factors: List[str],
        data: np.ndarray,
    ) -> str:
        base_diagnosis = self.diagnosis_templates[level]

        mean_val = np.mean(data)
        std_val = np.std(data)

        details = f"\n当前预紧力均值: {mean_val:.2f}，标准差: {std_val:.2f}。"

        if level != RiskLevel.LOW:
            details += f"\n主要风险因素: {', '.join(factors)}。"

        return base_diagnosis + details

    def _generate_recommendations(
        self,
        level: RiskLevel,
        factors: List[str],
    ) -> List[str]:
        recommendations = []

        if level == RiskLevel.HIGH:
            recommendations.extend([
                "立即安排现场检查",
                "评估是否需要临时停机",
                "准备备用螺栓和工具",
                "通知相关维护人员",
            ])
        elif level == RiskLevel.MEDIUM:
            recommendations.extend([
                "提高监测频率",
                "记录异常数据特征",
                "制定预防性维护计划",
                "关注后续变化趋势",
            ])
        else:
            recommendations.extend([
                "保持常规监测",
                "按计划执行维护",
            ])

        for factor in factors:
            if "波动" in factor:
                recommendations.append("检查环境因素对预紧力的影响")
            if "趋势" in factor:
                recommendations.append("分析趋势变化原因，可能存在渐进性损坏")
            if "极端" in factor:
                recommendations.append("检查是否存在过载或松动情况")

        return list(set(recommendations))

    def _calculate_confidence(
        self,
        deviation_score: float,
        volatility_score: float,
        trend_score: float,
        extreme_score: float,
        lstm_probs: Optional[np.ndarray],
    ) -> float:
        base_confidence = 0.7

        scores = [deviation_score, volatility_score, trend_score, extreme_score]
        score_std = np.std(scores)
        consistency_bonus = max(0, 0.2 - score_std * 0.5)

        lstm_bonus = 0
        if lstm_probs is not None:
            max_prob = np.max(lstm_probs)
            if max_prob > 0.8:
                lstm_bonus = 0.1

        confidence = base_confidence + consistency_bonus + lstm_bonus

        return min(confidence, 0.99)

    def batch_assess(
        self,
        data_list: List[np.ndarray],
        lstm_results: Optional[List[Tuple[int, np.ndarray]]] = None,
    ) -> List[RiskAssessment]:
        results = []

        for i, data in enumerate(data_list):
            lstm_class = None
            lstm_probs = None

            if lstm_results is not None and i < len(lstm_results):
                lstm_class, lstm_probs = lstm_results[i]

            assessment = self.assess_risk(data, lstm_probs, lstm_class)
            results.append(assessment)

        return results
