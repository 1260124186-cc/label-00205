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
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import IsolationForest
from scipy import interpolate
from loguru import logger

from app.utils.config import config


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
    """
    data: np.ndarray
    anomalies: Optional[np.ndarray] = None
    anomaly_indices: Optional[List[int]] = None
    interpolated_count: int = 0
    scaler: Optional[Any] = None


class KalmanFilter:
    """
    卡尔曼滤波器
    
    用于对时间序列数据进行平滑处理，减少噪声影响。
    
    Attributes:
        process_noise: 过程噪声协方差
        measurement_noise: 测量噪声协方差
        estimate: 当前状态估计
        estimate_error: 估计误差协方差
    """
    
    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 0.1):
        """
        初始化卡尔曼滤波器
        
        Args:
            process_noise: 过程噪声协方差，控制模型对变化的敏感度
            measurement_noise: 测量噪声协方差，控制对测量值的信任程度
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.estimate = 0.0
        self.estimate_error = 1.0
        
    def reset(self, initial_value: float = 0.0) -> None:
        """
        重置滤波器状态
        
        Args:
            initial_value: 初始估计值
        """
        self.estimate = initial_value
        self.estimate_error = 1.0
        
    def update(self, measurement: float) -> float:
        """
        更新滤波器状态
        
        Args:
            measurement: 新的测量值
            
        Returns:
            float: 滤波后的估计值
        """
        # 预测步骤
        prediction = self.estimate
        prediction_error = self.estimate_error + self.process_noise
        
        # 更新步骤
        kalman_gain = prediction_error / (prediction_error + self.measurement_noise)
        self.estimate = prediction + kalman_gain * (measurement - prediction)
        self.estimate_error = (1 - kalman_gain) * prediction_error
        
        return self.estimate
    
    def filter(self, data: np.ndarray) -> np.ndarray:
        """
        对整个数据序列进行滤波
        
        Args:
            data: 输入数据数组
            
        Returns:
            np.ndarray: 滤波后的数据数组
        """
        if len(data) == 0:
            return data
        
        self.reset(data[0])
        filtered = np.zeros_like(data, dtype=float)
        filtered[0] = data[0]
        
        for i in range(1, len(data)):
            filtered[i] = self.update(data[i])
        
        return filtered


class DataPreprocessor:
    """
    数据预处理器
    
    集成了多种数据预处理方法，提供完整的数据清洗流程。
    
    Attributes:
        config: 预处理配置
        scaler: 数据缩放器
        isolation_forest: 孤立森林模型
        kalman_filter: 卡尔曼滤波器
    """
    
    def __init__(self):
        """
        初始化数据预处理器
        """
        self.config = config.get('preprocessing', {})
        self._init_components()
        
    def _init_components(self) -> None:
        """
        初始化预处理组件
        """
        # 初始化缩放器
        norm_method = self.config.get('normalization', {}).get('method', 'minmax')
        if norm_method == 'zscore':
            self.scaler = StandardScaler()
        else:
            self.scaler = MinMaxScaler()
        
        # 初始化孤立森林
        iso_config = self.config.get('isolation_forest', {})
        self.isolation_forest = IsolationForest(
            contamination=iso_config.get('contamination', 0.1),
            n_estimators=iso_config.get('n_estimators', 100),
            random_state=iso_config.get('random_state', 42),
            n_jobs=-1
        )
        
        # 初始化卡尔曼滤波器
        kalman_config = self.config.get('kalman_filter', {})
        self.kalman_filter = KalmanFilter(
            process_noise=kalman_config.get('process_noise', 0.01),
            measurement_noise=kalman_config.get('measurement_noise', 0.1)
        )
        
        logger.info("数据预处理器初始化完成")
    
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
    
    def smooth(self, data: np.ndarray) -> np.ndarray:
        """
        使用卡尔曼滤波对数据进行平滑
        
        Args:
            data: 输入数据
            
        Returns:
            np.ndarray: 平滑后的数据
        """
        return self.kalman_filter.filter(data)
    
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
            sensor_id: 传感器ID（存储异常时需要）
            store_anomalies: 是否将检测到的异常写入数据库
            
        Returns:
            PreprocessingResult: 预处理结果
        """
        result = PreprocessingResult(data=data.copy())
        
        # 1. 异常值检测
        if remove_anomalies:
            normal_data, anomalies, anomaly_indices = self.detect_anomalies(data)
            result.data = normal_data
            result.anomalies = anomalies
            result.anomaly_indices = anomaly_indices
            
            # 存储异常到数据库
            if store_anomalies and sensor_id and anomalies is not None and len(anomalies) > 0:
                self.store_anomalies_to_db(
                    sensor_id=sensor_id,
                    anomalies=anomalies,
                    anomaly_indices=anomaly_indices,
                    timestamps=timestamps,
                )
        
        # 2. 缺失值插值
        if timestamps is not None:
            # 需要根据异常值移除后的索引调整时间戳
            if remove_anomalies and result.anomaly_indices:
                valid_mask = np.ones(len(data), dtype=bool)
                valid_mask[result.anomaly_indices] = False
                valid_timestamps = timestamps[valid_mask]
            else:
                valid_timestamps = timestamps
            
            result.data, _, result.interpolated_count = self.interpolate_missing(
                result.data, valid_timestamps
            )
        
        # 3. 卡尔曼滤波平滑
        if smooth:
            result.data = self.smooth(result.data)
        
        # 4. 归一化
        if normalize:
            result.data = self.normalize(result.data, fit=fit_scaler)
            result.scaler = self.scaler
        
        logger.info(f"数据预处理完成: 原始数据 {len(data)}, 处理后 {len(result.data)}")
        
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
