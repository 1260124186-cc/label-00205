"""
数据质量规则引擎模块

提供五种核心数据质量检测规则：
1. 缺失率检测 (MissingRateRule)
2. 重复数据检测 (DuplicateRule)
3. 时间倒挂检测 (TimeInversionRule)
4. 越界检测 (OutOfBoundsRule)
5. 漂移检测 (DriftDetectionRule)

设计模式: 策略模式 (Strategy Pattern)
每个规则都是独立的策略类，实现统一的接口。
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger


class RuleType(Enum):
    """规则类型枚举"""
    MISSING_RATE = "missing_rate"
    DUPLICATE = "duplicate"
    TIME_INVERSION = "time_inversion"
    OUT_OF_BOUNDS = "out_of_bounds"
    DRIFT = "drift"


class RuleSeverity(Enum):
    """规则严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RuleViolation:
    """
    规则违反记录

    Attributes:
        rule_type: 规则类型
        severity: 严重程度
        message: 描述信息
        score: 违反程度评分 (0-100，越高越严重)
        indices: 违反规则的数据点索引
        details: 详细信息
    """
    rule_type: RuleType
    severity: RuleSeverity
    message: str
    score: float
    indices: List[int] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_type': self.rule_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'score': self.score,
            'indices': self.indices,
            'details': self.details,
        }


@dataclass
class QualityCheckResult:
    """
    质量检查结果

    Attributes:
        sensor_id: 传感器ID
        total_points: 总数据点数
        valid_points: 有效数据点数
        violations: 规则违反列表
        rule_scores: 各规则评分 (0-100，越高质量越好)
        overall_score: 综合质量评分 (0-100)
        check_time: 检查时间
    """
    sensor_id: str
    total_points: int
    valid_points: int
    violations: List[RuleViolation]
    rule_scores: Dict[RuleType, float]
    overall_score: float
    check_time: datetime = field(default_factory=datetime.now)

    @property
    def has_errors(self) -> bool:
        return any(v.severity in [RuleSeverity.ERROR, RuleSeverity.CRITICAL] 
                   for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.severity == RuleSeverity.WARNING for v in self.violations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'total_points': self.total_points,
            'valid_points': self.valid_points,
            'violations': [v.to_dict() for v in self.violations],
            'rule_scores': {k.value: v for k, v in self.rule_scores.items()},
            'overall_score': self.overall_score,
            'check_time': self.check_time.isoformat(),
            'has_errors': self.has_errors,
            'has_warnings': self.has_warnings,
        }


class DataQualityRule(ABC):
    """
    数据质量规则抽象基类

    所有具体规则都必须实现 evaluate 方法。
    """

    rule_type: RuleType
    name: str
    description: str

    def __init__(self, threshold: float = None, **kwargs):
        """
        初始化规则

        Args:
            threshold: 规则阈值，None则使用默认值
        """
        self.threshold = threshold or self._default_threshold()
        self.config = kwargs

    @abstractmethod
    def _default_threshold(self) -> float:
        """返回默认阈值"""
        pass

    @abstractmethod
    def evaluate(
        self,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, Optional[RuleViolation]]:
        """
        评估数据质量

        Args:
            values: 数据值数组
            timestamps: 时间戳数组
            sensor_id: 传感器ID

        Returns:
            Tuple[float, Optional[RuleViolation]]:
                - 质量评分 (0-100，越高越好)
                - 规则违反记录（如果有），否则None
        """
        pass

    def _determine_severity(self, violation_score: float) -> RuleSeverity:
        """
        根据违反程度确定严重级别

        Args:
            violation_score: 违反程度 (0-100，越高越严重)

        Returns:
            RuleSeverity: 严重级别
        """
        if violation_score >= 80:
            return RuleSeverity.CRITICAL
        elif violation_score >= 50:
            return RuleSeverity.ERROR
        elif violation_score >= 20:
            return RuleSeverity.WARNING
        else:
            return RuleSeverity.INFO


class MissingRateRule(DataQualityRule):
    """
    缺失率检测规则

    检测数据中的缺失值（NaN/None）比例。
    """

    rule_type = RuleType.MISSING_RATE
    name = "缺失率检测"
    description = "检测数据中的缺失值比例"

    def _default_threshold(self) -> float:
        return 0.05  # 默认5%的缺失率阈值

    def evaluate(
        self,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, Optional[RuleViolation]]:
        if len(values) == 0:
            return 0.0, RuleViolation(
                rule_type=self.rule_type,
                severity=RuleSeverity.CRITICAL,
                message="数据为空",
                score=100.0,
                indices=[],
                details={'missing_count': 0, 'total_count': 0, 'missing_rate': 1.0}
            )

        # 检测缺失值
        nan_mask = np.isnan(values) if values.dtype.kind in 'fc' else pd.isna(values)
        missing_count = int(np.sum(nan_mask))
        missing_rate = missing_count / len(values)
        missing_indices = np.where(nan_mask)[0].tolist()

        # 计算质量评分（缺失率越高，评分越低）
        if missing_rate <= self.threshold:
            quality_score = 100.0 - (missing_rate / self.threshold) * 30.0
            violation = None
        else:
            quality_score = max(0.0, 100.0 - (missing_rate - self.threshold) / (1.0 - self.threshold) * 100.0)
            violation_score = min(100.0, (missing_rate - self.threshold) / (1.0 - self.threshold) * 100.0)
            severity = self._determine_severity(violation_score)

            violation = RuleViolation(
                rule_type=self.rule_type,
                severity=severity,
                message=f"缺失率 {missing_rate:.1%} 超过阈值 {self.threshold:.1%}",
                score=violation_score,
                indices=missing_indices,
                details={
                    'missing_count': missing_count,
                    'total_count': len(values),
                    'missing_rate': missing_rate,
                    'threshold': self.threshold,
                }
            )

        return quality_score, violation


class DuplicateRule(DataQualityRule):
    """
    重复数据检测规则

    检测数据中的重复值（相同时间戳或相同数值）。
    """

    rule_type = RuleType.DUPLICATE
    name = "重复数据检测"
    description = "检测数据中的重复时间戳或重复数值"

    def _default_threshold(self) -> float:
        return 0.02  # 默认2%的重复率阈值

    def evaluate(
        self,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, Optional[RuleViolation]]:
        if len(values) == 0:
            return 0.0, None

        duplicate_indices = []
        details = {}

        # 检测时间戳重复
        if timestamps is not None and len(timestamps) > 0:
            timestamp_series = pd.Series(timestamps)
            ts_duplicates = timestamp_series.duplicated(keep=False)
            ts_duplicate_count = int(ts_duplicates.sum())
            ts_duplicate_indices = np.where(ts_duplicates)[0].tolist()
            duplicate_indices.extend(ts_duplicate_indices)
            details['timestamp_duplicates'] = ts_duplicate_count
            details['timestamp_duplicate_indices'] = ts_duplicate_indices

        # 检测数值重复（连续相同值）
        value_diffs = np.diff(values)
        value_duplicates = np.concatenate(([False], np.abs(value_diffs) < 1e-9))
        val_duplicate_count = int(np.sum(value_duplicates))
        val_duplicate_indices = np.where(value_duplicates)[0].tolist()
        duplicate_indices.extend(val_duplicate_indices)
        details['value_duplicates'] = val_duplicate_count
        details['value_duplicate_indices'] = val_duplicate_indices

        # 去重后的索引
        unique_indices = list(set(duplicate_indices))
        duplicate_rate = len(unique_indices) / len(values)

        if duplicate_rate <= self.threshold:
            quality_score = 100.0 - (duplicate_rate / self.threshold) * 30.0
            violation = None
        else:
            quality_score = max(0.0, 100.0 - (duplicate_rate - self.threshold) / (1.0 - self.threshold) * 100.0)
            violation_score = min(100.0, (duplicate_rate - self.threshold) / (1.0 - self.threshold) * 100.0)
            severity = self._determine_severity(violation_score)

            violation = RuleViolation(
                rule_type=self.rule_type,
                severity=severity,
                message=f"重复数据率 {duplicate_rate:.1%} 超过阈值 {self.threshold:.1%}",
                score=violation_score,
                indices=sorted(unique_indices),
                details={
                    **details,
                    'total_duplicates': len(unique_indices),
                    'total_count': len(values),
                    'duplicate_rate': duplicate_rate,
                    'threshold': self.threshold,
                }
            )

        return quality_score, violation


class TimeInversionRule(DataQualityRule):
    """
    时间倒挂检测规则

    检测时间戳是否按升序排列，是否存在时间倒流。
    """

    rule_type = RuleType.TIME_INVERSION
    name = "时间倒挂检测"
    description = "检测时间戳是否按升序排列"

    def _default_threshold(self) -> float:
        return 0.01  # 默认1%的时间倒挂率阈值

    def evaluate(
        self,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, Optional[RuleViolation]]:
        if timestamps is None or len(timestamps) < 2:
            return 100.0, None

        # 转换为数值时间戳进行比较
        try:
            ts_numeric = pd.to_datetime(timestamps).astype(np.int64)
        except Exception:
            ts_numeric = np.array(timestamps, dtype=np.float64)

        # 检测时间倒挂（后一个时间小于前一个）
        time_diffs = np.diff(ts_numeric)
        inversion_mask = time_diffs < 0
        inversion_count = int(np.sum(inversion_mask))

        if inversion_count == 0:
            return 100.0, None

        # 获取倒挂点索引（后一个点的索引）
        inversion_indices = np.where(inversion_mask)[0] + 1
        inversion_indices = inversion_indices.tolist()
        inversion_rate = inversion_count / (len(timestamps) - 1)

        # 计算时间差总和（倒挂的严重程度）
        if inversion_count > 0:
            avg_inversion_amount = float(np.mean(np.abs(time_diffs[inversion_mask])))
        else:
            avg_inversion_amount = 0.0

        quality_score = max(0.0, 100.0 - inversion_rate / self.threshold * 100.0)
        violation_score = min(100.0, inversion_rate / self.threshold * 100.0)
        severity = self._determine_severity(violation_score)

        violation = RuleViolation(
            rule_type=self.rule_type,
            severity=severity,
            message=f"检测到 {inversion_count} 处时间倒挂，占比 {inversion_rate:.1%}",
            score=violation_score,
            indices=inversion_indices,
            details={
                'inversion_count': inversion_count,
                'total_intervals': len(timestamps) - 1,
                'inversion_rate': inversion_rate,
                'avg_inversion_amount_ns': avg_inversion_amount,
                'threshold': self.threshold,
            }
        )

        return quality_score, violation


class OutOfBoundsRule(DataQualityRule):
    """
    越界检测规则

    检测数值是否在合理范围内。
    """

    rule_type = RuleType.OUT_OF_BOUNDS
    name = "越界检测"
    description = "检测数值是否在合理范围内"

    def __init__(
        self,
        threshold: float = None,
        min_value: float = None,
        max_value: float = None,
        **kwargs,
    ):
        super().__init__(threshold, **kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def _default_threshold(self) -> float:
        return 0.03  # 默认3%的越界率阈值

    def _get_bounds(
        self,
        values: np.ndarray,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, float]:
        """
        获取数据的合理边界

        如果显式指定了边界则使用，否则基于数据统计自动计算。
        """
        if self.min_value is not None and self.max_value is not None:
            return self.min_value, self.max_value

        # 基于IQR方法计算边界
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        min_bound = q1 - 3.0 * iqr
        max_bound = q3 + 3.0 * iqr

        # 如果显式指定了单个边界
        if self.min_value is not None:
            min_bound = self.min_value
        if self.max_value is not None:
            max_bound = self.max_value

        return min_bound, max_bound

    def evaluate(
        self,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, Optional[RuleViolation]]:
        if len(values) == 0:
            return 100.0, None

        min_bound, max_bound = self._get_bounds(values, sensor_id)

        # 检测越界
        out_of_bounds_mask = (values < min_bound) | (values > max_bound)
        oob_count = int(np.sum(out_of_bounds_mask))
        oob_indices = np.where(out_of_bounds_mask)[0].tolist()

        if oob_count == 0:
            return 100.0, None

        oob_rate = oob_count / len(values)

        # 计算越界的严重程度（偏离边界的程度）
        deviations = []
        for idx in oob_indices:
            val = values[idx]
            if val < min_bound:
                deviations.append(abs(val - min_bound) / (max_bound - min_bound + 1e-9))
            else:
                deviations.append(abs(val - max_bound) / (max_bound - min_bound + 1e-9))

        avg_deviation = float(np.mean(deviations)) if deviations else 0.0
        max_deviation = float(np.max(deviations)) if deviations else 0.0

        if oob_rate <= self.threshold:
            quality_score = 100.0 - (oob_rate / self.threshold) * 40.0
            violation = None
        else:
            quality_score = max(0.0, 100.0 - (oob_rate - self.threshold) / (1.0 - self.threshold) * 100.0)
            violation_score = min(100.0, (oob_rate - self.threshold) / (1.0 - self.threshold) * 100.0)
            severity = self._determine_severity(violation_score * (1 + avg_deviation))

            violation = RuleViolation(
                rule_type=self.rule_type,
                severity=severity,
                message=f"检测到 {oob_count} 个越界点，占比 {oob_rate:.1%}，边界 [{min_bound:.2f}, {max_bound:.2f}]",
                score=violation_score,
                indices=oob_indices,
                details={
                    'out_of_bounds_count': oob_count,
                    'total_count': len(values),
                    'out_of_bounds_rate': oob_rate,
                    'min_bound': min_bound,
                    'max_bound': max_bound,
                    'avg_deviation': avg_deviation,
                    'max_deviation': max_deviation,
                    'threshold': self.threshold,
                }
            )

        return quality_score, violation


class DriftDetectionRule(DataQualityRule):
    """
    漂移检测规则

    检测数据的统计特性是否发生显著漂移（均值漂移、方差漂移）。
    使用滑动窗口方法比较最近数据与历史数据的分布差异。
    """

    rule_type = RuleType.DRIFT
    name = "漂移检测"
    description = "检测数据统计特性的显著漂移"

    def __init__(
        self,
        threshold: float = None,
        window_size: int = 50,
        reference_ratio: float = 0.5,
        **kwargs,
    ):
        super().__init__(threshold, **kwargs)
        self.window_size = window_size
        self.reference_ratio = reference_ratio

    def _default_threshold(self) -> float:
        return 2.0  # 默认2倍标准差的漂移阈值

    def evaluate(
        self,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        sensor_id: Optional[str] = None,
    ) -> Tuple[float, Optional[RuleViolation]]:
        if len(values) < self.window_size * 2:
            return 100.0, None

        # 分割为参考数据和检测数据
        split_idx = int(len(values) * self.reference_ratio)
        reference_data = values[:split_idx]
        detection_data = values[split_idx:]

        if len(reference_data) < self.window_size or len(detection_data) < self.window_size:
            return 100.0, None

        # 计算参考统计量
        ref_mean = float(np.mean(reference_data))
        ref_std = float(np.std(reference_data)) + 1e-9

        # 计算检测数据的滑动窗口统计量
        drift_scores = []
        drift_indices = []

        for i in range(0, len(detection_data) - self.window_size + 1, max(1, self.window_size // 2)):
            window = detection_data[i:i + self.window_size]
            window_mean = float(np.mean(window))
            window_std = float(np.std(window))

            # 计算均值漂移（Z-score）
            mean_drift = abs(window_mean - ref_mean) / ref_std
            # 计算方差漂移（F-ratio）
            var_drift = max(window_std / ref_std, ref_std / (window_std + 1e-9))

            # 综合漂移评分
            drift_score = max(mean_drift, (var_drift - 1) * 2)
            drift_scores.append(drift_score)

            if drift_score > self.threshold:
                # 记录漂移点（原始数据中的索引）
                start_idx = split_idx + i
                end_idx = split_idx + i + self.window_size
                drift_indices.extend(list(range(start_idx, end_idx)))

        if not drift_scores:
            return 100.0, None

        max_drift = float(np.max(drift_scores))
        avg_drift = float(np.mean(drift_scores))

        if max_drift <= self.threshold:
            quality_score = 100.0 - (max_drift / self.threshold) * 30.0
            violation = None
        else:
            # 漂移越严重，质量评分越低
            drift_excess = max_drift - self.threshold
            quality_score = max(0.0, 100.0 - drift_excess * 10.0)
            violation_score = min(100.0, drift_excess * 10.0)
            severity = self._determine_severity(violation_score)

            violation = RuleViolation(
                rule_type=self.rule_type,
                severity=severity,
                message=f"检测到数据漂移，最大漂移 {max_drift:.2f} 倍标准差（阈值 {self.threshold}）",
                score=violation_score,
                indices=sorted(list(set(drift_indices))),
                details={
                    'reference_mean': ref_mean,
                    'reference_std': ref_std,
                    'max_drift': max_drift,
                    'avg_drift': avg_drift,
                    'window_size': self.window_size,
                    'threshold': self.threshold,
                    'drift_points_count': len(set(drift_indices)),
                }
            )

        return quality_score, violation


class RulesEngine:
    """
    规则引擎

    组合所有质量规则，执行完整的数据质量检查。
    """

    def __init__(
        self,
        rules: Optional[List[DataQualityRule]] = None,
        weights: Optional[Dict[RuleType, float]] = None,
    ):
        """
        初始化规则引擎

        Args:
            rules: 使用的规则列表，None则使用所有默认规则
            weights: 各规则权重，None则使用等权重
        """
        self.rules = rules or self._default_rules()

        if weights is None:
            self.weights = {rule.rule_type: 1.0 for rule in self.rules}
        else:
            self.weights = weights

        logger.info(f"规则引擎初始化完成，包含 {len(self.rules)} 条规则")

    def _default_rules(self) -> List[DataQualityRule]:
        """创建默认规则列表"""
        from app.utils.config import config
        dq_config = config.get('data_quality', {})

        return [
            MissingRateRule(threshold=dq_config.get('missing_rate_threshold', 0.05)),
            DuplicateRule(threshold=dq_config.get('duplicate_threshold', 0.02)),
            TimeInversionRule(threshold=dq_config.get('time_inversion_threshold', 0.01)),
            OutOfBoundsRule(
                threshold=dq_config.get('out_of_bounds_threshold', 0.03),
                min_value=dq_config.get('min_value'),
                max_value=dq_config.get('max_value'),
            ),
            DriftDetectionRule(
                threshold=dq_config.get('drift_threshold', 2.0),
                window_size=dq_config.get('drift_window_size', 50),
            ),
        ]

    def check(
        self,
        sensor_id: str,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
    ) -> QualityCheckResult:
        """
        执行完整的数据质量检查

        Args:
            sensor_id: 传感器ID
            values: 数据值数组
            timestamps: 时间戳数组

        Returns:
            QualityCheckResult: 质量检查结果
        """
        violations = []
        rule_scores = {}
        total_weight = 0.0
        weighted_score = 0.0

        for rule in self.rules:
            weight = self.weights.get(rule.rule_type, 1.0)
            score, violation = rule.evaluate(values, timestamps, sensor_id)

            rule_scores[rule.rule_type] = score
            weighted_score += score * weight
            total_weight += weight

            if violation is not None:
                violations.append(violation)

        # 计算综合评分
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0

        # 计算有效数据点（排除所有违反规则的点）
        invalid_indices = set()
        for v in violations:
            invalid_indices.update(v.indices)
        valid_points = len(values) - len(invalid_indices)

        return QualityCheckResult(
            sensor_id=sensor_id,
            total_points=len(values),
            valid_points=valid_points,
            violations=violations,
            rule_scores=rule_scores,
            overall_score=overall_score,
        )
