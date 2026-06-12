"""
数据预处理模块单元测试

测试内容:
1. 数据标准化/归一化
2. 孤立森林异常检测
3. 卡尔曼滤波平滑
4. 时间序列插值
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestKalmanFilter:
    """卡尔曼滤波器测试"""
    
    def test_kalman_filter_1d(self):
        """测试一维卡尔曼滤波"""
        from app.services.kalman_filter import KalmanFilter1D
        
        # 创建带噪声的数据
        np.random.seed(42)
        true_values = np.linspace(100, 200, 50)
        noisy_data = true_values + np.random.randn(50) * 10
        
        # 应用滤波
        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=1.0)
        result = kf.filter(noisy_data)
        
        # 验证结果
        assert len(result.smoothed_data) == len(noisy_data)
        assert np.std(result.smoothed_data - true_values) < np.std(noisy_data - true_values)
    
    def test_adaptive_kalman(self):
        """测试自适应卡尔曼滤波"""
        from app.services.kalman_filter import AdaptiveKalmanFilter
        
        np.random.seed(42)
        data = np.sin(np.linspace(0, 4*np.pi, 100)) * 100 + 500
        noisy_data = data + np.random.randn(100) * 20
        
        kf = AdaptiveKalmanFilter()
        result = kf.filter(noisy_data)
        
        assert len(result.smoothed_data) == len(noisy_data)
    
    def test_rts_smoother(self):
        """测试RTS双向平滑"""
        from app.services.kalman_filter import RauchTungStriebelSmoother
        
        np.random.seed(42)
        true_values = np.linspace(100, 200, 30)
        noisy_data = true_values + np.random.randn(30) * 10
        
        smoother = RauchTungStriebelSmoother()
        smoothed = smoother.smooth(noisy_data)
        
        assert len(smoothed) == len(noisy_data)
        # RTS应该比单向滤波更平滑
        assert np.std(smoothed - true_values) < np.std(noisy_data - true_values)


class TestAnomalyDetection:
    """异常检测测试"""
    
    def test_isolation_forest_detector(self):
        """测试孤立森林检测器"""
        from app.services.anomaly_detection import IsolationForestDetector
        
        np.random.seed(42)
        # 正常数据
        normal_data = np.random.randn(100) * 10 + 500
        # 添加异常点
        normal_data[50] = 1000  # 异常高
        normal_data[75] = 100   # 异常低
        
        detector = IsolationForestDetector(contamination=0.05)
        result = detector.detect(normal_data)
        
        assert result.anomaly_count > 0
        assert len(result.cleaned_data) < len(normal_data)
        # 检查是否检测到添加的异常
        assert 50 in [a.index for a in result.anomalies] or 75 in [a.index for a in result.anomalies]
    
    def test_statistical_detector(self):
        """测试统计异常检测"""
        from app.services.anomaly_detection import StatisticalAnomalyDetector
        
        np.random.seed(42)
        data = np.random.randn(100) * 10 + 500
        data[10] = 600  # 添加异常
        
        detector = StatisticalAnomalyDetector(zscore_threshold=2.0)
        
        # Z-Score检测
        mask, scores = detector.detect_zscore(data)
        assert mask[10] == True  # 异常点应被检测到
        
        # IQR检测
        iqr_mask, bounds = detector.detect_iqr(data)
        assert isinstance(bounds, tuple)
        assert len(bounds) == 2
    
    def test_anomaly_detector_combined(self):
        """测试综合异常检测器"""
        from app.services.anomaly_detection import AnomalyDetector
        
        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        data[25] = 1500  # 极端高值
        data[50] = 50    # 极端低值
        
        detector = AnomalyDetector()
        result = detector.detect(data, methods=['isolation_forest', 'zscore', 'range'])
        
        assert result.anomaly_count >= 2
        assert result.anomaly_ratio > 0


class TestPreprocessing:
    """数据预处理测试"""
    
    def test_data_preprocessor(self):
        """测试数据预处理器"""
        from app.services.preprocessing import DataPreprocessor
        
        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        
        preprocessor = DataPreprocessor()
        result = preprocessor.process(
            data,
            remove_anomalies=True,
            normalize=True,
            smooth=True
        )
        
        assert len(result.data) <= len(data)
        assert result.data is not None
    
    def test_normalization(self):
        """测试归一化"""
        from app.services.preprocessing import DataPreprocessor
        
        data = np.array([100, 200, 300, 400, 500])
        
        preprocessor = DataPreprocessor()
        normalized = preprocessor.normalize(data)
        
        assert normalized.min() >= 0
        assert normalized.max() <= 1


class TestFeatureEngineering:
    """特征工程测试"""
    
    def test_extract_features(self):
        """测试特征提取"""
        from app.services.feature_engineering import FeatureEngineer
        
        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        
        engineer = FeatureEngineer()
        features = engineer.extract_features(data)
        
        assert features.combined_features is not None
        assert len(features.feature_names) > 0
        assert len(features.combined_features) == len(features.feature_names)
    
    def test_temporal_features(self):
        """测试时序特征"""
        from app.services.feature_engineering import FeatureEngineer
        
        np.random.seed(42)
        data = np.linspace(100, 200, 50) + np.random.randn(50) * 5
        
        engineer = FeatureEngineer()
        features, names = engineer.extract_temporal_features(data)
        
        assert len(features) > 0
        assert 'trend_slope' in names
    
    def test_domain_features(self):
        """测试领域特征"""
        from app.services.feature_engineering import FeatureEngineer
        
        # 正常范围内的数据
        normal_data = np.random.randn(100) * 10 + 600
        
        # 异常数据（低于正常范围）
        abnormal_data = np.random.randn(100) * 10 + 300
        
        engineer = FeatureEngineer()
        
        normal_features, _ = engineer.extract_domain_features(normal_data)
        abnormal_features, _ = engineer.extract_domain_features(abnormal_data)
        
        # 异常数据应该有更高的偏离评分
        assert abnormal_features[0] > normal_features[0]  # safety_deviation_ratio


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
