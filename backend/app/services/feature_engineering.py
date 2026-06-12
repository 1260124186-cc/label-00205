"""
特征工程模块

负责从原始预紧力数据中提取用于模型训练的特征，包括:
1. 时序特征: 滑动窗口统计量、趋势特征、周期性特征
2. 统计特征: 分布特征、变化率特征、极值特征
3. 领域特征: 预紧力安全区间、历史故障模式

使用示例:
    from app.services.feature_engineering import FeatureEngineer
    
    engineer = FeatureEngineer()
    features = engineer.extract_features(time_series_data)
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from scipy import stats
from scipy.fft import fft
from scipy.signal import find_peaks
from loguru import logger

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
    """
    temporal_features: np.ndarray
    statistical_features: np.ndarray
    domain_features: np.ndarray
    combined_features: np.ndarray
    feature_names: List[str]


class FeatureEngineer:
    """
    特征工程师类
    
    从时间序列数据中提取多种类型的特征。
    
    Attributes:
        window_sizes: 滑动窗口大小列表
        preload_thresholds: 预紧力阈值配置
    """
    
    def __init__(self):
        """
        初始化特征工程师
        """
        self.window_sizes = [5, 10, 20, 50]  # 滑动窗口大小
        self.preload_thresholds = config.get('risk_assessment.preload_thresholds', {
            'min_normal': 400,
            'max_normal': 800,
            'warning_deviation': 0.1,
            'critical_deviation': 0.2
        })
        logger.info("特征工程师初始化完成")
    
    def extract_temporal_features(
        self, 
        data: np.ndarray, 
        timestamps: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, List[str]]:
        """
        提取时序特征
        
        包括滑动窗口统计量、趋势特征、周期性特征。
        
        Args:
            data: 预紧力时间序列数据
            timestamps: 时间戳数组
            
        Returns:
            Tuple: (特征数组, 特征名称列表)
        """
        features = []
        feature_names = []
        
        # 1. 滑动窗口统计量
        for window in self.window_sizes:
            if len(data) >= window:
                # 滑动均值
                rolling_mean = self._rolling_mean(data, window)
                features.append(rolling_mean[-1] if len(rolling_mean) > 0 else 0)
                feature_names.append(f'rolling_mean_{window}')
                
                # 滑动标准差
                rolling_std = self._rolling_std(data, window)
                features.append(rolling_std[-1] if len(rolling_std) > 0 else 0)
                feature_names.append(f'rolling_std_{window}')
                
                # 滑动最大值
                rolling_max = self._rolling_max(data, window)
                features.append(rolling_max[-1] if len(rolling_max) > 0 else 0)
                feature_names.append(f'rolling_max_{window}')
                
                # 滑动最小值
                rolling_min = self._rolling_min(data, window)
                features.append(rolling_min[-1] if len(rolling_min) > 0 else 0)
                feature_names.append(f'rolling_min_{window}')
            else:
                features.extend([0, 0, 0, 0])
                feature_names.extend([
                    f'rolling_mean_{window}', f'rolling_std_{window}',
                    f'rolling_max_{window}', f'rolling_min_{window}'
                ])
        
        # 2. 趋势特征（线性回归斜率）
        slope, intercept = self._linear_trend(data)
        features.extend([slope, intercept])
        feature_names.extend(['trend_slope', 'trend_intercept'])
        
        # 3. 周期性特征（傅里叶分析）
        fft_features = self._fourier_features(data)
        features.extend(fft_features)
        feature_names.extend([
            'fft_dominant_freq', 'fft_dominant_amplitude',
            'fft_second_freq', 'fft_second_amplitude'
        ])
        
        # 4. 自相关特征
        autocorr_1 = self._autocorrelation(data, lag=1)
        autocorr_5 = self._autocorrelation(data, lag=5)
        features.extend([autocorr_1, autocorr_5])
        feature_names.extend(['autocorr_lag1', 'autocorr_lag5'])
        
        return np.array(features), feature_names
    
    def extract_statistical_features(self, data: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """
        提取统计特征
        
        包括分布特征、变化率特征、极值特征。
        
        Args:
            data: 预紧力数据数组
            
        Returns:
            Tuple: (特征数组, 特征名称列表)
        """
        features = []
        feature_names = []
        
        # 1. 基本统计量
        features.append(np.mean(data))
        feature_names.append('mean')
        
        features.append(np.std(data))
        feature_names.append('std')
        
        features.append(np.median(data))
        feature_names.append('median')
        
        # 2. 分布特征
        skewness = stats.skew(data) if len(data) > 2 else 0
        features.append(skewness)
        feature_names.append('skewness')
        
        kurtosis = stats.kurtosis(data) if len(data) > 3 else 0
        features.append(kurtosis)
        feature_names.append('kurtosis')
        
        # 3. 极值特征
        features.append(np.max(data))
        feature_names.append('max_value')
        
        features.append(np.min(data))
        feature_names.append('min_value')
        
        features.append(np.max(data) - np.min(data))
        feature_names.append('range')
        
        # 4. 变化率特征
        if len(data) > 1:
            changes = np.diff(data)
            features.append(np.mean(np.abs(changes)))
            feature_names.append('mean_abs_change')
            
            features.append(np.std(changes))
            feature_names.append('change_std')
            
            features.append(np.max(changes))
            feature_names.append('max_increase')
            
            features.append(np.min(changes))
            feature_names.append('max_decrease')
        else:
            features.extend([0, 0, 0, 0])
            feature_names.extend([
                'mean_abs_change', 'change_std', 
                'max_increase', 'max_decrease'
            ])
        
        # 5. 分位数特征
        features.append(np.percentile(data, 25))
        feature_names.append('q25')
        
        features.append(np.percentile(data, 75))
        feature_names.append('q75')
        
        features.append(np.percentile(data, 75) - np.percentile(data, 25))
        feature_names.append('iqr')
        
        return np.array(features), feature_names
    
    def extract_domain_features(self, data: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """
        提取领域特征
        
        基于螺栓预紧力领域知识提取的特征。
        
        Args:
            data: 预紧力数据数组
            
        Returns:
            Tuple: (特征数组, 特征名称列表)
        """
        features = []
        feature_names = []
        
        min_normal = self.preload_thresholds.get('min_normal', 400)
        max_normal = self.preload_thresholds.get('max_normal', 800)
        warning_dev = self.preload_thresholds.get('warning_deviation', 0.1)
        critical_dev = self.preload_thresholds.get('critical_deviation', 0.2)
        
        # 1. 安全区间相关特征
        mean_val = np.mean(data)
        
        # 距离安全区间的偏离程度
        if mean_val < min_normal:
            deviation_ratio = (min_normal - mean_val) / min_normal
        elif mean_val > max_normal:
            deviation_ratio = (mean_val - max_normal) / max_normal
        else:
            deviation_ratio = 0
        
        features.append(deviation_ratio)
        feature_names.append('safety_deviation_ratio')
        
        # 2. 超出阈值的比例
        below_min_ratio = np.sum(data < min_normal) / len(data)
        features.append(below_min_ratio)
        feature_names.append('below_min_ratio')
        
        above_max_ratio = np.sum(data > max_normal) / len(data)
        features.append(above_max_ratio)
        feature_names.append('above_max_ratio')
        
        # 3. 预警区间的比例
        warning_min = min_normal * (1 - warning_dev)
        warning_max = max_normal * (1 + warning_dev)
        critical_min = min_normal * (1 - critical_dev)
        critical_max = max_normal * (1 + critical_dev)
        
        in_warning_zone = np.sum(
            ((data < min_normal) & (data >= warning_min)) |
            ((data > max_normal) & (data <= warning_max))
        ) / len(data)
        features.append(in_warning_zone)
        feature_names.append('warning_zone_ratio')
        
        in_critical_zone = np.sum(
            (data < critical_min) | (data > critical_max)
        ) / len(data)
        features.append(in_critical_zone)
        feature_names.append('critical_zone_ratio')
        
        # 4. 骤降检测（可能断裂）
        if len(data) > 1:
            changes = np.diff(data)
            sudden_drop = np.sum(changes < -mean_val * 0.5) > 0
            features.append(float(sudden_drop))
            feature_names.append('has_sudden_drop')
        else:
            features.append(0)
            feature_names.append('has_sudden_drop')
        
        # 5. 持续下降趋势
        if len(data) >= 10:
            last_10 = data[-10:]
            slope, _ = self._linear_trend(last_10)
            features.append(slope)
            feature_names.append('recent_trend_slope')
        else:
            features.append(0)
            feature_names.append('recent_trend_slope')
        
        # 6. 波动性增加
        if len(data) >= 20:
            first_half_std = np.std(data[:len(data)//2])
            second_half_std = np.std(data[len(data)//2:])
            volatility_increase = second_half_std / (first_half_std + 1e-6)
            features.append(volatility_increase)
            feature_names.append('volatility_increase')
        else:
            features.append(1.0)
            feature_names.append('volatility_increase')
        
        return np.array(features), feature_names
    
    def extract_features(
        self, 
        data: np.ndarray, 
        timestamps: Optional[np.ndarray] = None
    ) -> FeatureSet:
        """
        提取所有特征
        
        Args:
            data: 预紧力时间序列数据
            timestamps: 时间戳数组，可选
            
        Returns:
            FeatureSet: 完整的特征集合
        """
        temporal, temporal_names = self.extract_temporal_features(data, timestamps)
        statistical, stat_names = self.extract_statistical_features(data)
        domain, domain_names = self.extract_domain_features(data)
        
        combined = np.concatenate([temporal, statistical, domain])
        all_names = temporal_names + stat_names + domain_names
        
        return FeatureSet(
            temporal_features=temporal,
            statistical_features=statistical,
            domain_features=domain,
            combined_features=combined,
            feature_names=all_names
        )
    
    def extract_sequence_features(
        self, 
        data: np.ndarray,
        sequence_length: int = 100
    ) -> np.ndarray:
        """
        提取用于LSTM的序列特征
        
        将原始数据转换为适合LSTM输入的序列格式。
        
        Args:
            data: 原始时间序列数据
            sequence_length: 序列长度
            
        Returns:
            np.ndarray: 形状为 (n_samples, sequence_length, n_features) 的数组
        """
        n_samples = len(data) - sequence_length + 1
        
        if n_samples <= 0:
            # 数据不足，进行填充
            padded_data = np.zeros(sequence_length)
            padded_data[-len(data):] = data
            return padded_data.reshape(1, sequence_length, 1)
        
        # 创建序列
        sequences = np.zeros((n_samples, sequence_length, 2))
        
        for i in range(n_samples):
            window = data[i:i + sequence_length]
            sequences[i, :, 0] = window  # 原始值
            
            # 添加时间索引作为第二个特征
            sequences[i, :, 1] = np.arange(sequence_length) / sequence_length
        
        return sequences
    
    def _rolling_mean(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滑动均值"""
        if len(data) < window:
            return np.array([np.mean(data)])
        return np.convolve(data, np.ones(window)/window, mode='valid')
    
    def _rolling_std(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滑动标准差"""
        if len(data) < window:
            return np.array([np.std(data)])
        result = []
        for i in range(len(data) - window + 1):
            result.append(np.std(data[i:i+window]))
        return np.array(result)
    
    def _rolling_max(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滑动最大值"""
        if len(data) < window:
            return np.array([np.max(data)])
        result = []
        for i in range(len(data) - window + 1):
            result.append(np.max(data[i:i+window]))
        return np.array(result)
    
    def _rolling_min(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算滑动最小值"""
        if len(data) < window:
            return np.array([np.min(data)])
        result = []
        for i in range(len(data) - window + 1):
            result.append(np.min(data[i:i+window]))
        return np.array(result)
    
    def _linear_trend(self, data: np.ndarray) -> Tuple[float, float]:
        """计算线性趋势"""
        if len(data) < 2:
            return 0.0, 0.0
        x = np.arange(len(data))
        coefficients = np.polyfit(x, data, 1)
        return coefficients[0], coefficients[1]  # slope, intercept
    
    def _fourier_features(self, data: np.ndarray, top_k: int = 2) -> List[float]:
        """提取傅里叶特征"""
        if len(data) < 4:
            return [0.0] * (top_k * 2)
        
        fft_result = np.abs(fft(data))
        n = len(fft_result)
        
        # 只取前半部分（对称性）
        half_n = n // 2
        magnitudes = fft_result[1:half_n]  # 排除直流分量
        frequencies = np.arange(1, half_n) / n
        
        if len(magnitudes) == 0:
            return [0.0] * (top_k * 2)
        
        # 找到最大的k个频率
        top_indices = np.argsort(magnitudes)[-top_k:][::-1]
        
        features = []
        for idx in top_indices:
            features.append(frequencies[idx])
            features.append(magnitudes[idx])
        
        # 补齐
        while len(features) < top_k * 2:
            features.extend([0.0, 0.0])
        
        return features[:top_k * 2]
    
    def _autocorrelation(self, data: np.ndarray, lag: int = 1) -> float:
        """计算自相关系数"""
        if len(data) <= lag:
            return 0.0
        
        n = len(data)
        mean = np.mean(data)
        var = np.var(data)
        
        if var == 0:
            return 0.0
        
        autocorr = np.sum((data[:-lag] - mean) * (data[lag:] - mean)) / ((n - lag) * var)
        return autocorr
