"""
机器学习模型单元测试

测试内容:
1. 螺栓LSTM模型
2. 法兰面注意力模型
3. 贝叶斯风险模型
4. Prophet预测器
"""

import pytest
import numpy as np
import torch
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBoltLSTMModel:
    """螺栓LSTM模型测试"""
    
    def test_model_creation(self):
        """测试模型创建"""
        from app.models.bolt_lstm import BoltLSTMModel, LSTMNetwork
        
        model = BoltLSTMModel(bolt_id='test')
        
        assert model.bolt_id == 'test'
        assert model.model is not None
        assert isinstance(model.model, LSTMNetwork)
    
    def test_lstm_network_forward(self):
        """测试LSTM网络前向传播"""
        from app.models.bolt_lstm import LSTMNetwork
        
        network = LSTMNetwork(
            input_dim=2,
            lstm_units_1=64,
            lstm_units_2=32,
            output_classes=5
        )
        
        # 创建输入张量 (batch=2, seq_len=100, features=2)
        x = torch.randn(2, 100, 2)
        
        output = network(x)
        
        assert output.shape == (2, 5)
    
    def test_prepare_data(self):
        """测试数据准备"""
        from app.models.bolt_lstm import BoltLSTMModel
        
        model = BoltLSTMModel(bolt_id='test')
        
        # 一维数据
        data_1d = np.random.randn(150)
        X, _ = model.prepare_data(data_1d, sequence_length=100)
        
        assert X.shape[1] == 100  # 序列长度
        assert X.shape[2] == 2    # 特征维度
    
    def test_predict_without_training(self):
        """测试未训练模型的预测"""
        from app.models.bolt_lstm import BoltLSTMModel
        
        model = BoltLSTMModel(bolt_id='test')
        
        data = np.random.randn(100) * 20 + 600
        
        # 即使未训练，predict也应该能工作
        pred_class, confidence, _ = model.predict(data)
        
        assert 0 <= pred_class <= 4
        assert 0 <= confidence <= 1
    
    def test_status_labels(self):
        """测试状态标签"""
        from app.models.bolt_lstm import BoltLSTMModel, STATUS_LABELS
        
        model = BoltLSTMModel()
        
        assert model.get_status_label(0) == '正常'
        assert model.get_status_label(4) == '故障'
        assert model.get_status_label(99) == '未知'


class TestFlangeAttentionModel:
    """法兰面注意力模型测试"""
    
    def test_model_creation(self):
        """测试模型创建"""
        from app.models.flange_attention import FlangeAttentionModel
        
        model = FlangeAttentionModel(flange_id='test')
        
        assert model.flange_id == 'test'
        assert model.model is not None
    
    def test_multi_head_attention(self):
        """测试多头自注意力"""
        from app.models.flange_attention import MultiHeadSelfAttention
        
        attention = MultiHeadSelfAttention(embed_dim=32, num_heads=4)
        
        x = torch.randn(2, 10, 32)  # (batch, seq, embed)
        output, weights = attention(x)
        
        assert output.shape == x.shape
        assert weights.shape[1] == 4  # num_heads
    
    def test_bolt_feature_extractor(self):
        """测试螺栓特征提取器"""
        from app.models.flange_attention import BoltFeatureExtractor
        
        extractor = BoltFeatureExtractor(input_dim=2, output_dim=32)
        
        x = torch.randn(2, 100, 2)  # (batch, seq, features)
        features = extractor(x)
        
        assert features.shape == (2, 32)
    
    def test_prepare_data(self):
        """测试多螺栓数据准备"""
        from app.models.flange_attention import FlangeAttentionModel
        
        model = FlangeAttentionModel(flange_id='test')
        
        # 创建多螺栓数据
        multi_bolt_data = [
            np.random.randn(100) * 20 + 600
            for _ in range(5)
        ]
        
        X, _, mask = model.prepare_data(multi_bolt_data, sequence_length=100)
        
        assert X.shape[1] == 20  # max_bolts
        assert X.shape[2] == 100  # seq_len
        assert mask.sum() == 5   # 实际螺栓数


class TestRiskModel:
    """贝叶斯风险模型测试"""
    
    def test_model_creation(self):
        """测试模型创建"""
        from app.models.risk_model import BayesianRiskModel
        
        model = BayesianRiskModel()
        
        assert model is not None
        assert model.thresholds is not None
    
    def test_assess_normal_risk(self):
        """测试正常数据的风险评估"""
        from app.models.risk_model import BayesianRiskModel, RiskLevel
        
        model = BayesianRiskModel()
        
        # 正常范围内的数据
        normal_data = np.random.randn(100) * 10 + 600
        
        result = model.assess_risk(normal_data)
        
        assert result.score >= 7  # 正常数据应该有较高评分
        assert result.level == RiskLevel.LOW
    
    def test_assess_high_risk(self):
        """测试异常数据的风险评估"""
        from app.models.risk_model import BayesianRiskModel, RiskLevel
        
        model = BayesianRiskModel()
        
        # 异常数据（远低于正常范围）
        abnormal_data = np.random.randn(100) * 10 + 200
        
        result = model.assess_risk(abnormal_data)
        
        assert result.score <= 5  # 异常数据应该有较低评分
        assert result.level in [RiskLevel.HIGH, RiskLevel.MEDIUM]
    
    def test_risk_factors(self):
        """测试风险因素识别"""
        from app.models.risk_model import BayesianRiskModel
        
        model = BayesianRiskModel()
        
        # 高波动数据
        volatile_data = np.random.randn(100) * 100 + 600
        
        result = model.assess_risk(volatile_data)
        
        assert len(result.factors) > 0
        assert len(result.recommendations) > 0


class TestProphetForecaster:
    """Prophet预测器测试"""
    
    def test_forecaster_creation(self):
        """测试预测器创建"""
        from app.models.prophet_forecaster import ProphetForecaster
        
        forecaster = ProphetForecaster()
        
        assert forecaster is not None
    
    def test_simple_forecast(self):
        """测试简单预测"""
        from app.models.prophet_forecaster import ProphetForecaster
        import pandas as pd
        
        forecaster = ProphetForecaster()
        
        # 创建历史数据
        np.random.seed(42)
        n = 100
        timestamps = pd.date_range('2025-01-01', periods=n, freq='D')
        data = np.linspace(500, 600, n) + np.random.randn(n) * 10
        
        # 预测
        result = forecaster.forecast(
            days=30,
            historical_data=data,
            historical_timestamps=timestamps.values
        )
        
        assert len(result.dates) == 30
        assert len(result.values) == 30
        assert result.confidence >= 0


class TestMetrics:
    """评估指标测试"""
    
    def test_classification_metrics(self):
        """测试分类指标"""
        from app.core.metrics import ClassificationMetrics
        
        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 1, 0, 2, 2])
        
        metrics = ClassificationMetrics()
        result = metrics.evaluate(y_true, y_pred)
        
        assert 0 <= result.accuracy <= 1
        assert result.confusion_matrix is not None
    
    def test_regression_metrics(self):
        """测试回归指标"""
        from app.core.metrics import RegressionMetrics
        
        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([110, 190, 310, 390, 510])
        
        metrics = RegressionMetrics()
        result = metrics.evaluate(y_true, y_pred)
        
        assert result.mae > 0
        assert result.rmse > 0
        assert result.r2 is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
