"""
特征工程模块

负责从原始预紧力数据中提取用于模型训练的特征，包括:
1. 时序特征: 滑动窗口统计量、趋势特征、周期性特征
2. 统计特征: 分布特征、变化率特征、极值特征
3. 领域特征: 预紧力安全区间、历史故障模式

新增功能:
- 配置开关: feature_engineering.enabled: true/false
- 特征子集选择: temporal/statistical/domain
- 批量特征提取（训练用）
- 特征标准化（fit/transform）
- Permutation Importance 计算

使用示例:
    from app.services.feature_engineering import FeatureEngineer
    
    engineer = FeatureEngineer()
    features = engineer.extract_features(time_series_data)
"""

import numpy as np
import pandas as pd
import warnings
from typing import List, Tuple, Dict, Optional, Union, Any
from dataclasses import dataclass, field
from scipy import stats
from scipy.fft import fft
from scipy.signal import find_peaks
from loguru import logger
from sklearn.preprocessing import StandardScaler

from app.utils.config import config


@dataclass
class FeatureSet:
    """
    特征集合数据类

    Attributes:
        temporal_features: 时序特征
        statistical_features: 统计特征
        domain_features: 领域特征
        combined_features: 组合后的所有特征
        feature_names: 特征名称列表
        enabled_categories: 启用的特征类别
    """
    temporal_features: np.ndarray
    statistical_features: np.ndarray
    domain_features: np.ndarray
    combined_features: np.ndarray
    feature_names: List[str]
    enabled_categories: List[str] = field(default_factory=list)


@dataclass
class FeatureImportanceResult:
    """
    特征重要性计算结果

    Attributes:
        feature_names: 特征名称列表
        importances_mean: 平均重要性得分
        importances_std: 重要性标准差
        importances_raw: 每次打乱的重要性矩阵 (n_features, n_repeats)
        sorted_indices: 按重要性降序的索引
        method: 使用的方法 (permutation / shap)
    """
    feature_names: List[str]
    importances_mean: np.ndarray
    importances_std: np.ndarray
    importances_raw: Optional[np.ndarray] = None
    sorted_indices: Optional[np.ndarray] = None
    method: str = "permutation"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "feature_names": self.feature_names,
            "importances_mean": self.importances_mean.tolist(),
            "importances_std": self.importances_std.tolist(),
            "top_10_features": (
                [
                    {
                        "name": self.feature_names[i],
                        "importance": float(self.importances_mean[i]),
                        "rank": rank + 1,
                    }
                    for rank, i in enumerate(self.sorted_indices[:10])
                ]
                if self.sorted_indices is not None
                else []
            ),
        }


class FeatureEngineer:
    """
    特征工程师类

    从时间序列数据中提取多种类型的特征。

    Attributes:
        window_sizes: 滑动窗口大小列表
        preload_thresholds: 预紧力阈值配置
        enabled: 是否启用特征工程
        feature_categories: 启用的特征类别
        scaler: 特征标准化器（训练后保存，推理时使用）
    """

    DEFAULT_CATEGORIES = ["temporal", "statistical", "domain"]

    def __init__(
        self,
        enabled: Optional[bool] = None,
        feature_categories: Optional[List[str]] = None,
    ):
        """
        初始化特征工程师

        Args:
            enabled: 是否启用特征工程，None 则从配置读取
            feature_categories: 启用的特征类别，None 则从配置读取
        """
        self.window_sizes = [5, 10, 20, 50]
        self.preload_thresholds = config.get(
            "risk_assessment.preload_thresholds",
            {
                "min_normal": 400,
                "max_normal": 800,
                "warning_deviation": 0.1,
                "critical_deviation": 0.2,
            },
        )

        # 从配置读取开关
        fe_cfg = config.get("feature_engineering", {})
        if enabled is None:
            self.enabled = fe_cfg.get("enabled", True)
        else:
            self.enabled = enabled

        if feature_categories is None:
            cfg_cats = fe_cfg.get(
                "feature_categories", self.DEFAULT_CATEGORIES
            )
            self.feature_categories = [
                c for c in cfg_cats if c in self.DEFAULT_CATEGORIES
            ]
        else:
            self.feature_categories = [
                c for c in feature_categories if c in self.DEFAULT_CATEGORIES
            ]

        if not self.feature_categories:
            self.feature_categories = list(self.DEFAULT_CATEGORIES)

        # 标准化器（fit后持久化）
        self.scaler: Optional[StandardScaler] = None
        self._is_fitted = False

        # 保存上一次提取的特征名（用于 permutation importance）
        self._last_feature_names: Optional[List[str]] = None

        logger.info(
            f"特征工程师初始化完成: enabled={self.enabled}, "
            f"categories={self.feature_categories}"
        )

    # ============================================================
    # 特征提取：单条序列 → 单个特征向量
    # ============================================================

    def extract_temporal_features(
        self, data: np.ndarray, timestamps: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, List[str]]:
        """提取时序特征"""
        features = []
        feature_names = []

        for window in self.window_sizes:
            if len(data) >= window:
                rolling_mean = self._rolling_mean(data, window)
                features.append(rolling_mean[-1] if len(rolling_mean) > 0 else 0)
                feature_names.append(f"rolling_mean_{window}")

                rolling_std = self._rolling_std(data, window)
                features.append(rolling_std[-1] if len(rolling_std) > 0 else 0)
                feature_names.append(f"rolling_std_{window}")

                rolling_max = self._rolling_max(data, window)
                features.append(rolling_max[-1] if len(rolling_max) > 0 else 0)
                feature_names.append(f"rolling_max_{window}")

                rolling_min = self._rolling_min(data, window)
                features.append(rolling_min[-1] if len(rolling_min) > 0 else 0)
                feature_names.append(f"rolling_min_{window}")
            else:
                features.extend([0, 0, 0, 0])
                feature_names.extend(
                    [
                        f"rolling_mean_{window}",
                        f"rolling_std_{window}",
                        f"rolling_max_{window}",
                        f"rolling_min_{window}",
                    ]
                )

        slope, intercept = self._linear_trend(data)
        features.extend([slope, intercept])
        feature_names.extend(["trend_slope", "trend_intercept"])

        fft_features = self._fourier_features(data)
        features.extend(fft_features)
        feature_names.extend(
            [
                "fft_dominant_freq",
                "fft_dominant_amplitude",
                "fft_second_freq",
                "fft_second_amplitude",
            ]
        )

        autocorr_1 = self._autocorrelation(data, lag=1)
        autocorr_5 = self._autocorrelation(data, lag=5)
        features.extend([autocorr_1, autocorr_5])
        feature_names.extend(["autocorr_lag1", "autocorr_lag5"])

        return np.array(features, dtype=np.float32), feature_names

    def extract_statistical_features(
        self, data: np.ndarray
    ) -> Tuple[np.ndarray, List[str]]:
        """提取统计特征"""
        features = []
        feature_names = []

        features.append(np.mean(data))
        feature_names.append("mean")

        features.append(np.std(data))
        feature_names.append("std")

        features.append(np.median(data))
        feature_names.append("median")

        skewness = stats.skew(data) if len(data) > 2 else 0
        features.append(skewness)
        feature_names.append("skewness")

        kurtosis = stats.kurtosis(data) if len(data) > 3 else 0
        features.append(kurtosis)
        feature_names.append("kurtosis")

        features.append(np.max(data))
        feature_names.append("max_value")

        features.append(np.min(data))
        feature_names.append("min_value")

        features.append(np.max(data) - np.min(data))
        feature_names.append("range")

        if len(data) > 1:
            changes = np.diff(data)
            features.append(np.mean(np.abs(changes)))
            feature_names.append("mean_abs_change")

            features.append(np.std(changes))
            feature_names.append("change_std")

            features.append(np.max(changes))
            feature_names.append("max_increase")

            features.append(np.min(changes))
            feature_names.append("max_decrease")
        else:
            features.extend([0, 0, 0, 0])
            feature_names.extend(
                [
                    "mean_abs_change",
                    "change_std",
                    "max_increase",
                    "max_decrease",
                ]
            )

        features.append(np.percentile(data, 25))
        feature_names.append("q25")

        features.append(np.percentile(data, 75))
        feature_names.append("q75")

        features.append(np.percentile(data, 75) - np.percentile(data, 25))
        feature_names.append("iqr")

        # 零交叉率（模拟信号过零次数）
        if len(data) > 1:
            centered = data - np.mean(data)
            zero_crossings = np.sum(np.diff(np.sign(centered)) != 0)
            features.append(zero_crossings / len(data))
        else:
            features.append(0.0)
        feature_names.append("zero_crossing_rate")

        # 能量
        features.append(np.sum(data**2) / max(len(data), 1))
        feature_names.append("signal_energy")

        return np.array(features, dtype=np.float32), feature_names

    def extract_domain_features(
        self, data: np.ndarray
    ) -> Tuple[np.ndarray, List[str]]:
        """提取领域特征"""
        features = []
        feature_names = []

        min_normal = self.preload_thresholds.get("min_normal", 400)
        max_normal = self.preload_thresholds.get("max_normal", 800)
        warning_dev = self.preload_thresholds.get("warning_deviation", 0.1)
        critical_dev = self.preload_thresholds.get("critical_deviation", 0.2)

        mean_val = np.mean(data)

        if mean_val < min_normal:
            deviation_ratio = (min_normal - mean_val) / min_normal
        elif mean_val > max_normal:
            deviation_ratio = (mean_val - max_normal) / max_normal
        else:
            deviation_ratio = 0

        features.append(deviation_ratio)
        feature_names.append("safety_deviation_ratio")

        below_min_ratio = np.sum(data < min_normal) / max(len(data), 1)
        features.append(below_min_ratio)
        feature_names.append("below_min_ratio")

        above_max_ratio = np.sum(data > max_normal) / max(len(data), 1)
        features.append(above_max_ratio)
        feature_names.append("above_max_ratio")

        warning_min = min_normal * (1 - warning_dev)
        warning_max = max_normal * (1 + warning_dev)
        critical_min = min_normal * (1 - critical_dev)
        critical_max = max_normal * (1 + critical_dev)

        in_warning_zone = np.sum(
            ((data < min_normal) & (data >= warning_min))
            | ((data > max_normal) & (data <= warning_max))
        ) / max(len(data), 1)
        features.append(in_warning_zone)
        feature_names.append("warning_zone_ratio")

        in_critical_zone = np.sum(
            (data < critical_min) | (data > critical_max)
        ) / max(len(data), 1)
        features.append(in_critical_zone)
        feature_names.append("critical_zone_ratio")

        if len(data) > 1:
            changes = np.diff(data)
            sudden_drop = float(np.sum(changes < -mean_val * 0.5) > 0)
            features.append(sudden_drop)
        else:
            features.append(0)
        feature_names.append("has_sudden_drop")

        if len(data) >= 10:
            last_10 = data[-10:]
            slope, _ = self._linear_trend(last_10)
            features.append(slope)
        else:
            features.append(0)
        feature_names.append("recent_trend_slope")

        if len(data) >= 20:
            first_half_std = np.std(data[: len(data) // 2])
            second_half_std = np.std(data[len(data) // 2 :])
            volatility_increase = second_half_std / (first_half_std + 1e-6)
            features.append(volatility_increase)
        else:
            features.append(1.0)
        feature_names.append("volatility_increase")

        # 连续正常/异常持续时间
        if len(data) >= 1:
            below_count = self._count_consecutive(data < min_normal)
            features.append(float(below_count) / max(len(data), 1))
        else:
            features.append(0.0)
        feature_names.append("consecutive_below_ratio")

        # 恢复能力（从异常中回升的次数）
        if len(data) >= 3:
            recovery_count = 0
            for i in range(1, len(data) - 1):
                if data[i - 1] < min_normal and data[i + 1] > min_normal:
                    recovery_count += 1
            features.append(float(recovery_count))
        else:
            features.append(0.0)
        feature_names.append("recovery_count")

        # 相对变异系数
        cv = np.std(data) / (np.abs(np.mean(data)) + 1e-6)
        features.append(cv)
        feature_names.append("coefficient_of_variation")

        return np.array(features, dtype=np.float32), feature_names

    def extract_features(
        self, data: np.ndarray, timestamps: Optional[np.ndarray] = None
    ) -> FeatureSet:
        """
        提取所有特征（根据配置的类别）

        Args:
            data: 预紧力时间序列数据
            timestamps: 时间戳数组，可选

        Returns:
            FeatureSet: 完整的特征集合
        """
        if not self.enabled:
            empty = np.array([], dtype=np.float32)
            return FeatureSet(
                temporal_features=empty,
                statistical_features=empty,
                domain_features=empty,
                combined_features=empty,
                feature_names=[],
                enabled_categories=[],
            )

        temporal = stat = domain = empty = np.array([], dtype=np.float32)
        temporal_names = stat_names = domain_names = []
        enabled = []

        if "temporal" in self.feature_categories:
            temporal, temporal_names = self.extract_temporal_features(
                data, timestamps
            )
            enabled.append("temporal")
        if "statistical" in self.feature_categories:
            stat, stat_names = self.extract_statistical_features(data)
            enabled.append("statistical")
        if "domain" in self.feature_categories:
            domain, domain_names = self.extract_domain_features(data)
            enabled.append("domain")

        combined = np.concatenate([temporal, stat, domain])
        all_names = temporal_names + stat_names + domain_names
        self._last_feature_names = list(all_names)

        return FeatureSet(
            temporal_features=temporal,
            statistical_features=stat,
            domain_features=domain,
            combined_features=combined,
            feature_names=all_names,
            enabled_categories=enabled,
        )

    # ============================================================
    # 批量特征提取：整个长序列 → 每个滑动窗口提取一个特征向量
    # ============================================================

    def extract_batch_features(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        window_size: int = 100,
        step: int = 1,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        批量提取特征（用于训练数据集）

        对 data 的每个长度为 window_size 的滑动窗口提取特征，
        返回形状 (n_windows, n_features) 的矩阵。

        Args:
            data: 原始预紧力序列 (N,)
            timestamps: 时间戳 (N,)，可选
            window_size: 滑动窗口大小
            step: 滑动步长

        Returns:
            (特征矩阵 (n_windows, n_features), 特征名列表)
        """
        if not self.enabled:
            return np.zeros((0, 0), dtype=np.float32), []

        n = len(data)
        if n < window_size:
            fs = self.extract_features(data, timestamps)
            if fs.combined_features.size == 0:
                return np.zeros((0, 0), dtype=np.float32), []
            return fs.combined_features.reshape(1, -1), list(fs.feature_names)

        windows = []
        feature_names = None
        for start in range(0, n - window_size + 1, step):
            end = start + window_size
            ts_slice = timestamps[start:end] if timestamps is not None else None
            fs = self.extract_features(data[start:end], ts_slice)
            windows.append(fs.combined_features)
            if feature_names is None:
                feature_names = list(fs.feature_names)

        if not windows:
            return np.zeros((0, 0), dtype=np.float32), feature_names or []

        matrix = np.stack(windows, axis=0).astype(np.float32)
        return matrix, feature_names or []

    def fit_scaler(self, feature_matrix: np.ndarray) -> None:
        """
        拟合特征标准化器

        Args:
            feature_matrix: (n_samples, n_features)
        """
        if feature_matrix.size == 0:
            return
        self.scaler = StandardScaler()
        self.scaler.fit(feature_matrix)
        self._is_fitted = True

    def transform_features(self, features: np.ndarray) -> np.ndarray:
        """
        对特征向量/矩阵进行标准化

        Args:
            features: 单条向量 (n_features,) 或矩阵 (n, n_features)

        Returns:
            标准化后的特征
        """
        if not self._is_fitted or self.scaler is None:
            return features
        if features.size == 0:
            return features
        orig_shape = features.shape
        if features.ndim == 1:
            feats = features.reshape(1, -1)
        else:
            feats = features
        scaled = self.scaler.transform(feats).astype(np.float32)
        if features.ndim == 1:
            return scaled.ravel()
        return scaled.reshape(orig_shape)

    def fit_transform_batch(
        self, feature_matrix: np.ndarray
    ) -> np.ndarray:
        """拟合并转换批量特征"""
        self.fit_scaler(feature_matrix)
        return self.transform_features(feature_matrix)

    def get_scaler_state(self) -> Optional[Dict[str, np.ndarray]]:
        """获取标准化器状态，用于持久化。返回 None 表示未 fit。"""
        if not self._is_fitted or self.scaler is None:
            return None
        try:
            return {
                'mean_': self.scaler.mean_.copy(),
                'scale_': self.scaler.scale_.copy(),
                'var_': self.scaler.var_.copy(),
                'n_features_in_': np.array([self.scaler.n_features_in_]),
            }
        except Exception as e:
            logger.warning(f"获取 scaler 状态失败: {e}")
            return None

    def set_scaler_state(self, state: Optional[Dict[str, np.ndarray]]) -> bool:
        """从持久化状态恢复 StandardScaler（推理期不重新 fit 即可 transform。返回是否恢复成功。"""
        if state is None or 'mean_' not in state:
            self._is_fitted = False
            self.scaler = None
            return False
        try:
            n_feat = int(state['n_features_in_'][0]) if state['n_features_in_'].ndim > 0 else len(state['mean_'].shape[0])
            self.scaler = StandardScaler()
            self.scaler.mean_ = state['mean_'].astype(np.float64).copy()
            self.scaler.scale_ = state['scale_'].astype(np.float64).copy()
            self.scaler.var_ = state['var_'].astype(np.float64).copy()
            self.scaler.n_features_in_ = n_feat
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                try:
                    self.scaler.feature_names_in_ = None
                except Exception:
                    pass
            self._is_fitted = True
            return True
        except Exception as e:
            logger.warning(f"恢复 scaler 状态失败: {e}")
            self._is_fitted = False
            return False

    # ============================================================
    # 特征重要性计算（Permutation Importance）
    # ============================================================

    def compute_permutation_importance(
        self,
        model_predict_fn,
        X_sequences: np.ndarray,
        feature_matrix: np.ndarray,
        y_true: np.ndarray,
        feature_names: Optional[List[str]] = None,
        n_repeats: int = 10,
        random_state: int = 42,
    ) -> FeatureImportanceResult:
        """
        使用 Permutation Importance 计算特征重要性

        通过随机打乱每个特征的值，观察模型性能下降的程度来衡量特征重要性。

        Args:
            model_predict_fn: 预测函数，签名: (sequences, features) -> 类别预测 (n_samples,)
            X_sequences: 序列输入 (n_samples, seq_len, input_dim)
            feature_matrix: 特征矩阵 (n_samples, n_features)
            y_true: 真实标签 (n_samples,)
            feature_names: 特征名列表，默认使用内部保存的名称
            n_repeats: 重复打乱次数
            random_state: 随机种子

        Returns:
            FeatureImportanceResult
        """
        if feature_matrix.size == 0:
            empty = np.array([], dtype=np.float32)
            return FeatureImportanceResult(
                feature_names=feature_names or [],
                importances_mean=empty,
                importances_std=empty,
                importances_raw=empty.reshape(0, n_repeats)
                if feature_names
                else empty,
                sorted_indices=None,
                method="permutation",
            )

        rng = np.random.RandomState(random_state)
        n_features = feature_matrix.shape[1]
        names = feature_names or self._last_feature_names or [
            f"f{i}" for i in range(n_features)
        ]

        # 基准准确率
        baseline_preds = model_predict_fn(X_sequences, feature_matrix)
        baseline_acc = np.mean(baseline_preds == y_true)

        importances_raw = np.zeros((n_features, n_repeats), dtype=np.float32)

        for feat_idx in range(n_features):
            for rep in range(n_repeats):
                shuffled_feats = feature_matrix.copy()
                rng.shuffle(shuffled_feats[:, feat_idx])
                shuffled_preds = model_predict_fn(X_sequences, shuffled_feats)
                shuffled_acc = np.mean(shuffled_preds == y_true)
                importances_raw[feat_idx, rep] = baseline_acc - shuffled_acc

        importances_mean = np.mean(importances_raw, axis=1)
        importances_std = np.std(importances_raw, axis=1)
        sorted_indices = np.argsort(importances_mean)[::-1]

        result = FeatureImportanceResult(
            feature_names=list(names),
            importances_mean=importances_mean,
            importances_std=importances_std,
            importances_raw=importances_raw,
            sorted_indices=sorted_indices,
            method="permutation",
        )

        logger.info(
            f"Permutation Importance 完成: n_features={n_features}, "
            f"top_feature={names[sorted_indices[0]] if len(sorted_indices) > 0 else 'N/A'} "
            f"({importances_mean[sorted_indices[0]]:.4f})"
            if len(sorted_indices) > 0
            else "N/A"
        )

        return result

    def compute_permutation_importance_from_windows(
        self,
        model_predict_fn,
        raw_sequences: np.ndarray,
        y_true: np.ndarray,
        seq_length: int = 100,
        n_repeats: int = 10,
        random_state: int = 42,
    ) -> FeatureImportanceResult:
        """
        从原始窗口数据自动提取特征并计算 Permutation Importance

        Args:
            model_predict_fn: 预测函数 (sequences, features) -> classes
            raw_sequences: 窗口序列 (n_samples,) 或 (n_samples, seq_len)
            y_true: 标签 (n_samples,)
            seq_length: 序列长度
            n_repeats: 重复次数
            random_state: 随机种子

        Returns:
            FeatureImportanceResult
        """
        if raw_sequences.ndim == 1:
            feats, names = self.extract_batch_features(
                raw_sequences, window_size=seq_length, step=1
            )
            # prepare sequences in LSTM format
            if len(raw_sequences) >= seq_length:
                X_seq = self._prepare_sequences_for_model(
                    raw_sequences, seq_length
                )
                y = y_true[-len(X_seq) :]
                feats = feats[-len(X_seq) :]
            else:
                X_seq = self._prepare_sequences_for_model(
                    raw_sequences, seq_length
                )
                y = y_true
        else:
            feats_list = []
            X_seq_parts = []
            names = None
            for i in range(raw_sequences.shape[0]):
                fs = self.extract_features(raw_sequences[i])
                feats_list.append(fs.combined_features)
                if names is None:
                    names = list(fs.feature_names)
                X_seq_parts.append(
                    self._prepare_sequences_for_model(
                        raw_sequences[i], seq_length
                    )[0]
                )
            feats = np.stack(feats_list, axis=0) if feats_list else np.array([])
            X_seq = (
                np.stack(X_seq_parts, axis=0) if X_seq_parts else np.array([])
            )
            y = y_true

        return self.compute_permutation_importance(
            model_predict_fn=model_predict_fn,
            X_sequences=X_seq,
            feature_matrix=feats,
            y_true=y,
            feature_names=names,
            n_repeats=n_repeats,
            random_state=random_state,
        )

    # ============================================================
    # 内部工具
    # ============================================================

    def _prepare_sequences_for_model(
        self, data: np.ndarray, sequence_length: int
    ) -> np.ndarray:
        """为 LSTM 准备序列输入（与 bolt_lstm prepare_data 对齐）"""
        if data.ndim == 1:
            n = len(data)
            time_index = np.arange(n) / max(n, 1)
            data_2d = np.column_stack([data, time_index])
        else:
            data_2d = data

        n_samples = len(data_2d) - sequence_length + 1
        if n_samples <= 0:
            padded = np.zeros((sequence_length, data_2d.shape[1]), dtype=np.float32)
            padded[-len(data_2d) :] = data_2d
            return padded.reshape(1, sequence_length, -1)

        seqs = np.zeros(
            (n_samples, sequence_length, data_2d.shape[1]), dtype=np.float32
        )
        for i in range(n_samples):
            seqs[i] = data_2d[i : i + sequence_length]
        return seqs

    @staticmethod
    def _count_consecutive(mask: np.ndarray) -> int:
        """计算最长连续 True 段的长度"""
        if mask.size == 0:
            return 0
        max_len = cur = 0
        for v in mask:
            if v:
                cur += 1
                max_len = max(max_len, cur)
            else:
                cur = 0
        return max_len

    def _rolling_mean(self, data: np.ndarray, window: int) -> np.ndarray:
        if len(data) < window:
            return np.array([np.mean(data)])
        return np.convolve(data, np.ones(window) / window, mode="valid")

    def _rolling_std(self, data: np.ndarray, window: int) -> np.ndarray:
        if len(data) < window:
            return np.array([np.std(data)])
        result = []
        for i in range(len(data) - window + 1):
            result.append(np.std(data[i : i + window]))
        return np.array(result)

    def _rolling_max(self, data: np.ndarray, window: int) -> np.ndarray:
        if len(data) < window:
            return np.array([np.max(data)])
        result = []
        for i in range(len(data) - window + 1):
            result.append(np.max(data[i : i + window]))
        return np.array(result)

    def _rolling_min(self, data: np.ndarray, window: int) -> np.ndarray:
        if len(data) < window:
            return np.array([np.min(data)])
        result = []
        for i in range(len(data) - window + 1):
            result.append(np.min(data[i : i + window]))
        return np.array(result)

    def _linear_trend(self, data: np.ndarray) -> Tuple[float, float]:
        if len(data) < 2:
            return 0.0, 0.0
        x = np.arange(len(data))
        coefficients = np.polyfit(x, data, 1)
        return coefficients[0], coefficients[1]

    def _fourier_features(self, data: np.ndarray, top_k: int = 2) -> List[float]:
        if len(data) < 4:
            return [0.0] * (top_k * 2)

        fft_result = np.abs(fft(data))
        n = len(fft_result)
        half_n = n // 2
        magnitudes = fft_result[1:half_n]
        frequencies = np.arange(1, half_n) / n

        if len(magnitudes) == 0:
            return [0.0] * (top_k * 2)

        top_indices = np.argsort(magnitudes)[-top_k:][::-1]

        features = []
        for idx in top_indices:
            features.append(frequencies[idx])
            features.append(magnitudes[idx])

        while len(features) < top_k * 2:
            features.extend([0.0, 0.0])

        return features[: top_k * 2]

    def _autocorrelation(self, data: np.ndarray, lag: int = 1) -> float:
        if len(data) <= lag:
            return 0.0

        n = len(data)
        mean = np.mean(data)
        var = np.var(data)

        if var == 0:
            return 0.0

        autocorr = (
            np.sum((data[:-lag] - mean) * (data[lag:] - mean))
            / ((n - lag) * var)
        )
        return autocorr
