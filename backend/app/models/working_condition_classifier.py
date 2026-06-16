"""
工况分类器模块

基于无监督/弱监督学习的工况识别，支持5种典型工况：
1. 稳态运行 (STEADY_STATE)
2. 升负荷 (LOAD_INCREASE)
3. 降负荷 (LOAD_DECREASE)
4. 停机冷却 (SHUTDOWN_COOLING)
5. 检修后恢复 (POST_MAINTENANCE_RECOVERY)

功能:
1. 多维度特征提取（统计特征、趋势特征、变化率特征）
2. 无监督聚类（KMeans + 轮廓系数自动确定簇数）
3. 规则校验（领域知识辅助分类）
4. 工况概率分布输出
5. 工况平滑处理（避免抖动）
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from scipy import stats

from app.utils.config import config


class WorkingCondition(Enum):
    """
    工况类型枚举
    """
    STEADY_STATE = "steady_state"
    LOAD_INCREASE = "load_increase"
    LOAD_DECREASE = "load_decrease"
    SHUTDOWN_COOLING = "shutdown_cooling"
    POST_MAINTENANCE_RECOVERY = "post_maintenance_recovery"
    UNKNOWN = "unknown"


WORKING_CONDITION_LABELS = {
    WorkingCondition.STEADY_STATE: "稳态运行",
    WorkingCondition.LOAD_INCREASE: "升负荷",
    WorkingCondition.LOAD_DECREASE: "降负荷",
    WorkingCondition.SHUTDOWN_COOLING: "停机冷却",
    WorkingCondition.POST_MAINTENANCE_RECOVERY: "检修后恢复",
    WorkingCondition.UNKNOWN: "未知工况",
}


@dataclass
class ConditionClassificationResult:
    """
    工况分类结果
    """
    condition: WorkingCondition
    condition_label: str
    confidence: float
    probabilities: Dict[WorkingCondition, float]
    features: Dict[str, float]
    is_transition: bool
    transition_from: Optional[WorkingCondition] = None
    transition_to: Optional[WorkingCondition] = None


@dataclass
class ConditionFeatureSet:
    """
    工况特征集合
    """
    statistical_features: Dict[str, float] = field(default_factory=dict)
    trend_features: Dict[str, float] = field(default_factory=dict)
    rate_features: Dict[str, float] = field(default_factory=dict)
    all_features: np.ndarray = field(default_factory=lambda: np.array([]))
    feature_names: List[str] = field(default_factory=list)


class WorkingConditionClassifier:
    """
    工况分类器（无监督 + 弱监督）

    结合无监督聚类和领域规则进行工况识别。

    Attributes:
        scaler: 特征标准化器
        kmeans: KMeans 聚类模型
        cluster_to_condition: 簇到工况的映射
        is_fitted: 是否已拟合
        condition_configs: 各工况的配置参数
    """

    def __init__(self):
        """
        初始化工况分类器
        """
        self.scaler = StandardScaler()
        self.kmeans: Optional[KMeans] = None
        self.cluster_to_condition: Dict[int, WorkingCondition] = {}
        self.is_fitted = False

        wc_config = config.get('working_condition', {})
        self.condition_configs = {
            WorkingCondition.STEADY_STATE: {
                'cv_threshold': wc_config.get('steady_state.cv_threshold', 0.08),
                'trend_threshold': wc_config.get('steady_state.trend_threshold', 0.003),
            },
            WorkingCondition.LOAD_INCREASE: {
                'rate_threshold': wc_config.get('load_increase.rate_threshold', 0.0015),
                'min_increase_ratio': wc_config.get('load_increase.min_increase_ratio', 0.5),
                'min_trend_strength': wc_config.get('load_increase.min_trend_strength', 0.7),
            },
            WorkingCondition.LOAD_DECREASE: {
                'rate_threshold': wc_config.get('load_decrease.rate_threshold', 0.0015),
                'min_decrease_ratio': wc_config.get('load_decrease.min_decrease_ratio', 0.5),
                'min_trend_strength': wc_config.get('load_decrease.min_trend_strength', 0.7),
            },
            WorkingCondition.SHUTDOWN_COOLING: {
                'low_value_ratio': wc_config.get('shutdown_cooling.low_value_ratio', 0.5),
                'decrease_rate': wc_config.get('shutdown_cooling.decrease_rate', 0.003),
                'value_ratio_threshold': wc_config.get('shutdown_cooling.value_ratio_threshold', 0.5),
                'min_trend_strength': wc_config.get('shutdown_cooling.min_trend_strength', 0.9),
                'min_range_ratio': wc_config.get('shutdown_cooling.min_range_ratio', 0.4),
            },
            WorkingCondition.POST_MAINTENANCE_RECOVERY: {
                'recovery_ratio': wc_config.get('post_maintenance.recovery_ratio', 0.6),
                'increase_rate': wc_config.get('post_maintenance.increase_rate', 0.002),
                'volatility_threshold': wc_config.get('post_maintenance.volatility_threshold', 0.2),
                'min_trend_strength': wc_config.get('post_maintenance.min_trend_strength', 0.5),
            },
        }

        self.max_clusters = wc_config.get('max_clusters', 8)
        self.min_clusters = wc_config.get('min_clusters', 3)
        self.smooth_window = wc_config.get('smooth_window', 5)

        self._recent_conditions: List[WorkingCondition] = []

        logger.info("工况分类器初始化完成")

    def extract_features(self, data: np.ndarray) -> ConditionFeatureSet:
        """
        提取工况识别特征

        Args:
            data: 时间序列数据

        Returns:
            ConditionFeatureSet: 特征集合
        """
        if len(data) < 10:
            raise ValueError("数据长度不足，至少需要10个数据点")

        data = np.asarray(data, dtype=np.float64).flatten()
        feature_set = ConditionFeatureSet()

        # 统计特征
        feature_set.statistical_features = {
            'mean': float(np.mean(data)),
            'std': float(np.std(data)),
            'cv': float(np.std(data) / (np.mean(data) + 1e-8)),
            'min': float(np.min(data)),
            'max': float(np.max(data)),
            'range': float(np.max(data) - np.min(data)),
            'median': float(np.median(data)),
            'q1': float(np.percentile(data, 25)),
            'q3': float(np.percentile(data, 75)),
            'iqr': float(np.percentile(data, 75) - np.percentile(data, 25)),
            'skewness': float(stats.skew(data)),
            'kurtosis': float(stats.kurtosis(data)),
        }

        # 趋势特征
        n = len(data)
        x = np.arange(n)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, data)
        feature_set.trend_features = {
            'slope': float(slope),
            'slope_normalized': float(slope / (np.mean(data) + 1e-8)),
            'r_squared': float(r_value ** 2),
            'p_value': float(p_value),
            'trend_strength': float(abs(r_value)),
        }

        # 变化率特征
        diffs = np.diff(data)
        normalized_diffs = diffs / (np.mean(data) + 1e-8)

        increase_count = np.sum(diffs > 0)
        decrease_count = np.sum(diffs < 0)
        total_changes = len(diffs)

        feature_set.rate_features = {
            'mean_diff': float(np.mean(diffs)),
            'mean_abs_diff': float(np.mean(np.abs(diffs))),
            'max_increase': float(np.max(diffs)) if len(diffs) > 0 else 0.0,
            'max_decrease': float(np.min(diffs)) if len(diffs) > 0 else 0.0,
            'increase_ratio': float(increase_count / total_changes) if total_changes > 0 else 0.0,
            'decrease_ratio': float(decrease_count / total_changes) if total_changes > 0 else 0.0,
            'normalized_mean_diff': float(np.mean(normalized_diffs)),
            'normalized_mean_abs_diff': float(np.mean(np.abs(normalized_diffs))),
            'acceleration': float(np.mean(np.diff(diffs))) if len(diffs) > 1 else 0.0,
        }

        # 组合所有特征
        all_features_dict = {
            **feature_set.statistical_features,
            **feature_set.trend_features,
            **feature_set.rate_features,
        }
        feature_set.feature_names = list(all_features_dict.keys())
        feature_set.all_features = np.array([all_features_dict[k] for k in feature_set.feature_names])

        return feature_set

    def _rule_based_classify(
        self,
        features: ConditionFeatureSet,
        historical_data: Optional[np.ndarray] = None,
    ) -> Tuple[WorkingCondition, Dict[WorkingCondition, float]]:
        """
        基于规则的工况分类（弱监督）

        Args:
            features: 特征集合
            historical_data: 历史数据（用于基准值对比）

        Returns:
            (工况, 各工况概率)
        """
        stats_feat = features.statistical_features
        trend_feat = features.trend_features
        rate_feat = features.rate_features

        probabilities: Dict[WorkingCondition, float] = {
            WorkingCondition.STEADY_STATE: 0.0,
            WorkingCondition.LOAD_INCREASE: 0.0,
            WorkingCondition.LOAD_DECREASE: 0.0,
            WorkingCondition.SHUTDOWN_COOLING: 0.0,
            WorkingCondition.POST_MAINTENANCE_RECOVERY: 0.0,
        }

        cv = stats_feat['cv']
        slope_norm = trend_feat['slope_normalized']
        trend_strength = trend_feat['trend_strength']
        increase_ratio = rate_feat['increase_ratio']
        decrease_ratio = rate_feat['decrease_ratio']
        mean_value = stats_feat['mean']
        value_range = stats_feat['range']

        # 计算基准值（用于判断停机/恢复）
        baseline = None
        if historical_data is not None and len(historical_data) > 0:
            baseline = float(np.percentile(historical_data, 75))
        else:
            baseline = mean_value * 1.5

        value_ratio = mean_value / (baseline + 1e-8)

        # 稳态运行判定
        steady_config = self.condition_configs[WorkingCondition.STEADY_STATE]
        if cv < steady_config['cv_threshold'] and abs(slope_norm) < steady_config['trend_threshold']:
            probabilities[WorkingCondition.STEADY_STATE] = 0.8 + (1 - cv / steady_config['cv_threshold']) * 0.2
        elif cv < steady_config['cv_threshold'] * 2:
            probabilities[WorkingCondition.STEADY_STATE] = 0.4
        else:
            probabilities[WorkingCondition.STEADY_STATE] = max(0.0, 0.3 - cv)

        # 升负荷判定
        increase_config = self.condition_configs[WorkingCondition.LOAD_INCREASE]
        min_trend_strength = increase_config.get('min_trend_strength', 0.5)
        if (
            slope_norm > increase_config['rate_threshold']
            and increase_ratio > increase_config['min_increase_ratio']
            and trend_strength > min_trend_strength
        ):
            score = min(1.0, slope_norm / (increase_config['rate_threshold'] * 5))
            score *= min(1.0, increase_ratio / increase_config['min_increase_ratio'])
            score *= min(1.0, trend_strength / min_trend_strength)
            probabilities[WorkingCondition.LOAD_INCREASE] = 0.6 + score * 0.4
        elif slope_norm > 0 and trend_strength > 0.3:
            probabilities[WorkingCondition.LOAD_INCREASE] = 0.2 + slope_norm * 50

        # 降负荷判定
        decrease_config = self.condition_configs[WorkingCondition.LOAD_DECREASE]
        min_trend_strength = decrease_config.get('min_trend_strength', 0.6)
        max_trend_for_decrease = 0.96
        is_load_decrease = (
            slope_norm < -decrease_config['rate_threshold']
            and decrease_ratio > decrease_config['min_decrease_ratio']
            and min_trend_strength <= trend_strength < max_trend_for_decrease
        )

        if is_load_decrease:
            score = min(1.0, abs(slope_norm) / (decrease_config['rate_threshold'] * 5))
            score *= min(1.0, decrease_ratio / decrease_config['min_decrease_ratio'])
            trend_score = 1.0 - abs(trend_strength - (min_trend_strength + max_trend_for_decrease) / 2) / ((max_trend_for_decrease - min_trend_strength) / 2)
            score *= max(0.3, trend_score)
            probabilities[WorkingCondition.LOAD_DECREASE] = 0.55 + score * 0.45
        elif slope_norm < 0 and trend_strength > 0.3 and trend_strength < max_trend_for_decrease:
            probabilities[WorkingCondition.LOAD_DECREASE] = 0.2 + abs(slope_norm) * 40

        # 停机冷却判定
        shutdown_config = self.condition_configs[WorkingCondition.SHUTDOWN_COOLING]
        min_trend_strength = shutdown_config.get('min_trend_strength', 0.94)
        min_range_ratio = shutdown_config.get('min_range_ratio', 0.35)
        range_ratio = value_range / (mean_value + 1e-8)
        abs_slope = abs(slope_norm)

        # 计算总下降幅度相对于均值的比例
        total_drop_ratio = value_range / (mean_value + 1e-8)

        is_shutdown = (
            slope_norm < -shutdown_config.get('decrease_rate', 0.002)
            and trend_strength >= min_trend_strength
            and total_drop_ratio > min_range_ratio
        )

        if is_shutdown:
            score = min(1.0, (trend_strength - min_trend_strength) / (1.0 - min_trend_strength + 1e-8))
            score *= min(1.0, total_drop_ratio / (min_range_ratio * 2.5))
            score *= min(1.0, abs_slope / (shutdown_config['decrease_rate'] * 3))
            score = min(1.0, score)
            probabilities[WorkingCondition.SHUTDOWN_COOLING] = 0.6 + score * 0.4
        elif value_ratio < shutdown_config['value_ratio_threshold']:
            probabilities[WorkingCondition.SHUTDOWN_COOLING] = 0.35
        elif trend_strength >= 0.9 and slope_norm < -shutdown_config.get('decrease_rate', 0.002) and total_drop_ratio > 0.3:
            probabilities[WorkingCondition.SHUTDOWN_COOLING] = 0.4

        # 检修后恢复判定
        recovery_config = self.condition_configs[WorkingCondition.POST_MAINTENANCE_RECOVERY]
        min_trend_strength = recovery_config.get('min_trend_strength', 0.4)
        is_recovering = (
            value_ratio > shutdown_config.get('value_ratio_threshold', 0.3)
            and value_ratio < recovery_config['recovery_ratio']
            and slope_norm > recovery_config['increase_rate']
            and trend_strength > min_trend_strength
        )

        if is_recovering:
            volatility = rate_feat['normalized_mean_abs_diff']
            if volatility < recovery_config['volatility_threshold']:
                score = min(1.0, slope_norm / (recovery_config['increase_rate'] * 3))
                score *= min(1.0, (recovery_config['recovery_ratio'] - value_ratio) / recovery_config['recovery_ratio'])
                score *= min(1.0, trend_strength / min_trend_strength)
                probabilities[WorkingCondition.POST_MAINTENANCE_RECOVERY] = 0.5 + score * 0.5
            else:
                probabilities[WorkingCondition.POST_MAINTENANCE_RECOVERY] = 0.3
        elif value_ratio < recovery_config['recovery_ratio'] and slope_norm > 0:
            probabilities[WorkingCondition.POST_MAINTENANCE_RECOVERY] = 0.15

        # 归一化概率
        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}
        else:
            probabilities = {k: 0.2 for k in probabilities}

        # 确定主工况
        main_condition = max(probabilities, key=probabilities.get)

        return main_condition, probabilities

    def _cluster_based_classify(
        self,
        features: ConditionFeatureSet,
    ) -> Tuple[WorkingCondition, Dict[WorkingCondition, float]]:
        """
        基于聚类的工况分类（无监督）

        Args:
            features: 特征集合

        Returns:
            (工况, 各工况概率)
        """
        if not self.is_fitted or self.kmeans is None:
            return WorkingCondition.UNKNOWN, {
                WorkingCondition.STEADY_STATE: 0.2,
                WorkingCondition.LOAD_INCREASE: 0.2,
                WorkingCondition.LOAD_DECREASE: 0.2,
                WorkingCondition.SHUTDOWN_COOLING: 0.2,
                WorkingCondition.POST_MAINTENANCE_RECOVERY: 0.2,
            }

        # 标准化特征
        scaled_features = self.scaler.transform(features.all_features.reshape(1, -1))

        # 预测簇
        cluster = self.kmeans.predict(scaled_features)[0]
        distances = self.kmeans.transform(scaled_features)[0]

        # 转换为概率（距离越近概率越高）
        inv_distances = 1.0 / (distances + 1e-8)
        cluster_probs = inv_distances / np.sum(inv_distances)

        # 映射到工况
        probabilities: Dict[WorkingCondition, float] = {
            WorkingCondition.STEADY_STATE: 0.0,
            WorkingCondition.LOAD_INCREASE: 0.0,
            WorkingCondition.LOAD_DECREASE: 0.0,
            WorkingCondition.SHUTDOWN_COOLING: 0.0,
            WorkingCondition.POST_MAINTENANCE_RECOVERY: 0.0,
        }

        for i, prob in enumerate(cluster_probs):
            condition = self.cluster_to_condition.get(i, WorkingCondition.UNKNOWN)
            if condition != WorkingCondition.UNKNOWN:
                probabilities[condition] += prob

        total_prob = sum(probabilities.values())
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}

        main_condition = max(probabilities, key=probabilities.get)

        return main_condition, probabilities

    def _smooth_condition(
        self,
        current_condition: WorkingCondition,
        current_probabilities: Dict[WorkingCondition, float],
    ) -> Tuple[WorkingCondition, Dict[WorkingCondition, float], bool]:
        """
        工况平滑处理，避免频繁抖动

        Args:
            current_condition: 当前识别的工况
            current_probabilities: 当前各工况概率

        Returns:
            (平滑后的工况, 平滑后的概率, 是否为过渡态)
        """
        self._recent_conditions.append(current_condition)
        if len(self._recent_conditions) > self.smooth_window:
            self._recent_conditions.pop(0)

        if len(self._recent_conditions) < 3:
            return current_condition, current_probabilities, False

        condition_counts: Dict[WorkingCondition, int] = {}
        for cond in self._recent_conditions:
            condition_counts[cond] = condition_counts.get(cond, 0) + 1

        most_common = max(condition_counts, key=condition_counts.get)
        most_common_count = condition_counts[most_common]

        is_transition = most_common_count < len(self._recent_conditions) * 0.6

        if is_transition and len(condition_counts) >= 2:
            sorted_conditions = sorted(condition_counts.items(), key=lambda x: -x[1])
            transition_from = sorted_conditions[1][0]
            transition_to = sorted_conditions[0][0]
            return most_common, current_probabilities, True

        return most_common, current_probabilities, is_transition

    def classify(
        self,
        data: np.ndarray,
        historical_data: Optional[np.ndarray] = None,
        use_clustering: bool = False,
    ) -> ConditionClassificationResult:
        """
        工况分类主接口

        Args:
            data: 当前时间序列数据
            historical_data: 历史基准数据（可选）
            use_clustering: 是否使用聚类方法

        Returns:
            ConditionClassificationResult: 分类结果
        """
        features = self.extract_features(data)

        if use_clustering and self.is_fitted:
            condition, probabilities = self._cluster_based_classify(features)
        else:
            condition, probabilities = self._rule_based_classify(features, historical_data)

        smoothed_condition, smoothed_probs, is_transition = self._smooth_condition(
            condition, probabilities
        )

        confidence = smoothed_probs.get(smoothed_condition, 0.0)

        result = ConditionClassificationResult(
            condition=smoothed_condition,
            condition_label=WORKING_CONDITION_LABELS[smoothed_condition],
            confidence=float(confidence),
            probabilities=smoothed_probs,
            features={
                **features.statistical_features,
                **features.trend_features,
                **features.rate_features,
            },
            is_transition=is_transition,
        )

        return result

    def fit(self, data_segments: List[np.ndarray]) -> bool:
        """
        拟合聚类模型（无监督学习）

        Args:
            data_segments: 数据段列表，每个数据段代表一个连续的时间序列

        Returns:
            bool: 是否拟合成功
        """
        if len(data_segments) < self.min_clusters:
            logger.warning(f"数据段数量不足，至少需要 {self.min_clusters} 个")
            return False

        try:
            all_features = []
            for segment in data_segments:
                try:
                    features = self.extract_features(segment)
                    all_features.append(features.all_features)
                except Exception:
                    continue

            if len(all_features) < self.min_clusters:
                logger.warning("有效特征数量不足")
                return False

            all_features = np.array(all_features)

            self.scaler.fit(all_features)
            scaled_features = self.scaler.transform(all_features)

            # 自动确定最佳簇数
            best_k = self.min_clusters
            best_score = -1

            max_k = min(self.max_clusters, len(all_features) - 1)
            for k in range(self.min_clusters, max_k + 1):
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(scaled_features)
                score = silhouette_score(scaled_features, labels)

                if score > best_score:
                    best_score = score
                    best_k = k

            self.kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            self.kmeans.fit(scaled_features)

            self._map_clusters_to_conditions(scaled_features, all_features)

            self.is_fitted = True
            logger.info(f"工况聚类模型拟合完成，簇数={best_k}, 轮廓系数={best_score:.4f}")
            return True

        except Exception as e:
            logger.error(f"工况聚类模型拟合失败: {e}")
            return False

    def _map_clusters_to_conditions(
        self,
        scaled_features: np.ndarray,
        original_features: np.ndarray,
    ) -> None:
        """
        将簇映射到具体工况（基于质心特征）

        Args:
            scaled_features: 标准化后的特征
            original_features: 原始特征
        """
        if self.kmeans is None:
            return

        labels = self.kmeans.labels_
        n_clusters = self.kmeans.n_clusters

        cluster_stats = []
        for i in range(n_clusters):
            mask = labels == i
            cluster_data = original_features[mask]
            mean_features = np.mean(cluster_data, axis=0)

            slope_idx = list(self.condition_configs.keys()).__len__()
            cv_idx = 2

            cluster_stats.append({
                'cluster_id': i,
                'mean_cv': mean_features[cv_idx] if len(mean_features) > cv_idx else 0,
                'mean_slope': mean_features[12] if len(mean_features) > 12 else 0,
                'mean_value': mean_features[0] if len(mean_features) > 0 else 0,
                'increase_ratio': mean_features[18] if len(mean_features) > 18 else 0,
                'size': int(np.sum(mask)),
            })

        # 简单启发式映射
        for i, stats in enumerate(cluster_stats):
            slope = stats['mean_slope']
            cv = stats['mean_cv']

            if cv < 0.05 and abs(slope) < 0.01:
                condition = WorkingCondition.STEADY_STATE
            elif slope > 0.02:
                condition = WorkingCondition.LOAD_INCREASE
            elif slope < -0.02:
                condition = WorkingCondition.LOAD_DECREASE
            elif stats['mean_value'] < 0.3:
                condition = WorkingCondition.SHUTDOWN_COOLING
            else:
                condition = WorkingCondition.UNKNOWN

            self.cluster_to_condition[i] = condition

    def classify_segment(
        self,
        data: np.ndarray,
        window_size: int = 100,
        step_size: int = 50,
    ) -> List[ConditionClassificationResult]:
        """
        对长序列分段进行工况分类

        Args:
            data: 长序列数据
            window_size: 窗口大小
            step_size: 步长

        Returns:
            各窗口的分类结果列表
        """
        results = []
        n = len(data)

        for start in range(0, n - window_size + 1, step_size):
            segment = data[start:start + window_size]
            result = self.classify(segment)
            results.append(result)

        return results

    def detect_condition_changes(
        self,
        data: np.ndarray,
        window_size: int = 100,
        step_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        检测工况变更点

        Args:
            data: 时间序列数据
            window_size: 窗口大小
            step_size: 步长

        Returns:
            工况变更点列表
        """
        results = self.classify_segment(data, window_size, step_size)

        changes = []
        for i in range(1, len(results)):
            prev = results[i - 1]
            curr = results[i]

            if prev.condition != curr.condition:
                changes.append({
                    'index': i * step_size,
                    'from_condition': prev.condition.value,
                    'from_label': prev.condition_label,
                    'to_condition': curr.condition.value,
                    'to_label': curr.condition_label,
                    'confidence_change': curr.confidence - prev.confidence,
                })

        return changes

    def reset_smoothing(self) -> None:
        """
        重置平滑状态
        """
        self._recent_conditions = []
