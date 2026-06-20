"""
模型漂移检测核心算法模块

实现以下漂移检测维度:
1. 数据分布漂移 (PSI / KS检验)
2. 预测置信度分布漂移
3. 误报率上升检测
4. 特征均值偏移检测
5. 综合漂移分数计算
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger


class DriftDimension(str, Enum):
    """漂移检测维度枚举"""

    DATA_PSI = "psi"
    DATA_KS = "ks"
    CONFIDENCE = "confidence"
    FALSE_POSITIVE = "false_positive"
    FEATURE_SHIFT = "feature_shift"


@dataclass
class DriftResult:
    """单维度漂移检测结果"""

    dimension: DriftDimension
    score: float = 0.0
    is_drifted: bool = False
    threshold: Optional[float] = None
    details: Dict = field(default_factory=dict)


@dataclass
class CompositeDriftResult:
    """综合漂移检测结果"""

    dimensions: Dict[DriftDimension, DriftResult] = field(default_factory=dict)
    composite_score: float = 0.0
    drift_level: str = "none"
    triggered_dims: List[str] = field(default_factory=list)

    def add(self, result: DriftResult) -> None:
        """添加单维度检测结果"""
        self.dimensions[result.dimension] = result
        if result.is_drifted:
            self.triggered_dims.append(result.dimension.value)


def _check_min_samples(expected: np.ndarray, actual: np.ndarray, min_samples: int = 30) -> bool:
    """检查样本量是否足够"""
    if len(expected) < min_samples or len(actual) < min_samples:
        logger.warning(
            f"样本量不足: expected={len(expected)}, actual={len(actual)}, 最小需要={min_samples}"
        )
        return False
    return True


def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    buckets: int = 10,
    epsilon: float = 1e-6,
) -> DriftResult:
    """
    计算 PSI (Population Stability Index)

    PSI = Σ((Actual% - Expected%) * ln(Actual% / Expected%))

    PSI 值参考:
    - < 0.1: 无显著漂移
    - 0.1 ~ 0.25: 轻度漂移，需关注
    - > 0.25: 显著漂移，需要行动

    Args:
        expected: 基准分布样本（训练数据）
        actual: 当前分布样本（生产数据）
        buckets: 分箱数量
        epsilon: 防止除零的极小值

    Returns:
        DriftResult: PSI检测结果
    """
    if not _check_min_samples(expected, actual):
        return DriftResult(
            dimension=DriftDimension.DATA_PSI,
            score=0.0,
            is_drifted=False,
            details={"error": "insufficient_samples", "expected_len": len(expected), "actual_len": len(actual)},
        )

    expected = np.asarray(expected, dtype=np.float64).flatten()
    actual = np.asarray(actual, dtype=np.float64).flatten()

    expected_clean = expected[~np.isnan(expected)]
    actual_clean = actual[~np.isnan(actual)]

    if len(expected_clean) < 10 or len(actual_clean) < 10:
        return DriftResult(
            dimension=DriftDimension.DATA_PSI,
            score=0.0,
            is_drifted=False,
            details={"error": "too_few_valid_samples"},
        )

    breakpoints = np.linspace(0, 100, buckets + 1)
    percentiles = np.percentile(expected_clean, breakpoints)
    percentiles = np.unique(percentiles)
    if len(percentiles) < 3:
        percentiles = np.array([expected_clean.min(), expected_clean.max()])

    expected_counts = np.histogram(expected_clean, bins=percentiles)[0]
    actual_counts = np.histogram(actual_clean, bins=percentiles)[0]

    expected_ratio = expected_counts / len(expected_clean)
    actual_ratio = actual_counts / len(actual_clean)

    expected_ratio = np.clip(expected_ratio, epsilon, 1.0)
    actual_ratio = np.clip(actual_ratio, epsilon, 1.0)

    psi_values = (actual_ratio - expected_ratio) * np.log(actual_ratio / expected_ratio)
    psi_score = float(np.sum(psi_values))

    is_drifted = psi_score > 0.25

    return DriftResult(
        dimension=DriftDimension.DATA_PSI,
        score=psi_score,
        is_drifted=is_drifted,
        threshold=0.25,
        details={
            "expected_ratio": expected_ratio.tolist(),
            "actual_ratio": actual_ratio.tolist(),
            "breakpoints": percentiles.tolist(),
            "expected_samples": len(expected_clean),
            "actual_samples": len(actual_clean),
        },
    )


def calculate_ks_test(
    expected: np.ndarray,
    actual: np.ndarray,
) -> DriftResult:
    """
    计算 KS (Kolmogorov-Smirnov) 检验

    KS检验用于判断两个样本是否来自同一分布。
    - p值 < 0.05: 拒绝同分布假设，存在漂移
    - KS统计量: 两个累积分布函数的最大距离

    Args:
        expected: 基准分布样本
        actual: 当前分布样本

    Returns:
        DriftResult: KS检测结果
    """
    if not _check_min_samples(expected, actual):
        return DriftResult(
            dimension=DriftDimension.DATA_KS,
            score=0.0,
            is_drifted=False,
            details={"error": "insufficient_samples"},
        )

    expected = np.asarray(expected, dtype=np.float64).flatten()
    actual = np.asarray(actual, dtype=np.float64).flatten()

    expected_clean = expected[~np.isnan(expected)]
    actual_clean = actual[~np.isnan(actual)]

    if len(expected_clean) < 5 or len(actual_clean) < 5:
        return DriftResult(
            dimension=DriftDimension.DATA_KS,
            score=0.0,
            is_drifted=False,
            details={"error": "too_few_valid_samples"},
        )

    try:
        from scipy import stats as scipy_stats

        ks_stat, p_value = scipy_stats.ks_2samp(expected_clean, actual_clean)
        ks_stat = float(ks_stat)
        p_value = float(p_value)
    except ImportError:
        logger.warning("scipy未安装，使用简化版KS检验")
        ks_stat, p_value = _ks_2samp_simple(expected_clean, actual_clean)

    is_drifted = p_value < 0.05

    return DriftResult(
        dimension=DriftDimension.DATA_KS,
        score=ks_stat,
        is_drifted=is_drifted,
        threshold=0.05,
        details={
            "ks_statistic": ks_stat,
            "p_value": p_value,
            "expected_samples": len(expected_clean),
            "actual_samples": len(actual_clean),
        },
    )


def _ks_2samp_simple(data1: np.ndarray, data2: np.ndarray) -> Tuple[float, float]:
    """简化版KS检验（无需scipy）"""
    n1, n2 = len(data1), len(data2)
    all_data = np.concatenate([data1, data2])
    sorted_data = np.sort(all_data)

    cdf1 = np.searchsorted(np.sort(data1), sorted_data, side="right") / n1
    cdf2 = np.searchsorted(np.sort(data2), sorted_data, side="right") / n2

    d = float(np.max(np.abs(cdf1 - cdf2)))

    en = math.sqrt(n1 * n2 / (n1 + n2))
    lam = (en + 0.12 + 0.11 / en) * d
    p_value = 2.0 * math.exp(-2.0 * lam * lam) if lam > 0 else 1.0
    p_value = max(0.0, min(1.0, p_value))

    return d, p_value


def calculate_confidence_drift(
    baseline_confidences: np.ndarray,
    current_confidences: np.ndarray,
) -> DriftResult:
    """
    检测预测置信度分布漂移

    使用KS检验比较基线置信度分布和当前置信度分布。
    如果分布发生显著变化，可能意味着模型遇到了OOD样本或数据分布变化。

    Args:
        baseline_confidences: 基线置信度分数 [0, 1]
        current_confidences: 当前置信度分数 [0, 1]

    Returns:
        DriftResult: 置信度分布漂移检测结果
    """
    ks_result = calculate_ks_test(baseline_confidences, current_confidences)

    score = ks_result.score
    details = ks_result.details
    p_value = details.get("p_value", 1.0)
    is_drifted = p_value < 0.05 or score > 0.15

    return DriftResult(
        dimension=DriftDimension.CONFIDENCE,
        score=score,
        is_drifted=is_drifted,
        threshold=0.15,
        details={
            **details,
            "baseline_mean": float(np.nanmean(baseline_confidences)) if len(baseline_confidences) > 0 else None,
            "current_mean": float(np.nanmean(current_confidences)) if len(current_confidences) > 0 else None,
            "baseline_std": float(np.nanstd(baseline_confidences)) if len(baseline_confidences) > 0 else None,
            "current_std": float(np.nanstd(current_confidences)) if len(current_confidences) > 0 else None,
        },
    )


def calculate_false_positive_rate(
    total_predictions: int,
    false_positive_count: int,
    baseline_fpr: float = 0.05,
    window_days: int = 7,
) -> DriftResult:
    """
    检测误报率是否显著上升

    使用二项分布检验当前误报率是否显著高于基线误报率。

    Args:
        total_predictions: 窗口期内总预测数
        false_positive_count: 窗口期内误报数
        baseline_fpr: 基线误报率
        window_days: 统计窗口天数

    Returns:
        DriftResult: 误报率检测结果
    """
    if total_predictions <= 0:
        return DriftResult(
            dimension=DriftDimension.FALSE_POSITIVE,
            score=0.0,
            is_drifted=False,
            details={"error": "no_predictions"},
        )

    current_fpr = false_positive_count / total_predictions

    try:
        from scipy import stats as scipy_stats

        expected_fp = total_predictions * baseline_fpr
        var_fp = total_predictions * baseline_fpr * (1 - baseline_fpr)

        if var_fp > 0:
            z_score = (false_positive_count - expected_fp) / math.sqrt(var_fp)
            p_value = float(1.0 - scipy_stats.norm.cdf(z_score))
        else:
            z_score = 0.0
            p_value = 1.0 if current_fpr <= baseline_fpr else 0.0
    except ImportError:
        ratio = current_fpr / baseline_fpr if baseline_fpr > 0 else float("inf")
        z_score = ratio - 1.0
        p_value = 0.0 if ratio > 2.0 else 1.0

    is_drifted = p_value < 0.05 and current_fpr > baseline_fpr
    score = current_fpr

    return DriftResult(
        dimension=DriftDimension.FALSE_POSITIVE,
        score=score,
        is_drifted=is_drifted,
        threshold=baseline_fpr,
        details={
            "total_predictions": total_predictions,
            "false_positive_count": false_positive_count,
            "current_fpr": current_fpr,
            "baseline_fpr": baseline_fpr,
            "z_score": float(z_score),
            "p_value": float(p_value),
            "window_days": window_days,
        },
    )


def calculate_feature_mean_shift(
    baseline_stats: Dict[str, Dict[str, float]],
    current_stats: Dict[str, Dict[str, float]],
    std_threshold: float = 2.0,
) -> Tuple[DriftResult, Dict[str, Dict]]:
    """
    检测特征均值偏移

    比较每个特征的当前均值与基线均值，以基线标准差为单位。
    如果偏移超过 std_threshold 个标准差，则判定该特征发生漂移。

    Args:
        baseline_stats: 基线特征统计 {feature_name: {"mean": x, "std": y}}
        current_stats: 当前特征统计 {feature_name: {"mean": x, "std": y}}
        std_threshold: 标准差倍数阈值

    Returns:
        Tuple[DriftResult, Dict]: (综合漂移结果, 各特征详情)
    """
    feature_details = {}
    shifted_features = []
    z_scores = []

    common_features = set(baseline_stats.keys()) & set(current_stats.keys())

    for feat in common_features:
        base = baseline_stats.get(feat, {})
        curr = current_stats.get(feat, {})
        base_mean = base.get("mean")
        base_std = base.get("std", 0.0) or 0.0
        curr_mean = curr.get("mean")

        if base_mean is None or curr_mean is None:
            continue

        if base_std <= 0 or math.isnan(base_std) or math.isclose(base_std, 0):
            z_score = 0.0
            is_shifted = False
        else:
            z_score = (curr_mean - base_mean) / base_std
            is_shifted = abs(z_score) > std_threshold

        z_scores.append(abs(z_score))
        if is_shifted:
            shifted_features.append(feat)

        feature_details[feat] = {
            "baseline_mean": base_mean,
            "baseline_std": base_std,
            "current_mean": curr_mean,
            "current_std": curr.get("std"),
            "z_score": float(z_score),
            "is_shifted": is_shifted,
        }

    total_features = len(common_features)
    shifted_count = len(shifted_features)
    if total_features > 0:
        shift_ratio = shifted_count / total_features
    else:
        shift_ratio = 0.0

    avg_z_score = float(np.mean(z_scores)) if z_scores else 0.0
    score = max(avg_z_score, shift_ratio)

    is_drifted = shifted_count > 0 and (shift_ratio > 0.2 or avg_z_score > std_threshold)

    result = DriftResult(
        dimension=DriftDimension.FEATURE_SHIFT,
        score=score,
        is_drifted=is_drifted,
        threshold=std_threshold,
        details={
            "total_features": total_features,
            "shifted_count": shifted_count,
            "shift_ratio": shift_ratio,
            "avg_z_score": avg_z_score,
            "shifted_features": shifted_features,
        },
    )

    return result, feature_details


def compute_composite_drift_score(
    results: Dict[DriftDimension, DriftResult],
    weights: Optional[Dict[DriftDimension, float]] = None,
) -> CompositeDriftResult:
    """
    计算综合漂移分数

    根据各维度权重计算加权平均的综合漂移分数，
    并给出漂移等级评定。

    Args:
        results: 各维度的检测结果
        weights: 各维度权重 {DriftDimension: weight}

    Returns:
        CompositeDriftResult: 综合结果
    """
    default_weights = {
        DriftDimension.DATA_PSI: 0.25,
        DriftDimension.DATA_KS: 0.20,
        DriftDimension.CONFIDENCE: 0.25,
        DriftDimension.FALSE_POSITIVE: 0.20,
        DriftDimension.FEATURE_SHIFT: 0.10,
    }

    if weights is None:
        weights = default_weights
    else:
        for dim in default_weights:
            if dim not in weights:
                weights[dim] = default_weights[dim]

    composite = CompositeDriftResult(dimensions=results)

    total_weight = 0.0
    weighted_score = 0.0

    for dim, result in results.items():
        composite.add(result)
        weight = weights.get(dim, 0.0)

        normalized = _normalize_dimension_score(dim, result.score, result.is_drifted)
        weighted_score += normalized * weight
        total_weight += weight

    if total_weight > 0:
        composite.composite_score = weighted_score / total_weight
    else:
        composite.composite_score = 0.0

    composite.drift_level = _classify_drift_level(composite.composite_score, len(composite.triggered_dims))

    return composite


def _normalize_dimension_score(dim: DriftDimension, raw_score: float, is_drifted: bool) -> float:
    """将各维度分数归一化到 [0, 1] 区间"""
    if dim == DriftDimension.DATA_PSI:
        return min(1.0, raw_score / 0.5)
    elif dim == DriftDimension.DATA_KS:
        return min(1.0, raw_score * 2.0)
    elif dim == DriftDimension.CONFIDENCE:
        return min(1.0, raw_score * 3.0)
    elif dim == DriftDimension.FALSE_POSITIVE:
        return min(1.0, raw_score * 5.0)
    elif dim == DriftDimension.FEATURE_SHIFT:
        return min(1.0, raw_score)
    else:
        return 1.0 if is_drifted else 0.0


def _classify_drift_level(score: float, triggered_count: int) -> str:
    """根据综合分数和触发维度数判断漂移等级"""
    if score < 0.15 and triggered_count == 0:
        return "none"
    elif score < 0.3 or triggered_count <= 1:
        return "low"
    elif score < 0.5 or triggered_count <= 2:
        return "medium"
    elif score < 0.75 or triggered_count <= 3:
        return "high"
    else:
        return "critical"
