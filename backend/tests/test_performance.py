"""
性能测试模块

测试系统在高负载下的性能和稳定性。

测试内容:
1. API响应时间
2. 并发处理能力
3. 内存使用
4. 模型推理速度

使用示例:
    pytest tests/test_performance.py -v
"""

import pytest
import time
import numpy as np
import threading
import concurrent.futures
from typing import List, Dict
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPreprocessingPerformance:
    """预处理性能测试"""
    
    def test_kalman_filter_speed(self):
        """测试卡尔曼滤波速度"""
        from app.services.kalman_filter import KalmanFilterService
        
        service = KalmanFilterService()
        
        # 不同数据量的测试
        sizes = [100, 1000, 5000, 10000]
        
        for size in sizes:
            data = np.random.randn(size) * 20 + 600
            
            start = time.time()
            result = service.smooth(data)
            elapsed = time.time() - start
            
            # 确保处理时间在合理范围内
            assert elapsed < size / 1000  # 每1000个数据点不超过1秒
            print(f"  卡尔曼滤波 {size}点: {elapsed*1000:.2f}ms")
    
    def test_anomaly_detection_speed(self):
        """测试异常检测速度"""
        from app.services.anomaly_detection import AnomalyDetector
        
        detector = AnomalyDetector()
        
        sizes = [100, 500, 1000]
        
        for size in sizes:
            data = np.random.randn(size) * 20 + 600
            
            start = time.time()
            result = detector.detect(data)
            elapsed = time.time() - start
            
            assert elapsed < 5.0  # 不超过5秒
            print(f"  异常检测 {size}点: {elapsed*1000:.2f}ms")


class TestModelPerformance:
    """模型性能测试"""
    
    def test_bolt_lstm_inference_speed(self):
        """测试螺栓LSTM推理速度"""
        from app.models.bolt_lstm import BoltLSTMModel
        
        model = BoltLSTMModel(bolt_id='perf_test')
        
        # 单次推理
        data = np.random.randn(100) * 20 + 600
        
        # 预热
        model.predict(data)
        
        # 测试多次推理
        n_iterations = 10
        start = time.time()
        
        for _ in range(n_iterations):
            model.predict(data)
        
        elapsed = time.time() - start
        avg_time = elapsed / n_iterations
        
        print(f"  LSTM推理平均时间: {avg_time*1000:.2f}ms")
        assert avg_time < 1.0  # 单次推理不超过1秒
    
    def test_ensemble_prediction_speed(self):
        """测试集成预测速度"""
        from app.models.ensemble_model import EnsemblePredictor
        
        predictor = EnsemblePredictor()
        
        data = np.random.randn(100) * 20 + 600
        
        # 预热
        predictor.predict(data)
        
        # 测试
        n_iterations = 20
        start = time.time()
        
        for _ in range(n_iterations):
            predictor.predict(data)
        
        elapsed = time.time() - start
        avg_time = elapsed / n_iterations
        
        print(f"  集成预测平均时间: {avg_time*1000:.2f}ms")
        assert avg_time < 0.5  # 单次不超过500ms
    
    def test_fault_classification_speed(self):
        """测试故障分类速度"""
        from app.models.fault_classifier import FaultClassifier
        
        classifier = FaultClassifier()
        
        data = np.random.randn(100) * 20 + 600
        
        n_iterations = 50
        start = time.time()
        
        for _ in range(n_iterations):
            classifier.classify(data)
        
        elapsed = time.time() - start
        avg_time = elapsed / n_iterations
        
        print(f"  故障分类平均时间: {avg_time*1000:.2f}ms")
        assert avg_time < 0.1  # 单次不超过100ms


class TestConcurrencyPerformance:
    """并发性能测试"""
    
    def test_concurrent_predictions(self):
        """测试并发预测"""
        from app.models.ensemble_model import EnsemblePredictor
        
        predictor = EnsemblePredictor()
        
        def make_prediction(data):
            return predictor.predict(data)
        
        # 生成多个测试数据
        n_concurrent = 10
        data_list = [np.random.randn(100) * 20 + 600 for _ in range(n_concurrent)]
        
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_concurrent) as executor:
            futures = [executor.submit(make_prediction, data) for data in data_list]
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start
        
        print(f"  {n_concurrent}个并发预测完成: {elapsed*1000:.2f}ms")
        assert len(results) == n_concurrent
        assert elapsed < 10.0  # 10个并发不超过10秒
    
    def test_thread_safety(self):
        """测试线程安全性"""
        from app.models.fault_classifier import FaultClassifier
        
        classifier = FaultClassifier()
        results = []
        errors = []
        
        def classify_task(task_id):
            try:
                data = np.random.randn(50) * 20 + 600
                result = classifier.classify(data)
                results.append((task_id, result.fault_type))
            except Exception as e:
                errors.append((task_id, str(e)))
        
        # 启动多个线程
        threads = []
        n_threads = 20
        
        for i in range(n_threads):
            t = threading.Thread(target=classify_task, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=10)
        
        assert len(errors) == 0, f"线程错误: {errors}"
        assert len(results) == n_threads


class TestMemoryPerformance:
    """内存性能测试"""
    
    def test_memory_usage_prediction(self):
        """测试预测过程内存使用"""
        import psutil
        import gc
        
        from app.models.bolt_lstm import BoltLSTMModel
        
        process = psutil.Process()
        
        # 初始内存
        gc.collect()
        initial_memory = process.memory_info().rss / (1024 ** 2)  # MB
        
        # 执行多次预测
        model = BoltLSTMModel(bolt_id='memory_test')
        
        for i in range(100):
            data = np.random.randn(100) * 20 + 600
            model.predict(data)
        
        gc.collect()
        final_memory = process.memory_info().rss / (1024 ** 2)
        
        memory_increase = final_memory - initial_memory
        
        print(f"  100次预测内存增长: {memory_increase:.2f}MB")
        assert memory_increase < 100  # 内存增长不超过100MB
    
    def test_large_data_handling(self):
        """测试大数据处理"""
        from app.services.kalman_filter import KalmanFilterService
        
        service = KalmanFilterService()
        
        # 大数据量测试
        large_data = np.random.randn(100000) * 20 + 600
        
        start = time.time()
        result = service.smooth(large_data)
        elapsed = time.time() - start
        
        print(f"  100000数据点处理: {elapsed:.2f}s")
        assert len(result) == len(large_data)
        assert elapsed < 30  # 不超过30秒


class TestLatencyBenchmark:
    """延迟基准测试"""
    
    def test_end_to_end_latency(self):
        """测试端到端延迟"""
        from app.services.anomaly_detection import AnomalyDetector
        from app.services.kalman_filter import KalmanFilterService
        from app.models.fault_classifier import FaultClassifier
        from app.models.ensemble_model import EnsemblePredictor
        
        detector = AnomalyDetector()
        kalman = KalmanFilterService()
        classifier = FaultClassifier()
        ensemble = EnsemblePredictor()
        
        data = np.random.randn(100) * 20 + 600
        
        # 完整流程计时
        start = time.time()
        
        # 1. 异常检测
        detection_result = detector.detect(data)
        
        # 2. 数据平滑
        smoothed = kalman.smooth(detection_result.cleaned_data)
        
        # 3. 故障分类
        fault_result = classifier.classify(smoothed)
        
        # 4. 集成预测
        prediction = ensemble.predict(smoothed)
        
        elapsed = time.time() - start
        
        print(f"\n  端到端处理延迟:")
        print(f"    总耗时: {elapsed*1000:.2f}ms")
        
        assert elapsed < 2.0  # 完整流程不超过2秒


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
