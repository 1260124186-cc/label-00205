"""
低质量数据过滤机制模块

提供数据质量过滤功能：
1. 在训练前过滤低质量数据
2. 在预测时根据数据质量调整置信度
3. 标记并排除低质量数据点

设计模式: 过滤器模式 (Filter Pattern)
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.services.data_quality.rules_engine import (
    QualityCheckResult,
    RuleViolation,
    RuleType,
    RuleSeverity,
)
from app.services.data_quality.quality_scoring import (
    SensorQualityScore,
    QualityLevel,
)


class FilterStrategy(Enum):
    """过滤策略"""
    EXCLUDE = "exclude"
    MARK = "mark"
    INTERPOLATE = "interpolate"
    DOWNGRADE = "downgrade"


@dataclass
class FilteredDataResult:
    """
    过滤后的数据结果

    Attributes:
        sensor_id: 传感器ID
        original_data: 原始数据
        original_timestamps: 原始时间戳
        filtered_data: 过滤后的数据
        filtered_timestamps: 过滤后的时间戳
        filtered_indices: 被过滤掉的索引
        kept_indices: 保留的索引
        filter_reasons: 各过滤点的原因
        filter_strategy: 使用的过滤策略
        quality_score: 数据质量评分
        confidence_multiplier: 置信度乘数
        valid_for_training: 是否适合用于训练
    """
    sensor_id: str
    original_data: np.ndarray
    original_timestamps: Optional[np.ndarray]
    filtered_data: np.ndarray
    filtered_timestamps: Optional[np.ndarray]
    filtered_indices: List[int]
    kept_indices: List[int]
    filter_reasons: Dict[int, List[str]]
    filter_strategy: FilterStrategy
    quality_score: float
    confidence_multiplier: float
    valid_for_training: bool

    @property
    def filter_ratio(self) -> float:
        """被过滤的数据比例"""
        if len(self.original_data) == 0:
            return 0.0
        return len(self.filtered_indices) / len(self.original_data)

    @property
    def kept_ratio(self) -> float:
        """保留的数据比例"""
        return 1.0 - self.filter_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'original_count': len(self.original_data),
            'filtered_count': len(self.filtered_data),
            'filter_ratio': self.filter_ratio,
            'kept_ratio': self.kept_ratio,
            'filtered_indices': self.filtered_indices,
            'kept_indices': self.kept_indices,
            'filter_reasons': {str(k): v for k, v in self.filter_reasons.items()},
            'filter_strategy': self.filter_strategy.value,
            'quality_score': self.quality_score,
            'confidence_multiplier': self.confidence_multiplier,
            'valid_for_training': self.valid_for_training,
        }


class DataQualityFilter:
    """
    数据质量过滤器

    基于质量检查结果，对数据进行过滤和调整。
    """

    def __init__(
        self,
        min_quality_score: float = 60.0,
        severity_filters: Optional[Dict[RuleSeverity, FilterStrategy]] = None,
        exclude_rules: Optional[List[RuleType]] = None,
        max_filter_ratio: float = 0.5,
    ):
        """
        初始化数据质量过滤器

        Args:
            min_quality_score: 最低质量评分，低于此分数的数据不适合训练
            severity_filters: 各严重级别的过滤策略
            exclude_rules: 需要强制排除的规则类型
            max_filter_ratio: 最大过滤比例，超过此比例则降级处理
        """
        self.min_quality_score = min_quality_score
        self.max_filter_ratio = max_filter_ratio

        self.severity_filters = severity_filters or {
            RuleSeverity.CRITICAL: FilterStrategy.EXCLUDE,
            RuleSeverity.ERROR: FilterStrategy.EXCLUDE,
            RuleSeverity.WARNING: FilterStrategy.MARK,
            RuleSeverity.INFO: FilterStrategy.MARK,
        }

        self.exclude_rules = exclude_rules or []

        logger.info("数据质量过滤器初始化完成")

    def filter_for_training(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray],
        check_result: QualityCheckResult,
        quality_score: Optional[SensorQualityScore] = None,
    ) -> FilteredDataResult:
        """
        为训练任务过滤数据

        Args:
            data: 原始数据
            timestamps: 时间戳
            check_result: 质量检查结果
            quality_score: 质量评分（可选）

        Returns:
            FilteredDataResult: 过滤结果
        """
        quality_score_value = quality_score.overall_score if quality_score else check_result.overall_score
        valid_for_training = quality_score_value >= self.min_quality_score

        # 训练时使用更严格的过滤策略
        training_severity_filters = {
            RuleSeverity.CRITICAL: FilterStrategy.EXCLUDE,
            RuleSeverity.ERROR: FilterStrategy.EXCLUDE,
            RuleSeverity.WARNING: FilterStrategy.EXCLUDE,
            RuleSeverity.INFO: FilterStrategy.MARK,
        }

        return self._filter(
            data=data,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
            severity_filters=training_severity_filters,
            valid_for_training=valid_for_training,
        )

    def filter_for_prediction(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray],
        check_result: QualityCheckResult,
        quality_score: Optional[SensorQualityScore] = None,
    ) -> FilteredDataResult:
        """
        为预测任务过滤数据

        预测时过滤策略相对宽松，主要通过置信度调整来体现数据质量影响。

        Args:
            data: 原始数据
            timestamps: 时间戳
            check_result: 质量检查结果
            quality_score: 质量评分（可选）

        Returns:
            FilteredDataResult: 过滤结果
        """
        quality_score_value = quality_score.overall_score if quality_score else check_result.overall_score
        valid_for_training = quality_score_value >= self.min_quality_score

        return self._filter(
            data=data,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
            severity_filters=self.severity_filters,
            valid_for_training=valid_for_training,
        )

    def _filter(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray],
        check_result: QualityCheckResult,
        quality_score: Optional[SensorQualityScore],
        severity_filters: Dict[RuleSeverity, FilterStrategy],
        valid_for_training: bool,
    ) -> FilteredDataResult:
        """
        内部过滤方法

        Args:
            data: 原始数据
            timestamps: 时间戳
            check_result: 质量检查结果
            quality_score: 质量评分
            severity_filters: 严重级别过滤策略
            valid_for_training: 是否适合训练

        Returns:
            FilteredDataResult: 过滤结果
        """
        if len(data) == 0:
            return FilteredDataResult(
                sensor_id=check_result.sensor_id,
                original_data=data,
                original_timestamps=timestamps,
                filtered_data=np.array([]),
                filtered_timestamps=None,
                filtered_indices=[],
                kept_indices=[],
                filter_reasons={},
                filter_strategy=FilterStrategy.EXCLUDE,
                quality_score=0.0,
                confidence_multiplier=0.0,
                valid_for_training=False,
            )

        # 收集所有需要排除的索引和原因
        exclude_indices = set()
        filter_reasons: Dict[int, List[str]] = {}

        for violation in check_result.violations:
            strategy = severity_filters.get(violation.severity, FilterStrategy.MARK)

            if strategy in [FilterStrategy.EXCLUDE, FilterStrategy.DOWNGRADE]:
                for idx in violation.indices:
                    if idx < len(data):
                        exclude_indices.add(idx)
                        if idx not in filter_reasons:
                            filter_reasons[idx] = []
                        filter_reasons[idx].append(violation.message)

            # 强制排除指定规则的违规
            if violation.rule_type in self.exclude_rules:
                for idx in violation.indices:
                    if idx < len(data):
                        exclude_indices.add(idx)
                        if idx not in filter_reasons:
                            filter_reasons[idx] = []
                        filter_reasons[idx].append(
                            f"[强制排除] {violation.message}"
                        )

        # 检查最大过滤比例
        exclude_list = sorted(list(exclude_indices))
        filter_ratio = len(exclude_list) / len(data)

        if filter_ratio > self.max_filter_ratio:
            logger.warning(
                f"传感器 {check_result.sensor_id} 过滤比例 {filter_ratio:.1%} "
                f"超过上限 {self.max_filter_ratio:.1%}，采用降级策略"
            )
            # 降级：只排除最严重的违规
            exclude_indices = set()
            filter_reasons = {}

            for violation in check_result.violations:
                if violation.severity in [RuleSeverity.CRITICAL, RuleSeverity.ERROR]:
                    for idx in violation.indices:
                        if idx < len(data):
                            exclude_indices.add(idx)
                            if idx not in filter_reasons:
                                filter_reasons[idx] = []
                            filter_reasons[idx].append(
                                f"[降级保留] {violation.message}"
                            )

            exclude_list = sorted(list(exclude_indices))
            filter_strategy = FilterStrategy.DOWNGRADE
        else:
            filter_strategy = FilterStrategy.EXCLUDE

        # 构建保留的索引
        kept_indices = [i for i in range(len(data)) if i not in exclude_indices]

        # 过滤数据
        filtered_data = data[kept_indices]
        filtered_timestamps = timestamps[kept_indices] if timestamps is not None else None

        # 计算置信度乘数
        quality_score_value = quality_score.overall_score if quality_score else check_result.overall_score
        confidence_multiplier = self._calculate_confidence_multiplier(
            quality_score_value,
            filter_ratio,
            check_result.violations,
        )

        result = FilteredDataResult(
            sensor_id=check_result.sensor_id,
            original_data=data.copy(),
            original_timestamps=timestamps.copy() if timestamps is not None else None,
            filtered_data=filtered_data,
            filtered_timestamps=filtered_timestamps,
            filtered_indices=exclude_list,
            kept_indices=kept_indices,
            filter_reasons=filter_reasons,
            filter_strategy=filter_strategy,
            quality_score=quality_score_value,
            confidence_multiplier=confidence_multiplier,
            valid_for_training=valid_for_training and len(filtered_data) >= 10,
        )

        logger.info(
            f"传感器 {check_result.sensor_id} 过滤完成: "
            f"原始 {len(data)} 条, 保留 {len(filtered_data)} 条 "
            f"({result.kept_ratio:.1%}), 置信度乘数 {confidence_multiplier:.3f}"
        )

        return result

    def _calculate_confidence_multiplier(
        self,
        quality_score: float,
        filter_ratio: float,
        violations: List[RuleViolation],
    ) -> float:
        """
        计算置信度乘数

        Args:
            quality_score: 质量评分
            filter_ratio: 过滤比例
            violations: 违规列表

        Returns:
            float: 置信度乘数 (0-1)
        """
        # 基础乘数：质量评分归一化
        base_multiplier = quality_score / 100.0

        # 过滤惩罚：过滤比例越高，乘数越低
        filter_penalty = max(0.0, 1.0 - filter_ratio * 1.5)

        # 严重违规惩罚
        severity_penalty = 1.0
        for violation in violations:
            if violation.severity == RuleSeverity.CRITICAL:
                severity_penalty *= 0.7
            elif violation.severity == RuleSeverity.ERROR:
                severity_penalty *= 0.85
            elif violation.severity == RuleSeverity.WARNING:
                severity_penalty *= 0.95

        # 综合乘数
        multiplier = base_multiplier * filter_penalty * severity_penalty
        multiplier = max(0.3, min(1.0, multiplier))

        return multiplier

    def adjust_prediction_confidence(
        self,
        original_confidence: float,
        quality_score: Optional[SensorQualityScore] = None,
        filter_result: Optional[FilteredDataResult] = None,
    ) -> float:
        """
        调整预测置信度

        根据数据质量调整预测置信度。

        Args:
            original_confidence: 原始置信度
            quality_score: 质量评分（可选）
            filter_result: 过滤结果（可选）

        Returns:
            float: 调整后的置信度
        """
        multiplier = 1.0

        if quality_score is not None:
            multiplier *= quality_score.confidence_adjustment

        if filter_result is not None:
            multiplier *= filter_result.confidence_multiplier

        adjusted_confidence = original_confidence * multiplier
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))

        logger.debug(
            f"置信度调整: {original_confidence:.3f} -> {adjusted_confidence:.3f} "
            f"(乘数 {multiplier:.3f})"
        )

        return adjusted_confidence

    def get_filter_statistics(
        self,
        results: List[FilteredDataResult],
    ) -> Dict[str, Any]:
        """
        获取过滤统计信息

        Args:
            results: 过滤结果列表

        Returns:
            Dict[str, Any]: 统计信息
        """
        if not results:
            return {'total_sensors': 0}

        filter_ratios = [r.filter_ratio for r in results]
        quality_scores = [r.quality_score for r in results]
        confidence_multipliers = [r.confidence_multiplier for r in results]
        training_eligible = sum(1 for r in results if r.valid_for_training)

        return {
            'total_sensors': len(results),
            'average_filter_ratio': float(np.mean(filter_ratios)),
            'max_filter_ratio': float(np.max(filter_ratios)),
            'average_quality_score': float(np.mean(quality_scores)),
            'average_confidence_multiplier': float(np.mean(confidence_multipliers)),
            'training_eligible_count': training_eligible,
            'training_eligible_ratio': training_eligible / len(results),
        }
