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
        """测试一维卡尔曼滤波（兼容旧API）"""
        from app.services.kalman_filter import SimpleKalmanFilter

        np.random.seed(42)
        true_values = np.linspace(100, 200, 50)
        noisy_data = true_values + np.random.randn(50) * 10

        kf = SimpleKalmanFilter(process_noise=0.01, measurement_noise=1.0)
        result = kf.filter(noisy_data)

        assert len(result.smoothed_data) == len(noisy_data)
        assert np.std(result.smoothed_data - true_values) < np.std(noisy_data - true_values)

    def test_adaptive_kalman(self):
        """测试自适应卡尔曼滤波"""
        from app.services.kalman_filter import AdaptiveKalmanFilter

        np.random.seed(42)
        data = np.sin(np.linspace(0, 4 * np.pi, 100)) * 100 + 500
        noisy_data = data + np.random.randn(100) * 20

        kf = AdaptiveKalmanFilter()
        result = kf.filter(noisy_data)

        assert len(result.smoothed_data) == len(noisy_data)

    def test_extended_kalman_constant(self):
        """测试扩展卡尔曼滤波（constant 状态转移，等价于simple）"""
        from app.services.kalman_filter import ExtendedKalmanFilter, SimpleKalmanFilter

        np.random.seed(42)
        data = np.linspace(500, 600, 30) + np.random.randn(30) * 5

        ekf = ExtendedKalmanFilter(state_transition="constant", process_noise=0.01, measurement_noise=0.5)
        skf = SimpleKalmanFilter(process_noise=0.01, measurement_noise=0.5)

        r_ekf = ekf.filter(data)
        r_skf = skf.filter(data)

        np.testing.assert_allclose(r_ekf.smoothed_data, r_skf.smoothed_data, rtol=1e-6)

    def test_extended_kalman_drift(self):
        """测试扩展卡尔曼滤波（linear_drift 线性漂移状态转移）"""
        from app.services.kalman_filter import ExtendedKalmanFilter

        np.random.seed(42)
        drift_rate = 0.5
        n = 50
        base = np.arange(n) * drift_rate + 100.0
        noisy = base + np.random.randn(n) * 2.0

        ekf = ExtendedKalmanFilter(
            state_transition="linear_drift",
            drift_rate=drift_rate,
            process_noise=0.01,
            measurement_noise=4.0,
        )
        result = ekf.filter(noisy)

        assert len(result.smoothed_data) == n
        final_estimate = result.smoothed_data[-1]
        expected_final = base[-1]
        assert abs(final_estimate - expected_final) < 5.0

    def test_rts_smoother(self):
        """测试RTS双向平滑"""
        from app.services.kalman_filter import RauchTungStriebelSmoother

        np.random.seed(42)
        true_values = np.linspace(100, 200, 30)
        noisy_data = true_values + np.random.randn(30) * 10

        smoother = RauchTungStriebelSmoother()
        smoothed = smoother.smooth(noisy_data)

        assert len(smoothed) == len(noisy_data)
        assert np.std(smoothed - true_values) < np.std(noisy_data - true_values)

    def test_kalman_diagnostics_output(self):
        """测试卡尔曼诊断信息输出（增益、新息、误差协方差）"""
        from app.services.kalman_filter import (
            SimpleKalmanFilter,
            KalmanDiagnostics,
        )

        np.random.seed(42)
        data = np.linspace(500, 600, 20) + np.random.randn(20) * 3

        kf = SimpleKalmanFilter(process_noise=0.01, measurement_noise=1.0)
        result = kf.filter_with_diagnostics(data)

        diag = result.diagnostics
        assert diag is not None
        assert isinstance(diag, KalmanDiagnostics)
        assert len(diag.kalman_gains) == len(data)
        assert len(diag.innovations) == len(data)
        assert len(diag.error_covariances) == len(data)
        assert len(diag.predicted_covariances) == len(data)
        assert len(diag.measurement_noise) == len(data)
        assert diag.mode == "simple"

        summary = diag.summary()
        assert "innovation_std" in summary
        assert "mean_gain" in summary
        assert "final_error_covariance" in summary

        d = diag.to_dict()
        assert d["mode"] == "simple"
        assert len(d["kalman_gains"]) == len(data)

    def test_adaptive_noise_adjustment(self):
        """测试自适应模式根据新息动态调整 measurement_noise"""
        from app.services.kalman_filter import AdaptiveKalmanFilter

        np.random.seed(42)
        n = 80
        base = np.full(n, 500.0)
        # 前半段低噪声，后半段高噪声
        low_noise = np.random.randn(n // 2) * 1.0
        high_noise = np.random.randn(n // 2) * 15.0
        noisy = base + np.concatenate([low_noise, high_noise])

        akf = AdaptiveKalmanFilter(
            process_noise=0.01,
            measurement_noise=1.0,
            adaptation_rate=0.3,
            innovation_window=10,
            upper_threshold=1.2,
            lower_threshold=0.8,
            min_measurement_noise_ratio=0.1,
        )
        result = akf.filter_with_diagnostics(noisy)

        diag = result.diagnostics
        assert diag is not None
        r_series = diag.measurement_noise
        # 后半段高噪声段 R 应该被调大
        r_low = np.mean(r_series[10 : n // 2])
        r_high = np.mean(r_series[n // 2 + 10 :])
        assert r_high > r_low, f"自适应应在高噪声段增大R: low={r_low}, high={r_high}"

    def test_kalman_filter_factory_modes(self):
        """测试 KalmanFilterFactory 创建三种模式"""
        from app.services.kalman_filter import (
            KalmanFilterFactory,
            SimpleKalmanFilter,
            AdaptiveKalmanFilter,
            ExtendedKalmanFilter,
        )

        factory = KalmanFilterFactory()

        kf_simple = factory.create_filter(mode="simple", collect_diagnostics=False)
        assert isinstance(kf_simple, SimpleKalmanFilter)

        kf_adaptive = factory.create_filter(mode="adaptive", collect_diagnostics=False)
        assert isinstance(kf_adaptive, AdaptiveKalmanFilter)

        kf_extended = factory.create_filter(mode="extended", collect_diagnostics=False)
        assert isinstance(kf_extended, ExtendedKalmanFilter)

    def test_kalman_factory_sensor_override(self):
        """测试工厂 per-sensor 参数覆盖"""
        from app.services.kalman_filter import KalmanFilterFactory, AdaptiveKalmanFilter

        factory = KalmanFilterFactory()
        factory.default_mode = "simple"
        factory.sensor_overrides = {
            "HIGH_NOISE_SENSOR": {
                "mode": "adaptive",
                "measurement_noise": 0.99,
            }
        }

        kf_normal = factory.create_filter(sensor_id="NORMAL_SENSOR")
        assert kf_normal.mode == "simple"

        kf_override = factory.create_filter(sensor_id="HIGH_NOISE_SENSOR")
        assert isinstance(kf_override, AdaptiveKalmanFilter)
        assert kf_override.mode == "adaptive"
        assert abs(kf_override.R - 0.99) < 1e-6

    def test_streaming_incremental_vs_batch(self):
        """测试流式增量结果与批量滤波结果一致"""
        from app.services.kalman_filter import SimpleKalmanFilter, StreamingKalmanManager

        np.random.seed(42)
        data = np.linspace(500, 600, 30) + np.random.randn(30) * 3

        kf_batch = SimpleKalmanFilter(process_noise=0.01, measurement_noise=0.5)
        batch_result = kf_batch.filter(data)

        manager = StreamingKalmanManager()
        manager.factory.default_Q = 0.01
        manager.factory.default_R = 0.5
        manager.factory.default_mode = "simple"
        incremental_results = []
        for v in data:
            est, _ = manager.update("BOLT-TEST", float(v))
            incremental_results.append(est)

        np.testing.assert_allclose(
            np.array(incremental_results), batch_result.smoothed_data, rtol=1e-5
        )

    def test_streaming_state_save_load(self):
        """测试流式状态保存与恢复"""
        from app.services.kalman_filter import StreamingKalmanManager, KalmanStreamingState

        np.random.seed(42)
        data1 = np.linspace(500, 550, 15) + np.random.randn(15) * 2
        data2 = np.linspace(550, 600, 15) + np.random.randn(15) * 2

        manager = StreamingKalmanManager()
        manager.factory.default_Q = 0.01
        manager.factory.default_R = 0.5
        manager.factory.default_mode = "simple"

        for v in data1:
            manager.update("BOLT-SAVE", float(v))

        state = manager.save_state("BOLT-SAVE")
        assert isinstance(state, KalmanStreamingState)
        assert state.initialized is True

        manager.reset("BOLT-SAVE")
        state_dict = state.to_dict()
        restored = KalmanStreamingState.from_dict(state_dict)
        manager.load_state("BOLT-SAVE", restored)

        part2 = []
        for v in data2:
            est, _ = manager.update("BOLT-SAVE", float(v))
            part2.append(est)

        manager2 = StreamingKalmanManager()
        manager2.factory.default_Q = 0.01
        manager2.factory.default_R = 0.5
        manager2.factory.default_mode = "simple"
        all_data = np.concatenate([data1, data2])
        reference = []
        for v in all_data:
            est, _ = manager2.update("BOLT-REF", float(v))
            reference.append(est)

        np.testing.assert_allclose(np.array(part2), np.array(reference[15:]), rtol=1e-5)


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
        """测试数据预处理器基础流程"""
        from app.services.preprocessing import DataPreprocessor

        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600

        preprocessor = DataPreprocessor()
        result = preprocessor.process(
            data, remove_anomalies=True, normalize=True, smooth=True
        )

        assert len(result.data) <= len(data)
        assert result.data is not None

    def test_preprocessing_kalman_diagnostics(self):
        """测试预处理流水线输出卡尔曼 diagnostics"""
        from app.services.preprocessing import DataPreprocessor
        from app.services.kalman_filter import KalmanDiagnostics

        np.random.seed(42)
        data = np.linspace(500, 600, 50) + np.random.randn(50) * 5

        preprocessor = DataPreprocessor()
        result = preprocessor.process(
            data,
            remove_anomalies=False,
            normalize=False,
            smooth=True,
            collect_kalman_diagnostics=True,
        )

        assert result.kalman_diagnostics is not None
        assert isinstance(result.kalman_diagnostics, KalmanDiagnostics)
        assert result.kalman_mode is not None
        assert len(result.kalman_diagnostics.kalman_gains) == len(result.data)
        assert len(result.kalman_diagnostics.innovations) == len(result.data)
        assert len(result.kalman_diagnostics.error_covariances) == len(result.data)

    def test_preprocessing_kalman_mode_override(self):
        """测试预处理流水线强制指定 kalman_mode"""
        from app.services.preprocessing import DataPreprocessor

        np.random.seed(42)
        data = np.linspace(500, 600, 30) + np.random.randn(30) * 5

        preprocessor = DataPreprocessor()

        r_simple = preprocessor.process(
            data,
            remove_anomalies=False,
            normalize=False,
            smooth=True,
            kalman_mode="simple",
            collect_kalman_diagnostics=True,
        )
        assert r_simple.kalman_mode == "simple"

        r_adaptive = preprocessor.process(
            data,
            remove_anomalies=False,
            normalize=False,
            smooth=True,
            kalman_mode="adaptive",
            collect_kalman_diagnostics=True,
        )
        assert r_adaptive.kalman_mode == "adaptive"

        r_extended = preprocessor.process(
            data,
            remove_anomalies=False,
            normalize=False,
            smooth=True,
            kalman_mode="extended",
            collect_kalman_diagnostics=True,
        )
        assert r_extended.kalman_mode == "extended"

    def test_preprocessing_sensor_id_override(self):
        """测试预处理流水线 per-sensor 参数覆盖"""
        from app.services.preprocessing import DataPreprocessor

        np.random.seed(42)
        data = np.linspace(500, 600, 40) + np.random.randn(40) * 5

        preprocessor = DataPreprocessor()
        preprocessor.kalman_factory.default_mode = "simple"
        preprocessor.kalman_factory.sensor_overrides = {
            "HIGH-NOISE-BOLT": {"mode": "adaptive", "measurement_noise": 0.5}
        }

        r_normal = preprocessor.process(
            data,
            remove_anomalies=False,
            normalize=False,
            smooth=True,
            sensor_id="NORMAL-BOLT",
            collect_kalman_diagnostics=True,
        )
        assert r_normal.kalman_mode == "simple"

        r_override = preprocessor.process(
            data,
            remove_anomalies=False,
            normalize=False,
            smooth=True,
            sensor_id="HIGH-NOISE-BOLT",
            collect_kalman_diagnostics=True,
        )
        assert r_override.kalman_mode == "adaptive"

    def test_preprocessing_streaming_incremental(self):
        """测试预处理流水线流式增量接口（与 StreamingKalmanManager 集成）"""
        from app.services.preprocessing import DataPreprocessor

        np.random.seed(42)
        data = np.linspace(500, 600, 30) + np.random.randn(30) * 3

        preprocessor = DataPreprocessor()
        preprocessor.streaming_kalman.factory.default_Q = 0.01
        preprocessor.streaming_kalman.factory.default_R = 0.5
        preprocessor.streaming_kalman.factory.default_mode = "simple"

        batch_result = preprocessor.process(
            data, remove_anomalies=False, normalize=False, smooth=True,
            kalman_mode="simple", collect_kalman_diagnostics=False,
        )

        incremental_values = []
        for v in data:
            est, _ = preprocessor.streaming_kalman.update("INCR-BOLT", float(v))
            incremental_values.append(est)

        np.testing.assert_allclose(
            np.array(incremental_values), batch_result.data, rtol=1e-5
        )

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
