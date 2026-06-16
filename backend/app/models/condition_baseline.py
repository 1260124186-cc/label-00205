"""
工况基线模型与动态阈值模块

为每种工况维护独立的基线模型和动态阈值：
1. 稳态运行：基于统计的基线模型，严格的异常阈值
2. 升负荷：趋势跟踪基线，宽松的上升阈值，严格的下降阈值
3. 降负荷：趋势跟踪基线，宽松的下降阈值，严格的上升阈值
4. 停机冷却：衰减基线模型，低绝对值阈值
5. 检修后恢复：恢复基线模型，渐进式阈值

功能:
1. 各工况独立基线维护
2. 动态阈值自适应调整
3. 基线模型增量更新
4. 异常检测（基于工况的阈值判断）
5. 阈值配置管理
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from collections import deque
from scipy import stats

from app.models.working_condition_classifier import WorkingCondition
from app.utils.config import config


@dataclass
class ConditionBaseline:
    """
    工况基线数据
    """
    condition: WorkingCondition
    mean: float = 0.0
    std: float = 0.0
    upper_bound: float = 0.0
    lower_bound: float = 0.0
    warning_upper: float = 0.0
    warning_lower: float = 0.0
    trend_slope: float = 0.0
    trend_intercept: float = 0.0
    sample_count: int = 0
    update_time: float = 0.0
    is_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'condition': self.condition.value,
            'mean': self.mean,
            'std': self.std,
            'upper_bound': self.upper_bound,
            'lower_bound': self.lower_bound,
            'warning_upper': self.warning_upper,
            'warning_lower': self.warning_lower,
            'trend_slope': self.trend_slope,
            'trend_intercept': self.trend_intercept,
            'sample_count': self.sample_count,
            'is_valid': self.is_valid,
        }


@dataclass
class ThresholdConfig:
    """
    阈值配置
    """
    sigma_upper: float = 3.0
    sigma_lower: float = 3.0
    warning_sigma_upper: float = 2.0
    warning_sigma_lower: float = 2.0
    min_std: float = 1.0
    adaptive_enabled: bool = True
    adaptive_rate: float = 0.1
    trend_weight: float = 0.3


@dataclass
class AnomalyResult:
    """
    异常检测结果
    """
    is_anomaly: bool
    is_warning: bool
    anomaly_level: str
    anomaly_type: str
    value: float
    baseline: float
    deviation: float
    deviation_ratio: float
    threshold_upper: float
    threshold_lower: float
    condition: WorkingCondition
    confidence: float


class ConditionBaselineManager:
    """
    工况基线管理器

    为每种工况维护独立的基线模型和动态阈值。
    支持基线增量更新和自适应阈值调整。

    Attributes:
        baselines: 各工况基线字典
        threshold_configs: 各工况阈值配置
        history_buffer: 历史数据缓冲（用于增量更新）
        max_history_size: 最大历史数据量
    """

    def __init__(self):
        """
        初始化工况基线管理器
        """
        self.baselines: Dict[WorkingCondition, ConditionBaseline] = {}
        self.threshold_configs: Dict[WorkingCondition, ThresholdConfig] = {}
        self.history_buffers: Dict[WorkingCondition, deque] = {}
        self.trend_buffers: Dict[WorkingCondition, deque] = {}

        wc_config = config.get('working_condition', {})
        self.max_history_size = wc_config.get('baseline.max_history_size', 10000)
        self.min_samples_for_baseline = wc_config.get('baseline.min_samples', 100)
        self.update_interval = wc_config.get('baseline.update_interval', 10)
        self._update_counters: Dict[WorkingCondition, int] = {}

        self._init_default_configs()
        self._init_baselines()

        logger.info("工况基线管理器初始化完成")

    def _init_default_configs(self) -> None:
        """
        初始化各工况的默认阈值配置
        """
        wc_config = config.get('working_condition', {})

        self.threshold_configs[WorkingCondition.STEADY_STATE] = ThresholdConfig(
            sigma_upper=wc_config.get('steady_state.threshold.sigma_upper', 3.0),
            sigma_lower=wc_config.get('steady_state.threshold.sigma_lower', 3.0),
            warning_sigma_upper=wc_config.get('steady_state.threshold.warning_sigma_upper', 2.0),
            warning_sigma_lower=wc_config.get('steady_state.threshold.warning_sigma_lower', 2.0),
            min_std=wc_config.get('steady_state.threshold.min_std', 5.0),
            adaptive_enabled=wc_config.get('steady_state.threshold.adaptive_enabled', True),
            adaptive_rate=wc_config.get('steady_state.threshold.adaptive_rate', 0.05),
            trend_weight=wc_config.get('steady_state.threshold.trend_weight', 0.1),
        )

        self.threshold_configs[WorkingCondition.LOAD_INCREASE] = ThresholdConfig(
            sigma_upper=wc_config.get('load_increase.threshold.sigma_upper', 4.0),
            sigma_lower=wc_config.get('load_increase.threshold.sigma_lower', 2.0),
            warning_sigma_upper=wc_config.get('load_increase.threshold.warning_sigma_upper', 2.5),
            warning_sigma_lower=wc_config.get('load_increase.threshold.warning_sigma_lower', 1.5),
            min_std=wc_config.get('load_increase.threshold.min_std', 10.0),
            adaptive_enabled=wc_config.get('load_increase.threshold.adaptive_enabled', True),
            adaptive_rate=wc_config.get('load_increase.threshold.adaptive_rate', 0.1),
            trend_weight=wc_config.get('load_increase.threshold.trend_weight', 0.6),
        )

        self.threshold_configs[WorkingCondition.LOAD_DECREASE] = ThresholdConfig(
            sigma_upper=wc_config.get('load_decrease.threshold.sigma_upper', 2.0),
            sigma_lower=wc_config.get('load_decrease.threshold.sigma_lower', 4.0),
            warning_sigma_upper=wc_config.get('load_decrease.threshold.warning_sigma_upper', 1.5),
            warning_sigma_lower=wc_config.get('load_decrease.threshold.warning_sigma_lower', 2.5),
            min_std=wc_config.get('load_decrease.threshold.min_std', 10.0),
            adaptive_enabled=wc_config.get('load_decrease.threshold.adaptive_enabled', True),
            adaptive_rate=wc_config.get('load_decrease.threshold.adaptive_rate', 0.1),
            trend_weight=wc_config.get('load_decrease.threshold.trend_weight', 0.6),
        )

        self.threshold_configs[WorkingCondition.SHUTDOWN_COOLING] = ThresholdConfig(
            sigma_upper=wc_config.get('shutdown_cooling.threshold.sigma_upper', 2.5),
            sigma_lower=wc_config.get('shutdown_cooling.threshold.sigma_lower', 2.5),
            warning_sigma_upper=wc_config.get('shutdown_cooling.threshold.warning_sigma_upper', 1.5),
            warning_sigma_lower=wc_config.get('shutdown_cooling.threshold.warning_sigma_lower', 1.5),
            min_std=wc_config.get('shutdown_cooling.threshold.min_std', 3.0),
            adaptive_enabled=wc_config.get('shutdown_cooling.threshold.adaptive_enabled', False),
            adaptive_rate=wc_config.get('shutdown_cooling.threshold.adaptive_rate', 0.02),
            trend_weight=wc_config.get('shutdown_cooling.threshold.trend_weight', 0.8),
        )

        self.threshold_configs[WorkingCondition.POST_MAINTENANCE_RECOVERY] = ThresholdConfig(
            sigma_upper=wc_config.get('post_maintenance.threshold.sigma_upper', 3.5),
            sigma_lower=wc_config.get('post_maintenance.threshold.sigma_lower', 2.5),
            warning_sigma_upper=wc_config.get('post_maintenance.threshold.warning_sigma_upper', 2.0),
            warning_sigma_lower=wc_config.get('post_maintenance.threshold.warning_sigma_lower', 1.5),
            min_std=wc_config.get('post_maintenance.threshold.min_std', 8.0),
            adaptive_enabled=wc_config.get('post_maintenance.threshold.adaptive_enabled', True),
            adaptive_rate=wc_config.get('post_maintenance.threshold.adaptive_rate', 0.15),
            trend_weight=wc_config.get('post_maintenance.threshold.trend_weight', 0.5),
        )

        self.threshold_configs[WorkingCondition.UNKNOWN] = ThresholdConfig(
            sigma_upper=3.0,
            sigma_lower=3.0,
            warning_sigma_upper=2.0,
            warning_sigma_lower=2.0,
            min_std=5.0,
            adaptive_enabled=True,
            adaptive_rate=0.05,
            trend_weight=0.2,
        )

    def _init_baselines(self) -> None:
        """
        初始化各工况的基线
        """
        for condition in WorkingCondition:
            self.baselines[condition] = ConditionBaseline(condition=condition)
            self.history_buffers[condition] = deque(maxlen=self.max_history_size)
            self.trend_buffers[condition] = deque(maxlen=self.max_history_size)
            self._update_counters[condition] = 0

    def update_baseline(
        self,
        condition: WorkingCondition,
        data: np.ndarray,
        incremental: bool = True,
    ) -> bool:
        """
        更新指定工况的基线

        Args:
            condition: 工况类型
            data: 数据序列
            incremental: 是否增量更新

        Returns:
            bool: 是否更新成功
        """
        if condition not in self.baselines:
            return False

        try:
            data = np.asarray(data, dtype=np.float64).flatten()
            if len(data) == 0:
                return False

            if incremental:
                self.history_buffers[condition].extend(data.tolist())
                self._update_counters[condition] += len(data)

                if self._update_counters[condition] < self.update_interval:
                    return True

                self._update_counters[condition] = 0
                history_data = np.array(self.history_buffers[condition])
            else:
                history_data = data
                self.history_buffers[condition].clear()
                self.history_buffers[condition].extend(data.tolist())

            if len(history_data) < self.min_samples_for_baseline:
                return False

            baseline = self.baselines[condition]
            threshold_config = self.threshold_configs[condition]

            mean = float(np.mean(history_data))
            std = float(np.std(history_data))
            std = max(std, threshold_config.min_std)

            n = len(history_data)
            x = np.arange(n)
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, history_data)

            trend_weight = threshold_config.trend_weight
            base_mean = mean * (1 - trend_weight) + (intercept + slope * n / 2) * trend_weight

            adaptive_std = std
            if threshold_config.adaptive_enabled and baseline.is_valid:
                adaptive_std = (
                    baseline.std * (1 - threshold_config.adaptive_rate)
                    + std * threshold_config.adaptive_rate
                )
                adaptive_std = max(adaptive_std, threshold_config.min_std)

            upper_bound = base_mean + threshold_config.sigma_upper * adaptive_std
            lower_bound = base_mean - threshold_config.sigma_lower * adaptive_std
            warning_upper = base_mean + threshold_config.warning_sigma_upper * adaptive_std
            warning_lower = base_mean - threshold_config.warning_sigma_lower * adaptive_std

            baseline.mean = base_mean
            baseline.std = adaptive_std
            baseline.upper_bound = upper_bound
            baseline.lower_bound = lower_bound
            baseline.warning_upper = warning_upper
            baseline.warning_lower = warning_lower
            baseline.trend_slope = float(slope)
            baseline.trend_intercept = float(intercept)
            baseline.sample_count = len(history_data)
            baseline.update_time = float(np.datetime64('now').astype('float64') / 1e9)
            baseline.is_valid = True

            logger.debug(
                f"基线更新: {condition.value}, "
                f"mean={base_mean:.2f}, std={adaptive_std:.2f}, "
                f"upper={upper_bound:.2f}, lower={lower_bound:.2f}, "
                f"samples={len(history_data)}"
            )

            return True

        except Exception as e:
            logger.error(f"更新基线失败: {condition.value}, 错误: {e}")
            return False

    def get_baseline(self, condition: WorkingCondition) -> Optional[ConditionBaseline]:
        """
        获取指定工况的基线

        Args:
            condition: 工况类型

        Returns:
            ConditionBaseline or None
        """
        return self.baselines.get(condition)

    def check_anomaly(
        self,
        condition: WorkingCondition,
        value: float,
        position: Optional[int] = None,
    ) -> AnomalyResult:
        """
        检查值是否异常（基于工况的动态阈值）

        Args:
            condition: 当前工况
            value: 待检测的值
            position: 在趋势中的位置（用于趋势基线调整）

        Returns:
            AnomalyResult: 异常检测结果
        """
        baseline = self.baselines.get(condition)
        threshold_config = self.threshold_configs.get(
            condition, self.threshold_configs[WorkingCondition.UNKNOWN]
        )

        if baseline is None or not baseline.is_valid:
            return AnomalyResult(
                is_anomaly=False,
                is_warning=False,
                anomaly_level='normal',
                anomaly_type='baseline_not_ready',
                value=value,
                baseline=value,
                deviation=0.0,
                deviation_ratio=0.0,
                threshold_upper=value * 1.5,
                threshold_lower=value * 0.5,
                condition=condition,
                confidence=0.5,
            )

        adjusted_mean = baseline.mean
        if position is not None and baseline.trend_slope != 0:
            trend_contribution = baseline.trend_slope * position * threshold_config.trend_weight
            adjusted_mean = baseline.mean + trend_contribution

        deviation = value - adjusted_mean
        deviation_ratio = deviation / (abs(adjusted_mean) + 1e-8)

        is_warning = (
            value > baseline.warning_upper
            or value < baseline.warning_lower
        )
        is_anomaly = (
            value > baseline.upper_bound
            or value < baseline.lower_bound
        )

        if value > baseline.upper_bound:
            anomaly_level = 'critical_high'
            anomaly_type = 'over_limit_high'
        elif value < baseline.lower_bound:
            anomaly_level = 'critical_low'
            anomaly_type = 'over_limit_low'
        elif value > baseline.warning_upper:
            anomaly_level = 'warning_high'
            anomaly_type = 'warning_high'
        elif value < baseline.warning_lower:
            anomaly_level = 'warning_low'
            anomaly_type = 'warning_low'
        else:
            anomaly_level = 'normal'
            anomaly_type = 'normal'

        confidence = self._calculate_anomaly_confidence(
            value, adjusted_mean, baseline.std, threshold_config
        )

        return AnomalyResult(
            is_anomaly=is_anomaly,
            is_warning=is_warning,
            anomaly_level=anomaly_level,
            anomaly_type=anomaly_type,
            value=value,
            baseline=adjusted_mean,
            deviation=deviation,
            deviation_ratio=deviation_ratio,
            threshold_upper=baseline.upper_bound,
            threshold_lower=baseline.lower_bound,
            condition=condition,
            confidence=confidence,
        )

    def _calculate_anomaly_confidence(
        self,
        value: float,
        mean: float,
        std: float,
        config: ThresholdConfig,
    ) -> float:
        """
        计算异常检测的置信度

        Args:
            value: 检测值
            mean: 基线均值
            std: 基线标准差
            config: 阈值配置

        Returns:
            float: 置信度 0-1
        """
        if std <= 0:
            return 0.5

        z_score = abs(value - mean) / std

        if z_score >= config.sigma_upper:
            confidence = min(0.99, 0.7 + (z_score - config.sigma_upper) * 0.1)
        elif z_score >= config.warning_sigma_upper:
            confidence = 0.5 + (z_score - config.warning_sigma_upper) / (
                config.sigma_upper - config.warning_sigma_upper
            ) * 0.4
        else:
            confidence = max(0.1, 0.5 - z_score / config.warning_sigma_upper * 0.4)

        return float(confidence)

    def batch_check_anomaly(
        self,
        condition: WorkingCondition,
        values: np.ndarray,
    ) -> List[AnomalyResult]:
        """
        批量异常检测

        Args:
            condition: 当前工况
            values: 待检测的值数组

        Returns:
            异常结果列表
        """
        values = np.asarray(values, dtype=np.float64).flatten()
        results = []
        for i, value in enumerate(values):
            result = self.check_anomaly(condition, float(value), position=i)
            results.append(result)
        return results

    def get_anomaly_summary(
        self,
        condition: WorkingCondition,
        values: np.ndarray,
    ) -> Dict[str, Any]:
        """
        获取异常检测汇总

        Args:
            condition: 当前工况
            values: 数据序列

        Returns:
            异常检测汇总信息
        """
        results = self.batch_check_anomaly(condition, values)

        anomaly_count = sum(1 for r in results if r.is_anomaly)
        warning_count = sum(1 for r in results if r.is_warning and not r.is_anomaly)
        normal_count = len(results) - anomaly_count - warning_count

        anomalies = [
            {
                'index': i,
                'value': r.value,
                'level': r.anomaly_level,
                'type': r.anomaly_type,
                'deviation': r.deviation,
            }
            for i, r in enumerate(results)
            if r.is_anomaly or r.is_warning
        ]

        baseline = self.get_baseline(condition)

        return {
            'condition': condition.value,
            'condition_label': condition.value,
            'total_count': len(values),
            'anomaly_count': anomaly_count,
            'warning_count': warning_count,
            'normal_count': normal_count,
            'anomaly_ratio': anomaly_count / len(values) if len(values) > 0 else 0,
            'warning_ratio': warning_count / len(values) if len(values) > 0 else 0,
            'anomalies': anomalies[:20],
            'baseline': baseline.to_dict() if baseline else None,
        }

    def set_threshold_config(
        self,
        condition: WorkingCondition,
        config: ThresholdConfig,
    ) -> None:
        """
        设置指定工况的阈值配置

        Args:
            condition: 工况类型
            config: 阈值配置
        """
        self.threshold_configs[condition] = config
        logger.info(f"阈值配置已更新: {condition.value}")

    def reset_baseline(self, condition: WorkingCondition) -> None:
        """
        重置指定工况的基线

        Args:
            condition: 工况类型
        """
        if condition in self.baselines:
            self.baselines[condition] = ConditionBaseline(condition=condition)
            self.history_buffers[condition].clear()
            self.trend_buffers[condition].clear()
            self._update_counters[condition] = 0
            logger.info(f"基线已重置: {condition.value}")

    def reset_all(self) -> None:
        """
        重置所有工况的基线
        """
        for condition in WorkingCondition:
            self.reset_baseline(condition)
        logger.info("所有工况基线已重置")

    def get_all_baselines(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有工况的基线信息

        Returns:
            各工况基线字典
        """
        return {
            cond.value: baseline.to_dict()
            for cond, baseline in self.baselines.items()
        }

    def get_dynamic_threshold_at(
        self,
        condition: WorkingCondition,
        position: int,
    ) -> Dict[str, float]:
        """
        获取指定位置的动态阈值

        Args:
            condition: 工况类型
            position: 位置索引

        Returns:
            阈值信息字典
        """
        baseline = self.get_baseline(condition)
        config = self.threshold_configs.get(
            condition, self.threshold_configs[WorkingCondition.UNKNOWN]
        )

        if baseline is None or not baseline.is_valid:
            return {
                'upper': 0.0,
                'lower': 0.0,
                'warning_upper': 0.0,
                'warning_lower': 0.0,
                'baseline': 0.0,
            }

        trend_offset = baseline.trend_slope * position * config.trend_weight
        adjusted_mean = baseline.mean + trend_offset

        return {
            'upper': adjusted_mean + config.sigma_upper * baseline.std,
            'lower': adjusted_mean - config.sigma_lower * baseline.std,
            'warning_upper': adjusted_mean + config.warning_sigma_upper * baseline.std,
            'warning_lower': adjusted_mean - config.warning_sigma_lower * baseline.std,
            'baseline': adjusted_mean,
        }
