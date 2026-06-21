"""
数据预处理模块

负责对原始预紧力数据进行清洗和预处理，包括:
1. 数据标准化/归一化
2. 孤立森林异常检测
3. 时间序列插值
4. 卡尔曼滤波平滑

使用示例:
    from app.services.preprocessing import DataPreprocessor
    
    preprocessor = DataPreprocessor()
    processed_data = preprocessor.process(raw_data)
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass, field
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import IsolationForest
from scipy import interpolate
from loguru import logger

from app.utils.config import config
from app.services.kalman_filter import (
    KalmanFilterFactory,
    KalmanDiagnostics,
    StreamingKalmanManager,
    KalmanStreamingState,
)


@dataclass
class PreprocessingResult:
    """
    预处理结果数据类
    
    Attributes:
        data: 处理后的数据
        anomalies: 检测到的异常数据
        anomaly_indices: 异常数据的索引
        interpolated_count: 插值填充的数据点数量
        scaler: 使用的缩放器（用于逆变换）
        kalman_diagnostics: 卡尔曼滤波诊断信息（增益、新息、误差协方差等）
        kalman_mode: 使用的滤波模式 simple/adaptive/extended
    """
    data: np.ndarray
    anomalies: Optional[np.ndarray] = None
    anomaly_indices: Optional[List[int]] = None
    interpolated_count: int = 0
    scaler: Optional[Any] = None
    kalman_diagnostics: Optional[KalmanDiagnostics] = None
    kalman_mode: Optional[str] = None


# 兼容旧引用：内部委托给高级 KalmanFilterFactory
class KalmanFilter:
    """
    兼容旧接口的卡尔曼滤波器（内部委托给 SimpleKalmanFilter）
    """

    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 0.1):
        from app.services.kalman_filter import SimpleKalmanFilter
        self._impl = SimpleKalmanFilter(
            process_noise=process_noise,
            measurement_noise=measurement_noise,
        )
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.estimate = 0.0
        self.estimate_error = 1.0

    def reset(self, initial_value: float = 0.0) -> None:
        self._impl.reset(initial_value)
        self.estimate = initial_value
        self.estimate_error = self._impl.initial_P

    def update(self, measurement: float) -> float:
        state = self._impl.update(float(measurement))
        self.estimate = state.estimate
        self.estimate_error = state.error_covariance
        return state.estimate

    def filter(self, data: np.ndarray) -> np.ndarray:
        if len(data) == 0:
            return data
        self._impl.reset()
        result = self._impl.filter(data, collect_diagnostics=False)
        self.estimate = float(result.estimates[-1]) if len(result.estimates) > 0 else 0.0
        self.estimate_error = float(result.error_covariances[-1]) if len(result.error_covariances) > 0 else 1.0
        return result.smoothed_data


class DataPreprocessor:
    """
    数据预处理器

    集成了多种数据预处理方法，提供完整的数据清洗流程。
    高级特性：
    - 卡尔曼滤波三种模式：simple / adaptive / extended
    - per-sensor 参数覆盖（高噪声传感器单独配置）
    - kalman_diagnostics 诊断输出（增益、新息、误差协方差）
    - 流式增量处理（与 StreamingKalmanManager / SlidingWindowManager 配合）

    Attributes:
        config: 预处理配置
        scaler: 数据缩放器
        isolation_forest: 孤立森林模型
        kalman_factory: 卡尔曼滤波器工厂
        streaming_kalman: 流式增量卡尔曼管理器
    """

    def __init__(self):
        self.config = config.get("preprocessing", {})
        self._init_components()

    def _init_components(self) -> None:
        norm_method = self.config.get("normalization", {}).get("method", "minmax")
        self.scaler = StandardScaler() if norm_method == "zscore" else MinMaxScaler()

        iso_config = self.config.get("isolation_forest", {})
        self.isolation_forest = IsolationForest(
            contamination=iso_config.get("contamination", 0.1),
            n_estimators=iso_config.get("n_estimators", 100),
            random_state=iso_config.get("random_state", 42),
            n_jobs=-1,
        )

        self.kalman_factory = KalmanFilterFactory()
        self.streaming_kalman = StreamingKalmanManager(self.kalman_factory)

        kalman_config = self.config.get("kalman_filter", {})
        self.kalman_filter = KalmanFilter(
            process_noise=kalman_config.get("process_noise", 0.01),
            measurement_noise=kalman_config.get("measurement_noise", 0.1),
        )

        logger.info("数据预处理器初始化完成（高级卡尔曼模式已启用）")
    
    def normalize(self, data: np.ndarray, fit: bool = True) -> np.ndarray:
        """
        对数据进行标准化/归一化
        
        Args:
            data: 输入数据，形状为 (n_samples, n_features) 或 (n_samples,)
            fit: 是否拟合缩放器，True表示训练时使用，False表示推理时使用
            
        Returns:
            np.ndarray: 归一化后的数据
        """
        # 确保数据是2D的
        original_shape = data.shape
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        if fit:
            normalized = self.scaler.fit_transform(data)
        else:
            normalized = self.scaler.transform(data)
        
        # 恢复原始形状
        if len(original_shape) == 1:
            normalized = normalized.ravel()
        
        return normalized
    
    def denormalize(self, data: np.ndarray) -> np.ndarray:
        """
        对数据进行逆归一化
        
        Args:
            data: 归一化后的数据
            
        Returns:
            np.ndarray: 原始尺度的数据
        """
        original_shape = data.shape
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        denormalized = self.scaler.inverse_transform(data)
        
        if len(original_shape) == 1:
            denormalized = denormalized.ravel()
        
        return denormalized
    
    def detect_anomalies(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[int]]:
        """
        使用孤立森林检测异常值
        
        Args:
            data: 输入数据，形状为 (n_samples, n_features) 或 (n_samples,)
            
        Returns:
            Tuple: (正常数据, 异常数据, 异常索引)
        """
        original_shape = data.shape
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        # 训练并预测
        predictions = self.isolation_forest.fit_predict(data)
        anomaly_scores = self.isolation_forest.score_samples(data)
        
        # 分离正常和异常数据
        normal_mask = predictions == 1
        anomaly_mask = predictions == -1
        
        normal_data = data[normal_mask]
        anomaly_data = data[anomaly_mask]
        anomaly_indices = np.where(anomaly_mask)[0].tolist()
        anomaly_scores_list = anomaly_scores[anomaly_mask].tolist()
        
        self._last_anomaly_scores = anomaly_scores_list
        
        logger.info(f"异常检测完成: 总数据 {len(data)}, 异常数据 {len(anomaly_indices)}")
        
        # 恢复原始形状
        if len(original_shape) == 1:
            normal_data = normal_data.ravel()
            anomaly_data = anomaly_data.ravel()
        
        return normal_data, anomaly_data, anomaly_indices
    
    def store_anomalies_to_db(
        self,
        sensor_id: str,
        anomalies: np.ndarray,
        anomaly_indices: List[int],
        timestamps: Optional[np.ndarray] = None,
    ) -> int:
        """
        将检测到的异常数据写入 sc_anomaly_data 表
        
        Args:
            sensor_id: 传感器/螺栓ID
            anomalies: 异常数据数组
            anomaly_indices: 异常数据的原始索引
            timestamps: 时间戳数组（可选）
            
        Returns:
            int: 成功写入的异常数量
        """
        if anomalies is None or len(anomalies) == 0:
            return 0

        try:
            import json
            from app.utils.database import get_db, AnomalyData

            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，跳过异常数据存储")
                    return 0

                count = 0
                for i, (idx, value) in enumerate(zip(anomaly_indices, anomalies)):
                    original_time = None
                    if timestamps is not None and idx < len(timestamps):
                        original_time = timestamps[idx]
                        if hasattr(original_time, 'to_pydatetime'):
                            original_time = original_time.to_pydatetime()
                        elif isinstance(original_time, np.datetime64):
                            original_time = pd.Timestamp(original_time).to_pydatetime()

                    score = 0.0
                    if hasattr(self, '_last_anomaly_scores') and self._last_anomaly_scores:
                        if i < len(self._last_anomaly_scores):
                            score = float(self._last_anomaly_scores[i])

                    details = {
                        "method": "isolation_forest",
                        "original_index": idx,
                        "preprocessing_stage": True,
                    }

                    anomaly_record = AnomalyData(
                        sensor_id=sensor_id,
                        anomaly_value=float(value),
                        anomaly_type="isolation_forest",
                        anomaly_score=score,
                        original_time=original_time,
                        details=json.dumps(details, ensure_ascii=False),
                    )
                    db.add(anomaly_record)
                    count += 1

                db.commit()
                logger.info(
                    f"预处理阶段异常写入数据库: sensor_id={sensor_id}, "
                    f"数量={count}"
                )
                return count

        except Exception as e:
            logger.error(f"预处理阶段异常写入数据库失败: {e}")
            return 0
    
    def interpolate_missing(
        self, 
        data: np.ndarray, 
        timestamps: np.ndarray,
        method: str = 'linear'
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        基于时间序列对缺失数据进行插值
        
        Args:
            data: 预紧力数据数组
            timestamps: 时间戳数组
            method: 插值方法 ('linear', 'cubic', 'nearest')
            
        Returns:
            Tuple: (插值后的数据, 新时间戳, 插值数量)
        """
        if len(data) < 2:
            return data, timestamps, 0
        
        # 转换时间戳为数值
        if isinstance(timestamps[0], (pd.Timestamp, np.datetime64)):
            time_numeric = pd.to_datetime(timestamps).astype(np.int64)
        else:
            time_numeric = np.array(timestamps, dtype=np.float64)
        
        # 检测缺失（NaN值）
        valid_mask = ~np.isnan(data)
        
        if valid_mask.all():
            # 没有缺失值，检查时间间隔
            return self._interpolate_by_time_gap(data, timestamps, time_numeric, method)
        
        # 有缺失值，进行插值
        valid_times = time_numeric[valid_mask]
        valid_data = data[valid_mask]
        
        if len(valid_data) < 2:
            return data, timestamps, 0
        
        # 创建插值函数
        interp_func = interpolate.interp1d(
            valid_times, valid_data, 
            kind=method, 
            fill_value='extrapolate',
            bounds_error=False
        )
        
        # 插值填充
        interpolated = interp_func(time_numeric)
        interpolated_count = (~valid_mask).sum()
        
        logger.info(f"插值完成: 填充了 {interpolated_count} 个缺失值")
        
        return interpolated, timestamps, interpolated_count
    
    def _interpolate_by_time_gap(
        self, 
        data: np.ndarray, 
        timestamps: np.ndarray,
        time_numeric: np.ndarray,
        method: str
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        根据时间间隔进行插值
        
        检测时间序列中的间隔，对间隔过大的区域进行插值。
        
        Args:
            data: 预紧力数据
            timestamps: 时间戳
            time_numeric: 数值化的时间戳
            method: 插值方法
            
        Returns:
            Tuple: (插值后的数据, 新时间戳, 插值数量)
        """
        # 计算时间差
        time_diffs = np.diff(time_numeric)
        median_diff = np.median(time_diffs)
        
        # 找出间隔过大的位置（超过中位数的3倍）
        gap_threshold = median_diff * 3
        large_gaps = np.where(time_diffs > gap_threshold)[0]
        
        if len(large_gaps) == 0:
            return data, timestamps, 0
        
        # 在间隔处插入新点
        new_times = list(time_numeric)
        new_data = list(data)
        insert_count = 0
        
        for gap_idx in reversed(large_gaps):
            # 计算需要插入的点数
            gap_size = time_diffs[gap_idx]
            n_points = int(gap_size / median_diff) - 1
            
            if n_points > 0 and n_points < 100:  # 限制插入点数
                # 线性插值
                t_start = time_numeric[gap_idx]
                t_end = time_numeric[gap_idx + 1]
                v_start = data[gap_idx]
                v_end = data[gap_idx + 1]
                
                for i in range(n_points, 0, -1):
                    ratio = i / (n_points + 1)
                    new_t = t_start + ratio * (t_end - t_start)
                    new_v = v_start + ratio * (v_end - v_start)
                    new_times.insert(gap_idx + 1, new_t)
                    new_data.insert(gap_idx + 1, new_v)
                    insert_count += 1
        
        logger.info(f"时间间隔插值完成: 插入了 {insert_count} 个数据点")
        
        return np.array(new_data), np.array(new_times), insert_count
    
    def smooth(
        self,
        data: np.ndarray,
        sensor_id: Optional[str] = None,
        mode: Optional[str] = None,
        collect_diagnostics: bool = True,
    ) -> Tuple[np.ndarray, Optional[KalmanDiagnostics], Optional[str]]:
        """
        使用高级卡尔曼滤波对数据进行平滑

        Args:
            data: 输入数据
            sensor_id: 传感器ID，用于查找 per-sensor 覆盖
            mode: 强制指定模式 simple/adaptive/extended
            collect_diagnostics: 是否收集诊断信息

        Returns:
            (smoothed_data, diagnostics, used_mode)
        """
        if len(data) == 0:
            return data, None, None

        kf = self.kalman_factory.create_filter(
            sensor_id=sensor_id, mode=mode, collect_diagnostics=collect_diagnostics
        )
        used_mode = kf.mode
        result = kf.filter(data, collect_diagnostics=collect_diagnostics)
        return result.smoothed_data, result.diagnostics, used_mode
    
    def process(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        remove_anomalies: bool = True,
        normalize: bool = True,
        smooth: bool = True,
        fit_scaler: bool = True,
        sensor_id: Optional[str] = None,
        store_anomalies: bool = False,
        kalman_mode: Optional[str] = None,
        collect_kalman_diagnostics: bool = True,
    ) -> PreprocessingResult:
        """
        执行完整的数据预处理流程

        Args:
            data: 原始预紧力数据
            timestamps: 时间戳数组，可选
            remove_anomalies: 是否移除异常值
            normalize: 是否归一化
            smooth: 是否平滑
            fit_scaler: 是否拟合缩放器
            sensor_id: 传感器ID（用于 per-sensor 参数覆盖和异常存储）
            store_anomalies: 是否将检测到的异常写入数据库
            kalman_mode: 强制指定滤波模式 simple/adaptive/extended（None 则使用配置）
            collect_kalman_diagnostics: 是否收集卡尔曼诊断信息

        Returns:
            PreprocessingResult: 预处理结果，包含 kalman_diagnostics
        """
        result = PreprocessingResult(data=data.copy())

        if remove_anomalies:
            normal_data, anomalies, anomaly_indices = self.detect_anomalies(data)
            result.data = normal_data
            result.anomalies = anomalies
            result.anomaly_indices = anomaly_indices

            if store_anomalies and sensor_id and anomalies is not None and len(anomalies) > 0:
                self.store_anomalies_to_db(
                    sensor_id=sensor_id,
                    anomalies=anomalies,
                    anomaly_indices=anomaly_indices,
                    timestamps=timestamps,
                )

        if timestamps is not None:
            if remove_anomalies and result.anomaly_indices:
                valid_mask = np.ones(len(data), dtype=bool)
                valid_mask[result.anomaly_indices] = False
                valid_timestamps = timestamps[valid_mask]
            else:
                valid_timestamps = timestamps

            result.data, _, result.interpolated_count = self.interpolate_missing(
                result.data, valid_timestamps
            )

        if smooth:
            smoothed, diag, mode = self.smooth(
                result.data,
                sensor_id=sensor_id,
                mode=kalman_mode,
                collect_diagnostics=collect_kalman_diagnostics,
            )
            result.data = smoothed
            result.kalman_diagnostics = diag
            result.kalman_mode = mode

        if normalize:
            result.data = self.normalize(result.data, fit=fit_scaler)
            result.scaler = self.scaler

        logger.info(
            f"数据预处理完成: 原始数据 {len(data)}, 处理后 {len(result.data)}, "
            f"kalman_mode={result.kalman_mode}, diagnostics={'on' if result.kalman_diagnostics else 'off'}"
        )

        return result
    
    def process_dataframe(
        self, 
        df: pd.DataFrame,
        value_column: str = 'ptf',
        time_column: str = 'create_time',
        group_column: Optional[str] = None,
        store_anomalies: bool = False,
    ) -> pd.DataFrame:
        """
        处理DataFrame格式的数据
        
        Args:
            df: 输入DataFrame
            value_column: 预紧力数据列名
            time_column: 时间戳列名
            group_column: 分组列名（如sensor_id），可选
            store_anomalies: 是否将检测到的异常写入数据库
            
        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        if group_column is None:
            # 不分组，直接处理
            data = df[value_column].values
            timestamps = df[time_column].values
            result = self.process(data, timestamps, store_anomalies=store_anomalies)
            
            # 创建新的DataFrame
            processed_df = pd.DataFrame({
                time_column: df[time_column].iloc[:len(result.data)].values,
                value_column: result.data,
                'is_anomaly': False
            })
            
            return processed_df
        
        # 按组处理
        processed_groups = []
        
        for group_id, group_df in df.groupby(group_column):
            data = group_df[value_column].values
            timestamps = group_df[time_column].values
            result = self.process(
                data, 
                timestamps, 
                sensor_id=str(group_id) if store_anomalies else None,
                store_anomalies=store_anomalies,
            )
            
            group_processed = pd.DataFrame({
                group_column: group_id,
                time_column: group_df[time_column].iloc[:len(result.data)].values,
                value_column: result.data
            })
            processed_groups.append(group_processed)
        
        return pd.concat(processed_groups, ignore_index=True)


# ============================================================
# 多变量/多传感器数据预处理扩展
# ============================================================

@dataclass
class MultivariatePreprocessingResult:
    """
    多变量预处理结果数据类

    Attributes:
        data: 处理后的多通道数据，形状 (N, n_channels)
        timestamps: 对齐后的时间戳 (N,)
        channels: 实际使用的通道名称列表
        channel_means: 各通道均值（用于反归一化）
        channel_stds: 各通道标准差
        interpolation_flags: 各点各通道的插值标记（1=插值填充，0=原始数据）
        data_quality: 数据质量标记 full/partial/degraded
        missing_channels: 缺失/降级的通道名称列表
        complete_ratio: 完整数据占比（非插值非缺失的比例）
        interpolation_count: 总插值填充点数
        channel_kalman_diagnostics: 各通道卡尔曼诊断信息
        channel_kalman_modes: 各通道实际使用的滤波模式
    """
    data: np.ndarray
    timestamps: np.ndarray
    channels: List[str]
    channel_means: Optional[np.ndarray] = None
    channel_stds: Optional[np.ndarray] = None
    interpolation_flags: Optional[np.ndarray] = None
    data_quality: str = "full"
    missing_channels: List[str] = None
    complete_ratio: float = 1.0
    interpolation_count: int = 0
    channel_kalman_diagnostics: Dict[str, Optional[KalmanDiagnostics]] = field(default_factory=dict)
    channel_kalman_modes: Dict[str, Optional[str]] = field(default_factory=dict)

    def __post_init__(self):
        if self.missing_channels is None:
            self.missing_channels = []


class MultivariatePreprocessor:
    """
    多变量/多传感器数据预处理器

    支持功能:
    1. 多通道时间对齐（统一时间网格）
    2. 多通道联合插值（支持线性、时间感知、样条插值）
    3. 通道缺失检测与降级策略
    4. 逐通道归一化
    5. 逐通道卡尔曼平滑
    6. 数据质量评估与标注
    """

    def __init__(
        self,
        interpolation_method: str = "linear",
        normalize_mode: str = "channel_wise",
        smooth_each_channel: bool = True,
        min_complete_ratio: float = 0.5,
        allow_degraded: bool = True,
        fallback_channel: str = "preload",
        collect_kalman_diagnostics: bool = True,
    ):
        self.interpolation_method = interpolation_method
        self.normalize_mode = normalize_mode
        self.smooth_each_channel = smooth_each_channel
        self.min_complete_ratio = min_complete_ratio
        self.allow_degraded = allow_degraded
        self.fallback_channel = fallback_channel
        self.collect_kalman_diagnostics = collect_kalman_diagnostics

        self._channel_scalers: Dict[str, StandardScaler] = {}
        self._kalman_filters: Dict[str, KalmanFilter] = {}
        self._kalman_factory = KalmanFilterFactory()

    # ---------- 核心：多通道时间对齐与插值 ----------

    def align_and_interpolate(
        self,
        channels_data: Dict[str, Tuple[np.ndarray, np.ndarray]],
        target_timestamps: Optional[np.ndarray] = None,
    ) -> MultivariatePreprocessingResult:
        """
        将各通道（时间戳+数值）对齐到统一时间网格，并进行插值填充

        Args:
            channels_data: 各通道数据字典 {channel_name: (timestamps, values)}
                           timestamps 可以是数值或 datetime
            target_timestamps: 目标时间网格，如为 None 则使用所有通道时间的并集

        Returns:
            MultivariatePreprocessingResult
        """
        import pandas as pd

        # 1. 将所有通道的时间戳转换为数值（秒/纳秒）
        channel_list = list(channels_data.keys())
        channels_numeric = {}

        for ch, (ts, vals) in channels_data.items():
            ts_num = self._to_numeric_time(ts)
            channels_numeric[ch] = (ts_num, np.asarray(vals, dtype=np.float32))

        # 2. 构建目标时间网格
        if target_timestamps is not None:
            target_num = self._to_numeric_time(target_timestamps)
        else:
            all_times = np.concatenate([ts for ts, _ in channels_numeric.values()])
            target_num = np.unique(np.sort(all_times))

        N = len(target_num)
        n_channels = len(channel_list)

        # 3. 初始化结果矩阵和插值标记
        aligned = np.full((N, n_channels), np.nan, dtype=np.float32)
        interp_flags = np.zeros((N, n_channels), dtype=np.int8)  # 1=interpolated

        # 4. 逐通道在目标网格上插值
        total_interp = 0
        for ch_idx, ch in enumerate(channel_list):
            ts_num, vals = channels_numeric[ch]
            col_result, col_flags, col_count = self._interpolate_channel(
                ts_num, vals, target_num
            )
            aligned[:, ch_idx] = col_result
            interp_flags[:, ch_idx] = col_flags
            total_interp += col_count

        # 5. 将 target_num 转换回原类型（若需要）
        if target_timestamps is not None:
            out_timestamps = target_timestamps
        else:
            # 以第一个通道的时间类型为准
            first_ts = channels_data[channel_list[0]][0]
            out_timestamps = self._numeric_to_original(target_num, first_ts)

        # 6. 评估完整度与降级策略
        complete_ratio = 1.0 - (np.sum(interp_flags) / max(N * n_channels, 1))
        missing_chs = []
        data_quality = 'full'

        # 检测完全缺失的通道（所有值都是NaN）
        for ch_idx, ch in enumerate(channel_list):
            col = aligned[:, ch_idx]
            nan_ratio = np.mean(np.isnan(col))
            if nan_ratio > 0.9:
                missing_chs.append(ch)

        if len(missing_chs) > 0 or complete_ratio < self.min_complete_ratio:
            if self.allow_degraded and self.fallback_channel in channel_list:
                # 降级：只保留 fallback_channel
                fb_idx = channel_list.index(self.fallback_channel)
                aligned = aligned[:, [fb_idx]]
                interp_flags = interp_flags[:, [fb_idx]]
                missing_chs = [c for c in channel_list if c != self.fallback_channel]
                channel_list = [self.fallback_channel]
                n_channels = 1
                complete_ratio = 1.0 - (np.sum(interp_flags) / max(N, 1))
                data_quality = 'degraded'
                logger.warning(
                    f"多变量预处理降级为单变量({self.fallback_channel})，"
                    f"缺失通道: {missing_chs}, 完整率={complete_ratio:.3f}"
                )
            else:
                data_quality = 'partial' if len(missing_chs) < len(channel_list) else 'degraded'

        result = MultivariatePreprocessingResult(
            data=aligned,
            timestamps=np.asarray(out_timestamps),
            channels=channel_list,
            interpolation_flags=interp_flags,
            data_quality=data_quality,
            missing_channels=missing_chs,
            complete_ratio=float(complete_ratio),
            interpolation_count=int(total_interp),
        )

        logger.info(
            f"多通道对齐完成: 通道={channel_list}, 长度={N}, "
            f"质量={data_quality}, 完整率={complete_ratio:.3f}"
        )
        return result

    # ---------- 归一化与平滑 ----------

    def normalize_multivariate(
        self,
        result: MultivariatePreprocessingResult,
        fit: bool = True,
    ) -> MultivariatePreprocessingResult:
        """
        逐通道归一化（StandardScaler）

        Args:
            result: 对齐后的预处理结果
            fit: 是否拟合 scaler（训练时 True，预测时 False）

        Returns:
            更新后的 MultivariatePreprocessingResult
        """
        if self.normalize_mode == 'none':
            return result

        N, C = result.data.shape
        means = np.zeros(C, dtype=np.float32)
        stds = np.ones(C, dtype=np.float32)

        for c, ch in enumerate(result.channels):
            col = result.data[:, c]
            valid = ~np.isnan(col)
            if not valid.any():
                continue

            if fit:
                scaler = StandardScaler()
                scaler.fit(col[valid].reshape(-1, 1))
                self._channel_scalers[ch] = scaler
            else:
                scaler = self._channel_scalers.get(ch)
                if scaler is None:
                    logger.warning(f"通道 {ch} 无拟合 scaler，跳过归一化")
                    continue

            transformed = np.full_like(col, np.nan)
            transformed[valid] = scaler.transform(col[valid].reshape(-1, 1)).ravel()
            result.data[:, c] = transformed
            means[c] = float(scaler.mean_[0])
            stds[c] = float(np.sqrt(scaler.var_[0]))

        result.channel_means = means
        result.channel_stds = stds
        return result

    def smooth_multivariate(
        self,
        result: MultivariatePreprocessingResult,
    ) -> MultivariatePreprocessingResult:
        """
        逐通道卡尔曼平滑（仅对非插值点应用，保持插值结果不变）

        Args:
            result: 预处理结果

        Returns:
            平滑后的结果
        """
        if not self.smooth_each_channel:
            return result

        from app.services.kalman_filter import BaseKalmanFilter

        N, C = result.data.shape

        for c, ch in enumerate(result.channels):
            col = result.data[:, c].copy()
            valid = ~np.isnan(col)

            if valid.sum() < 2:
                continue

            if ch not in self._kalman_filters:
                self._kalman_filters[ch] = KalmanFilter(
                    process_noise=0.01, measurement_noise=0.1
                )

            kf_advanced: BaseKalmanFilter = self._kalman_factory.create_filter(
                sensor_id=ch, collect_diagnostics=self.collect_kalman_diagnostics
            )

            first_valid_idx = np.argmax(valid)
            init_val = float(col[first_valid_idx])
            kf_advanced.reset(init_val)

            for i in range(N):
                if np.isnan(col[i]):
                    continue
                if result.interpolation_flags[i, c] == 1:
                    kf_advanced.x = float(col[i])
                    kf_advanced._initialized = True
                    continue
                state = kf_advanced.update(float(col[i]))
                col[i] = state.estimate

            result.data[:, c] = col

            diag = kf_advanced.get_diagnostics()
            result.channel_kalman_diagnostics[ch] = diag
            result.channel_kalman_modes[ch] = kf_advanced.mode

        return result

    # ---------- 便捷处理流水线 ----------

    def process(
        self,
        channels_data: Dict[str, Tuple[np.ndarray, np.ndarray]],
        target_timestamps: Optional[np.ndarray] = None,
        normalize: bool = True,
        smooth: bool = True,
    ) -> MultivariatePreprocessingResult:
        """
        多变量数据完整处理流水线：对齐 -> 平滑 -> 归一化

        Args:
            channels_data: {channel: (timestamps, values)}
            target_timestamps: 目标时间网格
            normalize: 是否归一化
            smooth: 是否卡尔曼平滑

        Returns:
            MultivariatePreprocessingResult
        """
        # 1. 对齐与插值
        result = self.align_and_interpolate(channels_data, target_timestamps)

        # 2. 平滑
        if smooth:
            result = self.smooth_multivariate(result)

        # 3. 归一化
        if normalize:
            result = self.normalize_multivariate(result, fit=True)

        return result

    def process_from_arrays(
        self,
        array_2d: np.ndarray,
        channels: List[str],
        timestamps: Optional[np.ndarray] = None,
    ) -> MultivariatePreprocessingResult:
        """
        从 (N, C) 数组直接处理（各通道已对齐，仅做缺失插值与评估）

        Args:
            array_2d: 形状 (N, n_channels)，NaN 表示缺失
            channels: 通道名称列表，长度 = C
            timestamps: 时间戳数组，长度 = N

        Returns:
            MultivariatePreprocessingResult
        """
        array_2d = np.asarray(array_2d, dtype=np.float32)
        N, C = array_2d.shape
        if len(channels) != C:
            raise ValueError(f"通道数不匹配: array C={C}, channels={len(channels)}")

        # 默认生成索引时间戳
        if timestamps is None:
            timestamps = np.arange(N, dtype=np.float64)

        # 对每个通道独立做插值
        result = np.copy(array_2d)
        interp_flags = np.zeros((N, C), dtype=np.int8)
        total_interp = 0

        for c in range(C):
            col = result[:, c]
            valid = ~np.isnan(col)
            if valid.all():
                continue
            if valid.sum() < 2:
                continue
            idx_all = np.arange(N)
            idx_valid = idx_all[valid]
            val_valid = col[valid]
            try:
                f = interpolate.interp1d(
                    idx_valid, val_valid, kind='linear',
                    fill_value='extrapolate', bounds_error=False
                )
                filled = f(idx_all)
                new_nan = ~valid
                result[new_nan, c] = filled[new_nan]
                interp_flags[new_nan, c] = 1
                total_interp += int(new_nan.sum())
            except Exception as e:
                logger.warning(f"通道 {channels[c]} 插值失败: {e}")

        # 评估完整度与降级
        complete_ratio = 1.0 - (np.sum(interp_flags) / max(N * C, 1))
        missing_chs = []
        data_quality = 'full'

        for c, ch in enumerate(channels):
            nan_ratio = np.mean(np.isnan(result[:, c]))
            if nan_ratio > 0.9:
                missing_chs.append(ch)

        if len(missing_chs) > 0 or complete_ratio < self.min_complete_ratio:
            if self.allow_degraded and self.fallback_channel in channels:
                fb_idx = channels.index(self.fallback_channel)
                result = result[:, [fb_idx]]
                interp_flags = interp_flags[:, [fb_idx]]
                missing_chs = [c for c in channels if c != self.fallback_channel]
                channels = [self.fallback_channel]
                complete_ratio = 1.0 - (np.sum(interp_flags) / max(N, 1))
                data_quality = 'degraded'
                logger.warning(f"process_from_arrays 降级为单变量，缺失通道: {missing_chs}")
            else:
                data_quality = 'partial' if missing_chs else 'partial'

        mv_result = MultivariatePreprocessingResult(
            data=result,
            timestamps=np.asarray(timestamps),
            channels=channels,
            interpolation_flags=interp_flags,
            data_quality=data_quality,
            missing_channels=missing_chs,
            complete_ratio=float(complete_ratio),
            interpolation_count=int(total_interp),
        )
        return mv_result

    # ---------- 内部工具方法 ----------

    @staticmethod
    def _to_numeric_time(timestamps: np.ndarray) -> np.ndarray:
        """将时间戳转换为数值（纳秒级int64）"""
        arr = np.asarray(timestamps)
        if arr.dtype.kind in ('M', 'O'):  # datetime or object (含 str)
            return pd.to_datetime(arr).astype(np.int64).values.astype(np.float64)
        return arr.astype(np.float64)

    @staticmethod
    def _numeric_to_original(numeric_ts: np.ndarray, reference_ts: np.ndarray) -> np.ndarray:
        """将数值时间转换回原始类型（尽量保持）"""
        ref = np.asarray(reference_ts)
        if ref.dtype.kind in ('M', 'O'):
            return pd.to_datetime(numeric_ts.astype(np.int64)).values
        return numeric_ts

    def _interpolate_channel(
        self,
        src_times: np.ndarray,
        src_values: np.ndarray,
        target_times: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        单通道在目标时间网格上插值

        Returns:
            (interpolated_values, interp_flags, interp_count)
        """
        N = len(target_times)
        out = np.full(N, np.nan, dtype=np.float32)
        flags = np.zeros(N, dtype=np.int8)

        valid_mask = ~np.isnan(src_values)
        src_t = src_times[valid_mask]
        src_v = src_values[valid_mask]

        if len(src_v) == 0:
            return out, np.ones(N, dtype=np.int8), N

        # 精确匹配的（时间戳完全一致）直接赋值
        common, src_idx, tgt_idx = np.intersect1d(src_t, target_times, return_indices=True)
        if len(common) > 0:
            out[tgt_idx] = src_v[src_idx].astype(np.float32)
            remaining_mask = np.ones(N, dtype=bool)
            remaining_mask[tgt_idx] = False
        else:
            remaining_mask = np.ones(N, dtype=bool)

        need_interp_idx = np.where(remaining_mask)[0]
        if len(need_interp_idx) == 0 or len(src_v) < 2:
            return out, flags, 0

        interp_times = target_times[need_interp_idx]

        try:
            if self.interpolation_method == 'spline' and len(src_v) >= 4:
                tck = interpolate.splrep(src_t, src_v, k=3)
                filled = interpolate.splev(interp_times, tck)
            elif self.interpolation_method == 'time_aware':
                dt = np.diff(src_t)
                weights = 1.0 / (dt + 1e-9)
                weights = np.concatenate([[weights[0]], weights])
                weights = weights / weights.sum()
                f = interpolate.interp1d(
                    src_t, src_v, kind='linear',
                    fill_value='extrapolate', bounds_error=False
                )
                filled = f(interp_times)
            else:
                f = interpolate.interp1d(
                    src_t, src_v, kind='linear',
                    fill_value='extrapolate', bounds_error=False
                )
                filled = f(interp_times)

            out[need_interp_idx] = filled.astype(np.float32)
            flags[need_interp_idx] = 1
            interp_count = len(need_interp_idx)
        except Exception as e:
            logger.warning(f"通道插值失败（method={self.interpolation_method}）: {e}")
            interp_count = 0

        return out, flags, interp_count
