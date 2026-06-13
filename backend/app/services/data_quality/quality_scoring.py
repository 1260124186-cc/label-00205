"""
传感器质量评分系统模块

基于数据质量检查结果，为每个传感器计算综合质量评分。
评分维度包括：
1. 完整性 (completeness): 数据缺失程度
2. 一致性 (consistency): 数据重复和时间倒挂程度
3. 有效性 (validity): 数据越界程度
4. 稳定性 (stability): 数据漂移程度

设计模式: 加权评分模型 (Weighted Scoring Model)
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from loguru import logger

from app.services.data_quality.rules_engine import (
    QualityCheckResult,
    RuleType,
    RuleSeverity,
)


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float) -> 'QualityLevel':
        if score >= 90:
            return cls.EXCELLENT
        elif score >= 75:
            return cls.GOOD
        elif score >= 60:
            return cls.FAIR
        elif score >= 40:
            return cls.POOR
        else:
            return cls.CRITICAL


class QualityDimension(Enum):
    """质量维度"""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    VALIDITY = "validity"
    STABILITY = "stability"


@dataclass
class QualityDimensionScore:
    """
    维度质量评分

    Attributes:
        dimension: 质量维度
        score: 维度评分 (0-100)
        level: 质量等级
        weight: 维度权重
        contributing_rules: 影响此维度的规则评分
        description: 维度描述
    """
    dimension: QualityDimension
    score: float
    level: QualityLevel
    weight: float
    contributing_rules: Dict[RuleType, float] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'dimension': self.dimension.value,
            'score': self.score,
            'level': self.level.value,
            'weight': self.weight,
            'contributing_rules': {k.value: v for k, v in self.contributing_rules.items()},
            'description': self.description,
        }


@dataclass
class SensorQualityScore:
    """
    传感器质量评分

    Attributes:
        sensor_id: 传感器ID
        overall_score: 综合评分 (0-100)
        overall_level: 综合质量等级
        dimensions: 各维度评分
        rule_violations_count: 各严重级别违规数量
        data_quality_score: 原始数据质量检查评分
        timeliness_score: 时效性评分
        historical_trend: 历史趋势评分
        last_check_time: 最后检查时间
        valid_for_training: 是否适合用于训练
        confidence_adjustment: 预测置信度调整系数 (0-1)
        check_time: 评分时间
    """
    sensor_id: str
    overall_score: float
    overall_level: QualityLevel
    dimensions: Dict[QualityDimension, QualityDimensionScore]
    rule_violations_count: Dict[RuleSeverity, int]
    data_quality_score: float
    timeliness_score: float
    historical_trend: float
    last_check_time: Optional[datetime] = None
    valid_for_training: bool = True
    confidence_adjustment: float = 1.0
    check_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'overall_score': self.overall_score,
            'overall_level': self.overall_level.value,
            'dimensions': {k.value: v.to_dict() for k, v in self.dimensions.items()},
            'rule_violations_count': {k.value: v for k, v in self.rule_violations_count.items()},
            'data_quality_score': self.data_quality_score,
            'timeliness_score': self.timeliness_score,
            'historical_trend': self.historical_trend,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'valid_for_training': self.valid_for_training,
            'confidence_adjustment': self.confidence_adjustment,
            'check_time': self.check_time.isoformat(),
        }


class QualityScorer:
    """
    质量评分器

    基于数据质量检查结果，计算传感器的综合质量评分。
    """

    def __init__(
        self,
        dimension_weights: Optional[Dict[QualityDimension, float]] = None,
        training_threshold: float = 60.0,
        min_confidence_adjustment: float = 0.3,
    ):
        """
        初始化质量评分器

        Args:
            dimension_weights: 各维度权重，None则使用默认权重
            training_threshold: 可用于训练的最低质量评分
            min_confidence_adjustment: 最小置信度调整系数
        """
        self.dimension_weights = dimension_weights or self._default_weights()
        self.training_threshold = training_threshold
        self.min_confidence_adjustment = min_confidence_adjustment

        self.rule_to_dimension = {
            RuleType.MISSING_RATE: QualityDimension.COMPLETENESS,
            RuleType.DUPLICATE: QualityDimension.CONSISTENCY,
            RuleType.TIME_INVERSION: QualityDimension.CONSISTENCY,
            RuleType.OUT_OF_BOUNDS: QualityDimension.VALIDITY,
            RuleType.DRIFT: QualityDimension.STABILITY,
        }

        logger.info("质量评分器初始化完成")

    def _default_weights(self) -> Dict[QualityDimension, float]:
        """返回默认维度权重"""
        return {
            QualityDimension.COMPLETENESS: 0.30,
            QualityDimension.CONSISTENCY: 0.25,
            QualityDimension.VALIDITY: 0.25,
            QualityDimension.STABILITY: 0.20,
        }

    def score(
        self,
        check_result: QualityCheckResult,
        historical_scores: Optional[List[SensorQualityScore]] = None,
        data_age_minutes: Optional[float] = None,
    ) -> SensorQualityScore:
        """
        计算传感器质量评分

        Args:
            check_result: 数据质量检查结果
            historical_scores: 历史评分列表，用于趋势分析
            data_age_minutes: 数据新鲜度（分钟），用于时效性评分

        Returns:
            SensorQualityScore: 传感器质量评分
        """
        # 1. 计算各维度评分
        dimensions = self._calculate_dimension_scores(check_result)

        # 2. 计算综合评分（加权平均）
        overall_score = self._calculate_overall_score(dimensions)
        overall_level = QualityLevel.from_score(overall_score)

        # 3. 统计违规数量
        violations_count = self._count_violations(check_result)

        # 4. 计算数据质量分（直接使用检查结果的综合分）
        data_quality_score = check_result.overall_score

        # 5. 计算时效性评分
        timeliness_score = self._calculate_timeliness_score(data_age_minutes)

        # 6. 计算历史趋势评分
        historical_trend = self._calculate_historical_trend(historical_scores, overall_score)

        # 7. 确定是否适合训练
        valid_for_training = overall_score >= self.training_threshold

        # 8. 计算置信度调整系数
        confidence_adjustment = self._calculate_confidence_adjustment(
            overall_score,
            violations_count,
        )

        return SensorQualityScore(
            sensor_id=check_result.sensor_id,
            overall_score=overall_score,
            overall_level=overall_level,
            dimensions=dimensions,
            rule_violations_count=violations_count,
            data_quality_score=data_quality_score,
            timeliness_score=timeliness_score,
            historical_trend=historical_trend,
            last_check_time=check_result.check_time,
            valid_for_training=valid_for_training,
            confidence_adjustment=confidence_adjustment,
        )

    def _calculate_dimension_scores(
        self,
        check_result: QualityCheckResult,
    ) -> Dict[QualityDimension, QualityDimensionScore]:
        """
        计算各维度评分

        Args:
            check_result: 质量检查结果

        Returns:
            Dict[QualityDimension, QualityDimensionScore]: 各维度评分
        """
        dimension_scores = {}

        for dimension in QualityDimension:
            weight = self.dimension_weights.get(dimension, 0.0)

            # 找出影响此维度的规则
            contributing_rules = {}
            for rule_type, rule_score in check_result.rule_scores.items():
                if self.rule_to_dimension.get(rule_type) == dimension:
                    contributing_rules[rule_type] = rule_score

            # 计算维度评分（规则评分的加权平均）
            if contributing_rules:
                dimension_score = float(np.mean(list(contributing_rules.values())))
            else:
                dimension_score = 100.0  # 没有相关规则，默认为满分

            level = QualityLevel.from_score(dimension_score)
            description = self._get_dimension_description(dimension, dimension_score)

            dimension_scores[dimension] = QualityDimensionScore(
                dimension=dimension,
                score=dimension_score,
                level=level,
                weight=weight,
                contributing_rules=contributing_rules,
                description=description,
            )

        return dimension_scores

    def _calculate_overall_score(
        self,
        dimensions: Dict[QualityDimension, QualityDimensionScore],
    ) -> float:
        """
        计算综合评分

        Args:
            dimensions: 各维度评分

        Returns:
            float: 综合评分 (0-100)
        """
        total_weight = 0.0
        weighted_score = 0.0

        for dim_score in dimensions.values():
            weighted_score += dim_score.score * dim_score.weight
            total_weight += dim_score.weight

        if total_weight == 0:
            return 0.0

        return weighted_score / total_weight

    def _count_violations(
        self,
        check_result: QualityCheckResult,
    ) -> Dict[RuleSeverity, int]:
        """
        统计各严重级别违规数量

        Args:
            check_result: 质量检查结果

        Returns:
            Dict[RuleSeverity, int]: 各严重级别违规数量
        """
        count = {
            RuleSeverity.INFO: 0,
            RuleSeverity.WARNING: 0,
            RuleSeverity.ERROR: 0,
            RuleSeverity.CRITICAL: 0,
        }

        for violation in check_result.violations:
            count[violation.severity] += 1

        return count

    def _calculate_timeliness_score(
        self,
        data_age_minutes: Optional[float],
    ) -> float:
        """
        计算时效性评分

        Args:
            data_age_minutes: 数据新鲜度（分钟）

        Returns:
            float: 时效性评分 (0-100)
        """
        if data_age_minutes is None:
            return 100.0

        if data_age_minutes < 0:
            return 100.0

        # 1小时内满分，24小时后60分，72小时后30分
        if data_age_minutes <= 60:
            return 100.0
        elif data_age_minutes <= 1440:
            return 100.0 - (data_age_minutes - 60) / (1440 - 60) * 40.0
        elif data_age_minutes <= 4320:
            return 60.0 - (data_age_minutes - 1440) / (4320 - 1440) * 30.0
        else:
            return max(0.0, 30.0 - (data_age_minutes - 4320) / 4320 * 30.0)

    def _calculate_historical_trend(
        self,
        historical_scores: Optional[List[SensorQualityScore]],
        current_score: float,
    ) -> float:
        """
        计算历史趋势评分

        Args:
            historical_scores: 历史评分列表
            current_score: 当前评分

        Returns:
            float: 趋势评分 (0-100)
            - >50: 质量上升趋势
            - 50: 平稳
            - <50: 质量下降趋势
        """
        if not historical_scores or len(historical_scores) < 2:
            return 50.0

        # 获取最近的历史评分（排除当前）
        recent_scores = [s.overall_score for s in historical_scores[-5:]]

        if len(recent_scores) < 2:
            return 50.0

        # 计算趋势斜率
        x = np.arange(len(recent_scores))
        y = np.array(recent_scores)
        slope = float(np.polyfit(x, y, 1)[0])

        # 斜率转换为评分
        # 斜率 > 5: 明显上升 (100分)
        # 斜率 < -5: 明显下降 (0分)
        # 中间线性插值
        trend_score = 50.0 + slope * 5.0
        trend_score = max(0.0, min(100.0, trend_score))

        return trend_score

    def _calculate_confidence_adjustment(
        self,
        overall_score: float,
        violations_count: Dict[RuleSeverity, int],
    ) -> float:
        """
        计算预测置信度调整系数

        Args:
            overall_score: 综合质量评分
            violations_count: 违规数量统计

        Returns:
            float: 置信度调整系数 (min_confidence_adjustment - 1.0)
        """
        # 基础调整系数与质量评分成正比
        base_adjustment = overall_score / 100.0

        # 违规惩罚系数
        penalty = 0.0
        penalty += violations_count.get(RuleSeverity.CRITICAL, 0) * 0.2
        penalty += violations_count.get(RuleSeverity.ERROR, 0) * 0.1
        penalty += violations_count.get(RuleSeverity.WARNING, 0) * 0.05

        adjustment = base_adjustment - penalty
        adjustment = max(self.min_confidence_adjustment, min(1.0, adjustment))

        return adjustment

    def _get_dimension_description(
        self,
        dimension: QualityDimension,
        score: float,
    ) -> str:
        """
        获取维度描述

        Args:
            dimension: 质量维度
            score: 维度评分

        Returns:
            str: 维度描述
        """
        descriptions = {
            QualityDimension.COMPLETENESS: {
                'excellent': '数据完整性优秀，缺失率极低',
                'good': '数据完整性良好，缺失率在可接受范围内',
                'fair': '数据完整性一般，存在一定缺失',
                'poor': '数据完整性较差，缺失率较高',
                'critical': '数据完整性极差，缺失严重',
            },
            QualityDimension.CONSISTENCY: {
                'excellent': '数据一致性优秀，无重复和时间错乱',
                'good': '数据一致性良好，重复和时间错乱极少',
                'fair': '数据一致性一般，存在少量重复或时间错乱',
                'poor': '数据一致性较差，存在较多重复或时间错乱',
                'critical': '数据一致性极差，重复和时间错乱严重',
            },
            QualityDimension.VALIDITY: {
                'excellent': '数据有效性优秀，所有值都在合理范围内',
                'good': '数据有效性良好，越界值极少',
                'fair': '数据有效性一般，存在少量越界值',
                'poor': '数据有效性较差，存在较多越界值',
                'critical': '数据有效性极差，越界值严重',
            },
            QualityDimension.STABILITY: {
                'excellent': '数据稳定性优秀，无明显漂移',
                'good': '数据稳定性良好，漂移在可接受范围内',
                'fair': '数据稳定性一般，存在一定漂移',
                'poor': '数据稳定性较差，漂移较明显',
                'critical': '数据稳定性极差，漂移严重',
            },
        }

        level = QualityLevel.from_score(score)
        return descriptions.get(dimension, {}).get(level.value, '')

    def get_quality_summary(
        self,
        scores: List[SensorQualityScore],
    ) -> Dict[str, Any]:
        """
        获取多个传感器的质量汇总统计

        Args:
            scores: 传感器质量评分列表

        Returns:
            Dict[str, Any]: 质量汇总统计
        """
        if not scores:
            return {'total_sensors': 0}

        overall_scores = [s.overall_score for s in scores]
        levels = [s.overall_level.value for s in scores]

        level_counts = {
            level: levels.count(level)
            for level in ['excellent', 'good', 'fair', 'poor', 'critical']
        }

        training_eligible = sum(1 for s in scores if s.valid_for_training)

        return {
            'total_sensors': len(scores),
            'average_score': float(np.mean(overall_scores)),
            'min_score': float(np.min(overall_scores)),
            'max_score': float(np.max(overall_scores)),
            'std_score': float(np.std(overall_scores)),
            'level_distribution': level_counts,
            'training_eligible_count': training_eligible,
            'training_eligible_ratio': training_eligible / len(scores),
        }
