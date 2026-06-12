"""
贝叶斯风险评估模型

基于贝叶斯网络的风险评分和等级评估模型。

功能:
1. 风险评分计算 (1-10分)
2. 风险等级评估 (低/中/高)
3. 诊断建议生成
4. 与LSTM模型输出融合

风险等级:
    - 高风险: 1-3分
    - 中风险: 4-7分
    - 低风险: 8-10分

使用示例:
    from app.models.risk_model import BayesianRiskModel
    
    model = BayesianRiskModel()
    score, level, diagnosis = model.assess_risk(preload_data, lstm_probs)
"""

import numpy as np
from typing import Tuple, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.utils.config import config


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


@dataclass
class RiskAssessment:
    """
    风险评估结果数据类
    
    Attributes:
        score: 风险评分 (1-10)
        level: 风险等级
        factors: 风险因素列表
        diagnosis: 诊断结论
        recommendations: 改善建议列表
        confidence: 评估置信度
    """
    score: float
    level: RiskLevel
    factors: List[str]
    diagnosis: str
    recommendations: List[str]
    confidence: float


class BayesianRiskModel:
    """
    贝叶斯风险评估模型
    
    结合历史数据和LSTM模型输出，使用贝叶斯推理计算风险评分。
    
    Attributes:
        thresholds: 预紧力阈值配置
        risk_thresholds: 风险等级阈值
        prior_weights: 先验权重
    """
    
    def __init__(self):
        """
        初始化风险评估模型
        """
        self.thresholds = config.get('risk_assessment.preload_thresholds', {
            'min_normal': 400,
            'max_normal': 800,
            'warning_deviation': 0.1,
            'critical_deviation': 0.2
        })
        
        self.risk_thresholds = {
            'high': config.get('risk_assessment.high_risk_threshold', 3),
            'medium': config.get('risk_assessment.medium_risk_threshold', 7)
        }
        
        # 先验权重 (可根据历史数据调整)
        self.prior_weights = {
            'mean_deviation': 0.25,      # 均值偏离
            'volatility': 0.20,          # 波动性
            'trend': 0.20,               # 趋势
            'extreme_values': 0.15,      # 极值
            'lstm_prediction': 0.20      # LSTM预测
        }
        
        # 诊断模板
        self.diagnosis_templates = {
            RiskLevel.LOW: "预紧力数据稳定，处于正常工作范围内。",
            RiskLevel.MEDIUM: "预紧力出现一定波动，需要密切关注变化趋势。",
            RiskLevel.HIGH: "预紧力异常明显，存在潜在故障风险，需要立即采取措施。"
        }
        
        logger.info("贝叶斯风险评估模型初始化完成")
    
    def calculate_deviation_score(self, data: np.ndarray) -> float:
        """
        计算预紧力偏离评分
        
        Args:
            data: 预紧力数据
            
        Returns:
            float: 偏离评分 (0-1, 越小越偏离)
        """
        mean_val = np.mean(data)
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']
        
        # 计算偏离程度
        if min_normal <= mean_val <= max_normal:
            # 在正常范围内
            center = (min_normal + max_normal) / 2
            range_half = (max_normal - min_normal) / 2
            deviation = abs(mean_val - center) / range_half
            score = 1.0 - deviation * 0.3  # 在范围内也有轻微惩罚
        elif mean_val < min_normal:
            # 低于最小值
            deviation = (min_normal - mean_val) / min_normal
            score = max(0, 1.0 - deviation * 2)
        else:
            # 高于最大值
            deviation = (mean_val - max_normal) / max_normal
            score = max(0, 1.0 - deviation * 2)
        
        return np.clip(score, 0, 1)
    
    def calculate_volatility_score(self, data: np.ndarray) -> float:
        """
        计算波动性评分
        
        Args:
            data: 预紧力数据
            
        Returns:
            float: 波动性评分 (0-1, 越大越稳定)
        """
        if len(data) < 2:
            return 1.0
        
        mean_val = np.mean(data)
        std_val = np.std(data)
        
        # 计算变异系数
        cv = std_val / (mean_val + 1e-6)
        
        # 正常变异系数应该较小
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
        """
        计算趋势评分
        
        Args:
            data: 预紧力数据
            
        Returns:
            float: 趋势评分 (0-1, 越大越稳定)
        """
        if len(data) < 3:
            return 1.0
        
        # 线性拟合
        x = np.arange(len(data))
        coeffs = np.polyfit(x, data, 1)
        slope = coeffs[0]
        
        # 计算每单位时间的变化率
        mean_val = np.mean(data)
        change_rate = abs(slope) / (mean_val + 1e-6)
        
        # 正常情况下趋势应该平稳
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
        """
        计算极值评分
        
        Args:
            data: 预紧力数据
            
        Returns:
            float: 极值评分 (0-1, 越大越安全)
        """
        min_val = np.min(data)
        max_val = np.max(data)
        
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']
        critical_dev = self.thresholds['critical_deviation']
        
        # 临界阈值
        critical_min = min_normal * (1 - critical_dev)
        critical_max = max_normal * (1 + critical_dev)
        
        score = 1.0
        
        # 检查是否有极端低值
        if min_val < critical_min:
            score -= 0.5
        elif min_val < min_normal:
            score -= 0.2
        
        # 检查是否有极端高值
        if max_val > critical_max:
            score -= 0.5
        elif max_val > max_normal:
            score -= 0.2
        
        # 检查是否有骤降（可能断裂）
        if len(data) > 1:
            changes = np.diff(data)
            if np.any(changes < -np.mean(data) * 0.5):
                score -= 0.3
        
        return max(0, score)
    
    def calculate_lstm_score(self, lstm_probs: Optional[np.ndarray]) -> float:
        """
        基于LSTM预测概率计算分数
        
        Args:
            lstm_probs: LSTM输出的概率分布 [正常, 关注, 检查, 紧急, 故障]
            
        Returns:
            float: LSTM评分 (0-1)
        """
        if lstm_probs is None:
            return 0.5  # 无LSTM结果时返回中性分数
        
        # 加权计算，正常概率权重最高
        weights = np.array([1.0, 0.7, 0.4, 0.2, 0.0])
        score = np.sum(lstm_probs * weights)
        
        return np.clip(score, 0, 1)
    
    def assess_risk(
        self,
        data: np.ndarray,
        lstm_probs: Optional[np.ndarray] = None,
        lstm_class: Optional[int] = None
    ) -> RiskAssessment:
        """
        评估风险
        
        Args:
            data: 预紧力时间序列数据
            lstm_probs: LSTM输出的概率分布
            lstm_class: LSTM预测的类别
            
        Returns:
            RiskAssessment: 风险评估结果
        """
        # 计算各项评分
        deviation_score = self.calculate_deviation_score(data)
        volatility_score = self.calculate_volatility_score(data)
        trend_score = self.calculate_trend_score(data)
        extreme_score = self.calculate_extreme_score(data)
        lstm_score = self.calculate_lstm_score(lstm_probs)
        
        # 加权融合
        weighted_score = (
            self.prior_weights['mean_deviation'] * deviation_score +
            self.prior_weights['volatility'] * volatility_score +
            self.prior_weights['trend'] * trend_score +
            self.prior_weights['extreme_values'] * extreme_score +
            self.prior_weights['lstm_prediction'] * lstm_score
        )
        
        # 转换为1-10分
        risk_score = round(weighted_score * 9 + 1, 1)
        risk_score = np.clip(risk_score, 1, 10)
        
        # 确定风险等级
        if risk_score <= self.risk_thresholds['high']:
            level = RiskLevel.HIGH
        elif risk_score <= self.risk_thresholds['medium']:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        
        # 识别风险因素
        factors = self._identify_risk_factors(
            deviation_score, volatility_score, trend_score, extreme_score, lstm_class
        )
        
        # 生成诊断和建议
        diagnosis = self._generate_diagnosis(level, factors, data)
        recommendations = self._generate_recommendations(level, factors)
        
        # 计算置信度
        confidence = self._calculate_confidence(
            deviation_score, volatility_score, trend_score, extreme_score, lstm_probs
        )
        
        return RiskAssessment(
            score=risk_score,
            level=level,
            factors=factors,
            diagnosis=diagnosis,
            recommendations=recommendations,
            confidence=confidence
        )
    
    def _identify_risk_factors(
        self,
        deviation_score: float,
        volatility_score: float,
        trend_score: float,
        extreme_score: float,
        lstm_class: Optional[int]
    ) -> List[str]:
        """
        识别主要风险因素
        """
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
        data: np.ndarray
    ) -> str:
        """
        生成诊断结论
        """
        base_diagnosis = self.diagnosis_templates[level]
        
        # 添加具体数据描述
        mean_val = np.mean(data)
        std_val = np.std(data)
        
        details = f"\n当前预紧力均值: {mean_val:.2f}，标准差: {std_val:.2f}。"
        
        if level != RiskLevel.LOW:
            details += f"\n主要风险因素: {', '.join(factors)}。"
        
        return base_diagnosis + details
    
    def _generate_recommendations(
        self,
        level: RiskLevel,
        factors: List[str]
    ) -> List[str]:
        """
        生成改善建议
        """
        recommendations = []
        
        if level == RiskLevel.HIGH:
            recommendations.extend([
                "立即安排现场检查",
                "评估是否需要临时停机",
                "准备备用螺栓和工具",
                "通知相关维护人员"
            ])
        elif level == RiskLevel.MEDIUM:
            recommendations.extend([
                "提高监测频率",
                "记录异常数据特征",
                "制定预防性维护计划",
                "关注后续变化趋势"
            ])
        else:
            recommendations.extend([
                "保持常规监测",
                "按计划执行维护"
            ])
        
        # 根据具体因素添加建议
        for factor in factors:
            if "波动" in factor:
                recommendations.append("检查环境因素对预紧力的影响")
            if "趋势" in factor:
                recommendations.append("分析趋势变化原因，可能存在渐进性损坏")
            if "极端" in factor:
                recommendations.append("检查是否存在过载或松动情况")
        
        return list(set(recommendations))  # 去重
    
    def _calculate_confidence(
        self,
        deviation_score: float,
        volatility_score: float,
        trend_score: float,
        extreme_score: float,
        lstm_probs: Optional[np.ndarray]
    ) -> float:
        """
        计算评估置信度
        """
        # 基础置信度
        base_confidence = 0.7
        
        # 数据一致性加成
        scores = [deviation_score, volatility_score, trend_score, extreme_score]
        score_std = np.std(scores)
        consistency_bonus = max(0, 0.2 - score_std * 0.5)
        
        # LSTM确定性加成
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
        lstm_results: Optional[List[Tuple[int, np.ndarray]]] = None
    ) -> List[RiskAssessment]:
        """
        批量评估风险
        
        Args:
            data_list: 预紧力数据列表
            lstm_results: LSTM结果列表 [(class, probs), ...]
            
        Returns:
            List[RiskAssessment]: 评估结果列表
        """
        results = []
        
        for i, data in enumerate(data_list):
            lstm_class = None
            lstm_probs = None
            
            if lstm_results is not None and i < len(lstm_results):
                lstm_class, lstm_probs = lstm_results[i]
            
            assessment = self.assess_risk(data, lstm_probs, lstm_class)
            results.append(assessment)
        
        return results
