"""
螺栓预紧力机器学习预测系统 - 核心模块算法自动化测试

覆盖模块:
1. BoltLSTMModel - LSTM网络训练/预测/保存加载
2. EnsembleModel - 集成学习(三种预测器+三种投票)
3. FaultClassifier - 故障分类(松动/过载/断裂检测)
4. FlangeAttentionModel - 法兰面注意力模型
5. MultivariateModel - 多变量预测(温度耦合)
6. ProphetForecaster - Prophet时间序列预测
7. BayesianRiskModel - 贝叶斯风险评估
8. RuleBasedClassifier - 规则分类器
9. WarningStrategyPolicy - 预警策略
10. PredictionOrchestrator - 预测编排流水线
11. KalmanFilterService - 卡尔曼滤波
12. DataPreprocessor - 数据预处理
13. FeatureEngineer - 特征工程
14. AnomalyDetector - 异常检测
15. Metrics - 评估指标

用法:
    pytest tests/test_core_algorithms.py -v
    pytest tests/test_core_algorithms.py -v -k "TestBoltLSTM"
    pytest tests/test_core_algorithms.py -v -k "TestEnsemble"
"""

import pytest
import numpy as np
import torch
import tempfile
import os
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# BoltLSTMModel
# ============================================================

class TestBoltLSTMModelAlgorithms:
    """螺栓LSTM模型核心算法测试"""

    def test_lstm_network_output_shape(self):
        from app.models.bolt_lstm import LSTMNetwork

        network = LSTMNetwork(input_dim=2, lstm_units_1=64, lstm_units_2=32, output_classes=5)
        x = torch.randn(4, 100, 2)
        output = network(x)
        assert output.shape == (4, 5)

    def test_lstm_network_gradient_flow(self):
        from app.models.bolt_lstm import LSTMNetwork

        network = LSTMNetwork(input_dim=2, lstm_units_1=32, lstm_units_2=16, output_classes=5)
        x = torch.randn(2, 50, 2)
        output = network(x)
        loss = output.sum()
        loss.backward()
        for name, param in network.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"Gradient not computed for {name}"

    def test_prepare_data_1d_input(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        data_1d = np.random.randn(150)
        X, _ = model.prepare_data(data_1d, sequence_length=100)
        assert X.shape[1] == 100
        assert X.shape[2] == 2

    def test_prepare_data_2d_input(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        data_2d = np.random.randn(150, 2)
        X, _ = model.prepare_data(data_2d, sequence_length=100)
        assert X.shape[1] == 100
        assert X.shape[2] == 2

    def test_prepare_data_with_labels(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        data = np.random.randn(200)
        labels = np.random.randint(0, 5, 101)
        X, y = model.prepare_data(data, labels, sequence_length=100)
        assert y is not None
        assert len(y) == X.shape[0]

    def test_prepare_data_short_sequence(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        data = np.random.randn(50)
        X, _ = model.prepare_data(data, sequence_length=100)
        assert X.shape[1] == 100
        assert X.shape[0] == 1

    def test_predict_return_proba(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        data = np.random.randn(100) * 20 + 600
        pred_class, confidence, prob = model.predict(data, return_proba=True)
        assert 0 <= pred_class <= 4
        assert 0 <= confidence <= 1
        assert prob is not None
        assert len(prob) == 5
        assert abs(prob.sum() - 1.0) < 1e-5

    def test_predict_batch(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        data_list = [np.random.randn(100) * 20 + 600 for _ in range(5)]
        results = model.predict_batch(data_list)
        assert len(results) == 5
        for pred_class, confidence in results:
            assert 0 <= pred_class <= 4
            assert 0 <= confidence <= 1

    def test_train_with_small_data(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_train')
        np.random.seed(42)
        data = np.random.randn(300) * 20 + 600
        labels = np.random.randint(0, 5, 201)

        history = model.train(data, labels, epochs=3, batch_size=16, learning_rate=0.01)

        assert 'train_loss' in history
        assert 'val_loss' in history
        assert 'train_acc' in history
        assert 'val_acc' in history
        assert len(history['train_loss']) > 0
        assert model.is_trained

    def test_train_with_class_weights(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_cw')
        np.random.seed(42)
        data = np.random.randn(300) * 20 + 600
        labels = np.random.randint(0, 5, 201)
        class_weights = np.array([1.0, 2.0, 2.0, 3.0, 5.0])

        history = model.train(data, labels, epochs=2, batch_size=16, class_weights=class_weights)
        assert model.is_trained

    def test_save_and_load(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_save')
        np.random.seed(42)
        data = np.random.randn(300) * 20 + 600
        labels = np.random.randint(0, 5, 201)
        model.train(data, labels, epochs=2, batch_size=16)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = model.save(os.path.join(tmpdir, 'test_model.pt'))
            assert os.path.exists(path)

            loaded_model = BoltLSTMModel(bolt_id='test_loaded')
            loaded_model.load(path)
            assert loaded_model.is_trained

    def test_load_nonexistent_file(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test')
        with pytest.raises(FileNotFoundError):
            model.load('/nonexistent/path/model.pt')

    def test_get_recommendation_normal(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel()
        rec = model.get_recommendation(0, 0.95)
        assert '监测' in rec or '正常' in rec

    def test_get_recommendation_fault(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel()
        rec = model.get_recommendation(4, 0.95)
        assert '紧急' in rec or '停机' in rec

    def test_get_recommendation_low_confidence(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel()
        rec = model.get_recommendation(2, 0.5)
        assert '置信度较低' in rec


# ============================================================
# EnsembleModel
# ============================================================

class TestEnsembleModelAlgorithms:
    """集成学习模型核心算法测试"""

    def test_rule_based_predictor_normal(self):
        from app.models.ensemble_model import RuleBasedPredictor

        predictor = RuleBasedPredictor()
        data = np.random.randn(100) * 10 + 600
        pred_class, confidence, probs = predictor.predict(data)
        assert 0 <= pred_class <= 4
        assert 0 <= confidence <= 1
        assert len(probs) == 5
        assert abs(probs.sum() - 1.0) < 1e-5

    def test_rule_based_predictor_below_normal(self):
        from app.models.ensemble_model import RuleBasedPredictor

        predictor = RuleBasedPredictor()
        data = np.random.randn(100) * 10 + 200
        pred_class, confidence, probs = predictor.predict(data)
        assert pred_class >= 2

    def test_rule_based_predictor_above_normal(self):
        from app.models.ensemble_model import RuleBasedPredictor

        predictor = RuleBasedPredictor()
        data = np.random.randn(100) * 10 + 1100
        pred_class, confidence, probs = predictor.predict(data)
        assert pred_class >= 1

    def test_statistical_predictor(self):
        from app.models.ensemble_model import StatisticalPredictor

        predictor = StatisticalPredictor()
        data = np.random.randn(100) * 20 + 600
        pred_class, confidence, probs = predictor.predict(data)
        assert 0 <= pred_class <= 4
        assert len(probs) == 5

    def test_statistical_predictor_declining(self):
        from app.models.ensemble_model import StatisticalPredictor

        predictor = StatisticalPredictor()
        data = np.linspace(800, 200, 100)
        pred_class, confidence, probs = predictor.predict(data)
        assert pred_class >= 1

    def test_trend_predictor_stable(self):
        from app.models.ensemble_model import TrendPredictor

        predictor = TrendPredictor()
        data = np.random.randn(100) * 5 + 600
        pred_class, confidence, probs = predictor.predict(data)
        assert 0 <= pred_class <= 4

    def test_trend_predictor_declining(self):
        from app.models.ensemble_model import TrendPredictor

        predictor = TrendPredictor()
        data = np.linspace(800, 100, 100)
        pred_class, confidence, probs = predictor.predict(data)
        assert pred_class >= 1

    def test_trend_predictor_short_data(self):
        from app.models.ensemble_model import TrendPredictor

        predictor = TrendPredictor()
        data = np.array([600.0, 601.0])
        pred_class, confidence, probs = predictor.predict(data)
        assert pred_class == 0

    def test_hard_voting(self):
        from app.models.ensemble_model import EnsemblePredictor

        predictor = EnsemblePredictor(method='voting')
        data = np.random.randn(100) * 20 + 600
        result = predictor.predict(data)
        assert 0 <= result.final_prediction <= 4
        assert 0 <= result.final_confidence <= 1
        assert result.method == 'voting'

    def test_weighted_voting(self):
        from app.models.ensemble_model import EnsemblePredictor

        predictor = EnsemblePredictor(method='weighted_voting')
        data = np.random.randn(100) * 20 + 600
        result = predictor.predict(data)
        assert 0 <= result.final_prediction <= 4
        assert result.method == 'weighted_voting'

    def test_soft_voting(self):
        from app.models.ensemble_model import EnsemblePredictor

        predictor = EnsemblePredictor(method='soft_voting')
        data = np.random.randn(100) * 20 + 600
        result = predictor.predict(data)
        assert 0 <= result.final_prediction <= 4
        assert result.method == 'soft_voting'

    def test_custom_weights(self):
        from app.models.ensemble_model import EnsemblePredictor

        weights = {'rule_based': 0.5, 'statistical': 0.3, 'trend': 0.2}
        predictor = EnsemblePredictor(method='weighted_voting', weights=weights)
        total = sum(predictor.weights.values())
        assert abs(total - 1.0) < 1e-5

    def test_add_predictor(self):
        from app.models.ensemble_model import EnsemblePredictor, BasePredictor

        class DummyPredictor(BasePredictor):
            @property
            def name(self):
                return "dummy"
            def predict(self, data):
                return 0, 0.9, np.array([0.9, 0.025, 0.025, 0.025, 0.025])

        predictor = EnsemblePredictor()
        initial_count = len(predictor.predictors)
        predictor.add_predictor(DummyPredictor(), weight=2.0)
        assert len(predictor.predictors) == initial_count + 1

    def test_update_weights(self):
        from app.models.ensemble_model import EnsemblePredictor

        predictor = EnsemblePredictor()
        metrics = {'rule_based': 0.9, 'statistical': 0.7, 'trend': 0.5}
        predictor.update_weights(metrics)
        assert predictor.weights['rule_based'] > predictor.weights['trend']

    def test_predict_with_details(self):
        from app.models.ensemble_model import EnsemblePredictor

        predictor = EnsemblePredictor()
        data = np.random.randn(100) * 20 + 600
        details = predictor.predict_with_details(data)
        assert 'status' in details
        assert 'status_code' in details
        assert 'confidence' in details
        assert 'individual_results' in details
        assert 'weights' in details

    def test_ensemble_prediction_dataclass(self):
        from app.models.ensemble_model import EnsemblePrediction

        pred = EnsemblePrediction(
            final_prediction=0,
            final_confidence=0.9,
            individual_predictions={'a': 0, 'b': 1},
            individual_confidences={'a': 0.9, 'b': 0.7},
            weights={'a': 0.6, 'b': 0.4},
            method='weighted_voting'
        )
        assert pred.final_prediction == 0
        assert pred.method == 'weighted_voting'


# ============================================================
# FaultClassifier
# ============================================================

class TestFaultClassifierAlgorithms:
    """故障分类器核心算法测试"""

    def test_fault_pattern_extract(self):
        from app.models.fault_classifier import FaultPatternExtractor

        extractor = FaultPatternExtractor()
        data = np.random.randn(100) * 20 + 600
        pattern = extractor.extract(data)
        assert pattern.trend_slope is not None
        assert pattern.volatility >= 0
        assert pattern.sudden_changes >= 0
        assert pattern.min_value <= pattern.max_value

    def test_fault_pattern_to_dict(self):
        from app.models.fault_classifier import FaultPatternExtractor

        extractor = FaultPatternExtractor()
        data = np.random.randn(100) * 20 + 600
        pattern = extractor.extract(data)
        d = pattern.to_dict()
        assert 'trend_slope' in d
        assert 'volatility' in d

    def test_loosening_detector_positive(self):
        from app.models.fault_classifier import LooseningDetector, FaultPattern

        detector = LooseningDetector()
        pattern = FaultPattern(
            trend_slope=-1.0, volatility=0.05, sudden_changes=0,
            min_value=300, max_value=700, mean_value=500
        )
        is_loosening, score, evidence = detector.detect(pattern)
        assert score > 0
        assert len(evidence) > 0

    def test_loosening_detector_negative(self):
        from app.models.fault_classifier import LooseningDetector, FaultPattern

        detector = LooseningDetector()
        pattern = FaultPattern(
            trend_slope=0.01, volatility=0.02, sudden_changes=0,
            min_value=590, max_value=610, mean_value=600
        )
        is_loosening, score, evidence = detector.detect(pattern)
        assert score < 0.5

    def test_overload_detector_positive(self):
        from app.models.fault_classifier import OverloadDetector, FaultPattern

        detector = OverloadDetector(max_normal=800)
        pattern = FaultPattern(
            trend_slope=0.5, volatility=0.05, sudden_changes=1,
            min_value=800, max_value=1200, mean_value=1000
        )
        data = np.random.randn(100) * 20 + 1100
        is_overload, score, evidence = detector.detect(pattern, data)
        assert score > 0

    def test_overload_detector_negative(self):
        from app.models.fault_classifier import OverloadDetector, FaultPattern

        detector = OverloadDetector(max_normal=800)
        pattern = FaultPattern(
            trend_slope=0.01, volatility=0.03, sudden_changes=0,
            min_value=550, max_value=650, mean_value=600
        )
        data = np.random.randn(100) * 10 + 600
        is_overload, score, evidence = detector.detect(pattern, data)
        assert score < 0.5

    def test_fracture_detector_positive(self):
        from app.models.fault_classifier import FractureDetector, FaultPattern

        detector = FractureDetector(min_normal=400)
        pattern = FaultPattern(
            trend_slope=-5.0, volatility=0.5, sudden_changes=3,
            min_value=10, max_value=700, mean_value=200
        )
        data = np.concatenate([np.random.randn(80) * 20 + 600, np.linspace(600, 10, 20)])
        is_fracture, score, evidence = detector.detect(pattern, data)
        assert score > 0

    def test_fracture_detector_negative(self):
        from app.models.fault_classifier import FractureDetector, FaultPattern

        detector = FractureDetector(min_normal=400)
        pattern = FaultPattern(
            trend_slope=0.01, volatility=0.02, sudden_changes=0,
            min_value=550, max_value=650, mean_value=600
        )
        data = np.random.randn(100) * 10 + 600
        is_fracture, score, evidence = detector.detect(pattern, data)
        assert score < 0.5

    def test_classify_normal_data(self):
        from app.models.fault_classifier import FaultClassifier, FaultType

        classifier = FaultClassifier()
        data = np.random.randn(100) * 10 + 600
        result = classifier.classify(data)
        assert result.fault_type in [FaultType.NORMAL, FaultType.UNKNOWN]
        assert 1 <= result.severity <= 10
        assert len(result.evidence) > 0

    def test_classify_loosening_data(self):
        from app.models.fault_classifier import FaultClassifier, FaultType

        classifier = FaultClassifier()
        data = np.linspace(700, 200, 100)
        result = classifier.classify(data)
        assert result.confidence >= 0
        assert len(result.evidence) > 0

    def test_classify_fracture_data(self):
        from app.models.fault_classifier import FaultClassifier, FaultType

        classifier = FaultClassifier()
        data = np.concatenate([np.random.randn(80) * 20 + 600, np.linspace(600, 10, 20)])
        result = classifier.classify(data)
        assert result.confidence >= 0

    def test_fault_classification_result_fault_name(self):
        from app.models.fault_classifier import FaultClassificationResult, FaultType, FaultPattern

        pattern = FaultPattern(0, 0, 0, 0, 0, 0)
        result = FaultClassificationResult(
            fault_type=FaultType.LOOSENING, confidence=0.8, severity=5,
            pattern=pattern, evidence=["test"], recommendations=["test"]
        )
        assert result.fault_name == "松动"

    def test_batch_classify(self):
        from app.models.fault_classifier import FaultClassifier

        classifier = FaultClassifier()
        data_list = [np.random.randn(100) * 20 + 600 for _ in range(3)]
        node_ids = ['B001', 'B002', 'B003']
        results = classifier.classify_batch(data_list, node_ids)
        assert len(results) == 3
        assert 'B001' in results
        assert 'B002' in results
        assert 'B003' in results


# ============================================================
# FlangeAttentionModel
# ============================================================

class TestFlangeAttentionModelAlgorithms:
    """法兰面注意力模型核心算法测试"""

    def test_multi_head_self_attention_forward(self):
        from app.models.flange_attention import MultiHeadSelfAttention

        attention = MultiHeadSelfAttention(embed_dim=32, num_heads=4)
        x = torch.randn(2, 10, 32)
        output, weights = attention(x)
        assert output.shape == (2, 10, 32)
        assert weights.shape[0] == 2
        assert weights.shape[1] == 4

    def test_multi_head_attention_with_mask(self):
        from app.models.flange_attention import MultiHeadSelfAttention

        attention = MultiHeadSelfAttention(embed_dim=32, num_heads=4)
        x = torch.randn(2, 10, 32)
        mask = torch.ones(10)
        mask[5:] = 0
        output, weights = attention(x, mask=mask)
        assert output.shape == (2, 10, 32)

    def test_bolt_feature_extractor_bidirectional(self):
        from app.models.flange_attention import BoltFeatureExtractor

        extractor = BoltFeatureExtractor(input_dim=2, hidden_dim=64, output_dim=32)
        x = torch.randn(3, 50, 2)
        features = extractor(x)
        assert features.shape == (3, 32)

    def test_flange_attention_network_forward(self):
        from app.models.flange_attention import FlangeAttentionNetwork

        network = FlangeAttentionNetwork(
            max_bolts=5, input_dim=2, feature_dim=16,
            attention_heads=4, lstm_units=32, output_classes=5
        )
        x = torch.randn(2, 5, 50, 2)
        output, attn_weights = network(x)
        assert output.shape == (2, 5)
        assert attn_weights is not None

    def test_analyze_bolt_correlations(self):
        from app.models.flange_attention import FlangeAttentionModel

        model = FlangeAttentionModel(flange_id='test')
        bolt_data = {
            'B001': np.random.randn(100) * 20 + 600,
            'B002': np.random.randn(100) * 20 + 600,
            'B003': np.random.randn(100) * 20 + 600,
        }
        corr_matrix = model.analyze_bolt_correlations(bolt_data)
        assert corr_matrix.shape == (3, 3)
        for i in range(3):
            assert abs(corr_matrix[i, i] - 1.0) < 1e-5

    def test_prepare_data_padding(self):
        from app.models.flange_attention import FlangeAttentionModel

        model = FlangeAttentionModel(flange_id='test')
        multi_bolt_data = [np.random.randn(50) * 20 + 600 for _ in range(3)]
        X, _, mask = model.prepare_data(multi_bolt_data, sequence_length=100)
        assert X.shape[1] == 20
        assert mask.sum() == 3

    def test_predict_with_attention(self):
        from app.models.flange_attention import FlangeAttentionModel

        model = FlangeAttentionModel(flange_id='test')
        multi_bolt_data = [np.random.randn(100) * 20 + 600 for _ in range(3)]
        pred_class, confidence, attn = model.predict(multi_bolt_data, return_attention=True)
        assert 0 <= pred_class <= 4
        assert 0 <= confidence <= 1
        assert attn is not None

    def test_get_status_label(self):
        from app.models.flange_attention import FlangeAttentionModel

        model = FlangeAttentionModel()
        assert model.get_status_label(0) == '正常'
        assert model.get_status_label(4) == '故障'
        assert model.get_status_label(99) == '未知'

    def test_save_and_load(self):
        from app.models.flange_attention import FlangeAttentionModel

        model = FlangeAttentionModel(flange_id='test_save')
        with tempfile.TemporaryDirectory() as tmpdir:
            path = model.save(os.path.join(tmpdir, 'flange_model.pt'))
            assert os.path.exists(path)
            loaded = FlangeAttentionModel(flange_id='test_loaded')
            loaded.load(path)


# ============================================================
# MultivariateModel
# ============================================================

class TestMultivariateModelAlgorithms:
    """多变量预测模型核心算法测试"""

    def test_multivariate_input_n_features(self):
        from app.models.multivariate_model import MultivariateInput

        data = MultivariateInput(
            preload=np.random.randn(100),
            temperature=np.random.randn(100),
        )
        assert data.n_features == 2

        data2 = MultivariateInput(
            preload=np.random.randn(100),
            temperature=np.random.randn(100),
            humidity=np.random.randn(100),
            vibration=np.random.randn(100),
        )
        assert data2.n_features == 4

    def test_multivariate_input_to_array(self):
        from app.models.multivariate_model import MultivariateInput

        data = MultivariateInput(
            preload=np.random.randn(100),
            temperature=np.random.randn(100),
        )
        arr = data.to_array()
        assert arr.shape == (100, 2)

    def test_temperature_coupling_fit(self):
        from app.models.multivariate_model import TemperatureCouplingModel

        model = TemperatureCouplingModel()
        np.random.seed(42)
        temp = np.linspace(10, 50, 100)
        preload = 600 - 0.5 * (temp - 20) + np.random.randn(100) * 5
        result = model.fit(preload, temp)
        assert result is model
        assert model._fitted

    def test_temperature_coupling_compensate(self):
        from app.models.multivariate_model import TemperatureCouplingModel

        model = TemperatureCouplingModel()
        np.random.seed(42)
        temp = np.linspace(10, 50, 100)
        preload = 600 - 0.5 * (temp - 20) + np.random.randn(100) * 5
        model.fit(preload, temp)
        compensated = model.compensate(preload, temp)
        assert len(compensated) == len(preload)

    def test_temperature_coupling_analyze_effect(self):
        from app.models.multivariate_model import TemperatureCouplingModel

        model = TemperatureCouplingModel()
        np.random.seed(42)
        temp = np.linspace(10, 50, 100)
        preload = 600 - 2.0 * (temp - 20) + np.random.randn(100) * 5
        effect = model.analyze_effect(preload, temp)
        assert 'correlation' in effect
        assert 'coefficient' in effect
        assert 'effect_level' in effect
        assert effect['effect_level'] in ['可忽略', '轻微', '中等', '显著']

    def test_temperature_coupling_auto_fit_on_compensate(self):
        from app.models.multivariate_model import TemperatureCouplingModel

        model = TemperatureCouplingModel()
        assert not model._fitted
        temp = np.linspace(10, 50, 50)
        preload = 600 - 0.5 * (temp - 20)
        compensated = model.compensate(preload, temp)
        assert model._fitted

    def test_multivariate_lstm_forward(self):
        from app.models.multivariate_model import MultivariateLSTM

        model = MultivariateLSTM(input_dim=4, hidden_dim=64, num_layers=2, output_classes=5)
        x = torch.randn(2, 50, 4)
        output, attn_weights = model(x)
        assert output.shape == (2, 5)
        assert attn_weights.shape == (2, 50)

    def test_multivariate_predictor_predict(self):
        from app.models.multivariate_model import MultivariatePredictor, MultivariateInput

        predictor = MultivariatePredictor()
        data = MultivariateInput(
            preload=np.random.randn(150) * 20 + 600,
            temperature=np.random.randn(150) * 5 + 25,
        )
        result = predictor.predict(data)
        assert 0 <= result.status_code <= 4
        assert 0 <= result.confidence <= 1

    def test_multivariate_predictor_without_temp_compensation(self):
        from app.models.multivariate_model import MultivariatePredictor, MultivariateInput

        predictor = MultivariatePredictor()
        data = MultivariateInput(
            preload=np.random.randn(150) * 20 + 600,
            temperature=np.random.randn(150) * 5 + 25,
        )
        result = predictor.predict(data, apply_temp_compensation=False)
        assert result.temperature_effect == {}

    def test_temperature_data_processor_validate_valid(self):
        from app.models.multivariate_model import TemperatureDataProcessor

        processor = TemperatureDataProcessor()
        temp = np.random.randn(100) * 5 + 25
        is_valid, errors = processor.validate(temp)
        assert is_valid
        assert len(errors) == 0

    def test_temperature_data_processor_validate_empty(self):
        from app.models.multivariate_model import TemperatureDataProcessor

        processor = TemperatureDataProcessor()
        is_valid, errors = processor.validate(np.array([]))
        assert not is_valid

    def test_temperature_data_processor_validate_out_of_range(self):
        from app.models.multivariate_model import TemperatureDataProcessor

        processor = TemperatureDataProcessor()
        temp = np.array([200.0, -100.0, 25.0])
        is_valid, errors = processor.validate(temp)
        assert not is_valid

    def test_temperature_data_processor_validate_nan(self):
        from app.models.multivariate_model import TemperatureDataProcessor

        processor = TemperatureDataProcessor()
        temp = np.array([25.0, np.nan, 30.0])
        is_valid, errors = processor.validate(temp)
        assert not is_valid

    def test_temperature_data_processor_preprocess(self):
        from app.models.multivariate_model import TemperatureDataProcessor

        processor = TemperatureDataProcessor()
        temp = np.array([25.0, np.nan, 30.0, np.nan, 35.0])
        processed = processor.preprocess(temp, fill_method='linear')
        assert not np.any(np.isnan(processed))


# ============================================================
# ProphetForecaster
# ============================================================

class TestProphetForecasterAlgorithms:
    """Prophet预测器核心算法测试"""

    def _create_test_data(self, n=100):
        np.random.seed(42)
        timestamps = pd.date_range('2025-01-01', periods=n, freq='D')
        data = np.linspace(500, 600, n) + np.random.randn(n) * 10
        return data, timestamps

    def test_simple_forecast_basic(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        data, timestamps = self._create_test_data()
        result = forecaster.forecast(days=30, historical_data=data, historical_timestamps=timestamps.values)
        assert len(result.dates) == 30
        assert len(result.values) == 30
        assert len(result.lower_bound) == 30
        assert len(result.upper_bound) == 30
        assert 0 <= result.confidence <= 1

    def test_simple_forecast_confidence_bounds(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        data, timestamps = self._create_test_data()
        result = forecaster.forecast(days=15, historical_data=data, historical_timestamps=timestamps.values)
        for i in range(len(result.values)):
            assert result.lower_bound[i] <= result.values[i] <= result.upper_bound[i]

    def test_forecast_without_fitting(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        with pytest.raises(ValueError):
            forecaster.forecast(days=30)

    def test_predict_status(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        data, timestamps = self._create_test_data()
        result = forecaster.predict_status(data, timestamps.values, days=30)
        assert 'pw_type' in result
        assert 'confidence' in result
        assert 'rec_measures' in result

    def test_detect_anomaly_periods_normal(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        data, timestamps = self._create_test_data()
        result = forecaster.forecast(days=30, historical_data=data, historical_timestamps=timestamps.values)
        assert isinstance(result.anomaly_dates, list)
        assert isinstance(result.anomaly_type, str)

    def test_detect_anomaly_periods_declining(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        np.random.seed(42)
        n = 100
        timestamps = pd.date_range('2025-01-01', periods=n, freq='D')
        data = np.linspace(700, 100, n) + np.random.randn(n) * 5
        result = forecaster.forecast(days=30, historical_data=data, historical_timestamps=timestamps.values)
        assert isinstance(result.anomaly_dates, list)

    def test_calculate_forecast_confidence(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        values = np.array([500, 510, 520])
        lower = np.array([480, 490, 500])
        upper = np.array([520, 530, 540])
        confidence = forecaster._calculate_forecast_confidence(values, lower, upper)
        assert 0 <= confidence <= 1

    def test_determine_warning_type_normal(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        mock_result = MagicMock()
        mock_result.values = np.array([550, 560, 570])
        mock_result.anomaly_dates = []
        mock_result.anomaly_type = "正常"
        result = forecaster._determine_warning_type(mock_result)
        assert result == "正常"

    def test_generate_measures(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        for pw_type in ["正常", "关注级预警", "检查级预警", "紧急级预警", "故障"]:
            measures = forecaster._generate_measures(pw_type, None)
            assert len(measures) > 0

    def test_generate_measures_with_fault(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        measures = forecaster._generate_measures("紧急级预警", "松动")
        assert "松动" in measures

    def test_get_anomaly_timeframe_none(self):
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster()
        mock_result = MagicMock()
        mock_result.anomaly_dates = []
        begin, end = forecaster._get_anomaly_timeframe(mock_result)
        assert begin is None
        assert end is None


# ============================================================
# BayesianRiskModel
# ============================================================

class TestRiskModelAlgorithms:
    """贝叶斯风险评估模型核心算法测试"""

    def test_calculate_deviation_score_in_range(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 10 + 600
        score = model.calculate_deviation_score(data)
        assert 0 <= score <= 1
        assert score > 0.7

    def test_calculate_deviation_score_below_range(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 10 + 200
        score = model.calculate_deviation_score(data)
        assert 0 <= score <= 1
        assert score < 0.5

    def test_calculate_deviation_score_above_range(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 10 + 1200
        score = model.calculate_deviation_score(data)
        assert 0 <= score <= 1
        assert score < 0.5

    def test_calculate_volatility_score_stable(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 5 + 600
        score = model.calculate_volatility_score(data)
        assert score > 0.7

    def test_calculate_volatility_score_volatile(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 200 + 600
        score = model.calculate_volatility_score(data)
        assert score < 0.7

    def test_calculate_volatility_score_single_point(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.array([600.0])
        score = model.calculate_volatility_score(data)
        assert score == 1.0

    def test_calculate_trend_score_stable(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 5 + 600
        score = model.calculate_trend_score(data)
        assert score > 0.5

    def test_calculate_trend_score_declining(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data_stable = np.random.randn(100) * 5 + 600
        data_declining = np.linspace(800, 100, 100)
        score_stable = model.calculate_trend_score(data_stable)
        score_declining = model.calculate_trend_score(data_declining)
        assert score_declining < score_stable

    def test_calculate_trend_score_short_data(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.array([600.0, 601.0])
        score = model.calculate_trend_score(data)
        assert score == 1.0

    def test_calculate_extreme_score_normal(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 20 + 600
        score = model.calculate_extreme_score(data)
        assert score > 0.5

    def test_calculate_extreme_score_with_sudden_drop(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 20 + 600
        data[50] = 50
        score = model.calculate_extreme_score(data)
        assert score < 1.0

    def test_calculate_lstm_score(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        probs = np.array([0.8, 0.1, 0.05, 0.03, 0.02])
        score = model.calculate_lstm_score(probs)
        assert 0 <= score <= 1

    def test_calculate_lstm_score_none(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        score = model.calculate_lstm_score(None)
        assert score == 0.5

    def test_assess_risk_low(self):
        from app.models.risk_model import BayesianRiskModel, RiskLevel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 10 + 600
        result = model.assess_risk(data)
        assert 1 <= result.score <= 10
        assert result.level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert len(result.factors) > 0
        assert len(result.recommendations) > 0
        assert 0 <= result.confidence <= 1

    def test_assess_risk_high(self):
        from app.models.risk_model import BayesianRiskModel, RiskLevel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 100 + 200
        result = model.assess_risk(data)
        assert result.level in [RiskLevel.HIGH, RiskLevel.MEDIUM]

    def test_assess_risk_with_lstm_probs(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data = np.random.randn(100) * 10 + 600
        probs = np.array([0.8, 0.1, 0.05, 0.03, 0.02])
        result = model.assess_risk(data, lstm_probs=probs, lstm_class=0)
        assert result.confidence is not None

    def test_batch_assess(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data_list = [np.random.randn(100) * 20 + 600 for _ in range(5)]
        results = model.batch_assess(data_list)
        assert len(results) == 5

    def test_batch_assess_with_lstm(self):
        from app.models.risk_model import BayesianRiskModel

        model = BayesianRiskModel()
        data_list = [np.random.randn(100) * 20 + 600 for _ in range(3)]
        lstm_results = [(0, np.array([0.8, 0.1, 0.05, 0.03, 0.02])) for _ in range(3)]
        results = model.batch_assess(data_list, lstm_results)
        assert len(results) == 3


# ============================================================
# RuleBasedClassifier & WarningStrategyPolicy
# ============================================================

class TestRuleBasedClassifierAlgorithms:
    """规则分类器核心算法测试"""

    def test_predict_normal(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        data = np.random.randn(100) * 10 + 600
        status, confidence, probs = classifier.predict(data)
        assert status == 0
        assert confidence > 0.5

    def test_predict_attention_warning(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        data = np.random.randn(100) * 150 + 600
        status, confidence, probs = classifier.predict(data)
        assert status >= 1

    def test_predict_check_warning(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        data = np.random.randn(100) * 10 + 350
        status, confidence, probs = classifier.predict(data)
        assert status >= 2

    def test_predict_urgent_warning(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        data = np.random.randn(100) * 10 + 250
        status, confidence, probs = classifier.predict(data)
        assert status >= 3

    def test_predict_fault_below(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        data = np.random.randn(100) * 10 + 100
        status, confidence, probs = classifier.predict(data)
        assert status == 4

    def test_predict_fault_above(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        data = np.random.randn(100) * 10 + 1400
        status, confidence, probs = classifier.predict(data)
        assert status == 4

    def test_aggregate_predictions(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        multi_bolt_data = [
            np.random.randn(100) * 10 + 600,
            np.random.randn(100) * 10 + 350,
            np.random.randn(100) * 10 + 600,
        ]
        status, confidence = classifier.aggregate_predictions(multi_bolt_data)
        assert 0 <= status <= 4

    def test_aggregate_predictions_empty(self):
        from app.services.prediction.rule_classifier import RuleBasedClassifier

        classifier = RuleBasedClassifier()
        status, confidence = classifier.aggregate_predictions([])
        assert status == 0


class TestWarningStrategyPolicyAlgorithms:
    """预警策略核心算法测试"""

    def test_report_all_high_confidence(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=1)
        code, label = policy.apply(3, '紧急级预警', 0.9)
        assert code == 3

    def test_report_all_low_confidence(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=1)
        code, label = policy.apply(3, '紧急级预警', 0.3)
        assert code == 2

    def test_report_all_zero_not_negative(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=1)
        code, label = policy.apply(0, '正常', 0.3)
        assert code == 0

    def test_precise_high_confidence(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=2)
        code, label = policy.apply(3, '紧急级预警', 0.99)
        assert code == 3

    def test_precise_low_confidence(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=2)
        code, label = policy.apply(3, '紧急级预警', 0.5)
        assert code == 0
        assert label == '正常'

    def test_precise_normal_stays_normal(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=2)
        code, label = policy.apply(0, '正常', 0.3)
        assert code == 0

    def test_default_strategy_from_config(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy()
        assert policy.strategy_type in [1, 2]


# ============================================================
# PredictionOrchestrator
# ============================================================

class TestPredictionOrchestratorAlgorithms:
    """预测编排器核心算法测试"""

    def test_init_default_components(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        assert orch.preprocessor is not None
        assert orch.feature_engineer is not None
        assert orch.risk_model is not None
        assert orch.rule_classifier is not None
        assert orch.warning_policy is not None

    def test_predict_bolt_returns_required_fields(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        data = np.random.randn(100) * 20 + 600
        result = orch.predict_bolt('B001', data, save_to_db=False)
        assert 'bolt_id' in result
        assert 'status' in result
        assert 'status_code' in result
        assert 'confidence' in result
        assert 'risk_score' in result
        assert 'risk_level' in result

    def test_predict_bolt_with_timestamps(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        data = np.random.randn(100) * 20 + 600
        timestamps = [f"20250101 {i:02d}:00:00" for i in range(100)]
        result = orch.predict_bolt('B001', data, timestamps=timestamps, save_to_db=False)
        assert result['recent_time'] == timestamps[-1]

    def test_predict_flange_returns_required_fields(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        multi_bolt_data = [np.random.randn(100) * 20 + 600 for _ in range(3)]
        result = orch.predict_flange('F001', multi_bolt_data, save_to_db=False)
        assert 'flange_id' in result
        assert 'status' in result
        assert 'status_code' in result
        assert 'confidence' in result
        assert 'risk_score' in result

    def test_assess_risk_standalone(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        data = np.random.randn(100) * 20 + 600
        result = orch.assess_risk('B001', 'bolt', data)
        assert 'node_id' in result
        assert 'risk_score' in result
        assert 'risk_level' in result
        assert 'factors' in result

    def test_predict_bolt_model_caching(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        model1 = orch.get_bolt_model('cache_test')
        model2 = orch.get_bolt_model('cache_test')
        assert model1 is model2

    def test_predict_flange_model_caching(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        model1 = orch.get_flange_model('flange_cache_test')
        model2 = orch.get_flange_model('flange_cache_test')
        assert model1 is model2

    def test_predict_bolt_status_code_range(self):
        from app.services.prediction.orchestrator import PredictionOrchestrator

        orch = PredictionOrchestrator()
        data = np.random.randn(100) * 20 + 600
        result = orch.predict_bolt('B_RANGE', data, save_to_db=False)
        assert 0 <= result['status_code'] <= 4


# ============================================================
# KalmanFilterService
# ============================================================

class TestKalmanFilterServiceAlgorithms:
    """卡尔曼滤波服务核心算法测试"""

    def test_standard_filter(self):
        from app.services.kalman_filter import KalmanFilterService

        service = KalmanFilterService()
        np.random.seed(42)
        data = np.random.randn(50) * 10 + 600
        result = service.smooth(data, method='standard')
        assert len(result) == len(data)

    def test_adaptive_filter(self):
        from app.services.kalman_filter import KalmanFilterService

        service = KalmanFilterService()
        np.random.seed(42)
        data = np.random.randn(50) * 10 + 600
        result = service.smooth(data, method='adaptive')
        assert len(result) == len(data)

    def test_rts_smoother(self):
        from app.services.kalman_filter import KalmanFilterService

        service = KalmanFilterService()
        np.random.seed(42)
        data = np.random.randn(50) * 10 + 600
        result = service.smooth(data, method='rts')
        assert len(result) == len(data)

    def test_unknown_method_fallback(self):
        from app.services.kalman_filter import KalmanFilterService

        service = KalmanFilterService()
        data = np.random.randn(20) * 10 + 600
        result = service.smooth(data, method='unknown')
        assert len(result) == len(data)

    def test_empty_data(self):
        from app.services.kalman_filter import KalmanFilterService

        service = KalmanFilterService()
        result = service.smooth(np.array([]))
        assert len(result) == 0

    def test_kalman_filter_1d_predict_step(self):
        from app.services.kalman_filter import KalmanFilter1D

        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=0.1, initial_estimate=100.0)
        x_pred, P_pred = kf.predict()
        assert x_pred == 100.0
        assert P_pred == 1.01

    def test_kalman_filter_1d_update_step(self):
        from app.services.kalman_filter import KalmanFilter1D

        kf = KalmanFilter1D(process_noise=0.01, measurement_noise=0.1)
        state = kf.update(100.0)
        assert isinstance(state.estimate, float)
        assert isinstance(state.kalman_gain, float)

    def test_adaptive_kalman_noise_adaptation(self):
        from app.services.kalman_filter import AdaptiveKalmanFilter

        kf = AdaptiveKalmanFilter(base_process_noise=0.01, base_measurement_noise=0.1)
        data = np.random.randn(50) * 20 + 600
        result = kf.filter(data)
        assert len(result.smoothed_data) == 50

    def test_smooth_with_details(self):
        from app.services.kalman_filter import KalmanFilterService

        service = KalmanFilterService()
        data = np.random.randn(50) * 10 + 600
        result = service.smooth_with_details(data, method='standard')
        assert result.smoothed_data is not None
        assert result.kalman_gains is not None
        assert result.error_covariances is not None
        assert result.innovations is not None


# ============================================================
# DataPreprocessor
# ============================================================

class TestDataPreprocessorAlgorithms:
    """数据预处理器核心算法测试"""

    def test_normalize_minmax(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        data = np.array([100, 200, 300, 400, 500])
        normalized = preprocessor.normalize(data)
        assert normalized.min() >= 0
        assert normalized.max() <= 1

    def test_denormalize(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        data = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        normalized = preprocessor.normalize(data)
        denormalized = preprocessor.denormalize(normalized)
        np.testing.assert_array_almost_equal(denormalized, data, decimal=5)

    def test_normalize_without_fit(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        train = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        preprocessor.normalize(train, fit=True)
        test = np.array([150.0, 250.0, 350.0])
        result = preprocessor.normalize(test, fit=False)
        assert result is not None

    def test_detect_anomalies(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        normal, anomalies, indices = preprocessor.detect_anomalies(data)
        assert len(normal) + len(anomalies) <= len(data)

    def test_smooth(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        data = np.random.randn(100) * 10 + 600
        smoothed = preprocessor.smooth(data)
        assert len(smoothed) == len(data)

    def test_process_full_pipeline(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        data = np.random.randn(100) * 20 + 600
        result = preprocessor.process(data, remove_anomalies=True, normalize=True, smooth=True)
        assert result.data is not None
        assert result.scaler is not None

    def test_process_without_normalize(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        data = np.random.randn(100) * 20 + 600
        result = preprocessor.process(data, normalize=False, smooth=True)
        assert result.scaler is None

    def test_process_without_smooth(self):
        from app.services.preprocessing import DataPreprocessor

        preprocessor = DataPreprocessor()
        data = np.random.randn(100) * 20 + 600
        result = preprocessor.process(data, normalize=False, smooth=False, remove_anomalies=False)
        assert len(result.data) == len(data)

    def test_kalman_filter_in_preprocessing(self):
        from app.services.preprocessing import KalmanFilter

        kf = KalmanFilter(process_noise=0.01, measurement_noise=0.1)
        kf.reset(100.0)
        result = kf.update(105.0)
        assert 100.0 < result < 105.0


# ============================================================
# FeatureEngineer
# ============================================================

class TestFeatureEngineerAlgorithms:
    """特征工程核心算法测试"""

    def test_extract_temporal_features(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(100) * 20 + 600
        features, names = engineer.extract_temporal_features(data)
        assert 'trend_slope' in names
        assert 'rolling_mean_5' in names
        assert 'fft_dominant_freq' in names
        assert 'autocorr_lag1' in names

    def test_extract_statistical_features(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(100) * 20 + 600
        features, names = engineer.extract_statistical_features(data)
        assert 'mean' in names
        assert 'std' in names
        assert 'skewness' in names
        assert 'kurtosis' in names
        assert 'iqr' in names

    def test_extract_domain_features_normal(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(100) * 10 + 600
        features, names = engineer.extract_domain_features(data)
        assert 'safety_deviation_ratio' in names
        assert features[0] == 0.0

    def test_extract_domain_features_abnormal(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(100) * 10 + 200
        features, names = engineer.extract_domain_features(data)
        assert features[0] > 0

    def test_extract_features_combined(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(100) * 20 + 600
        feature_set = engineer.extract_features(data)
        assert len(feature_set.combined_features) == len(feature_set.feature_names)
        assert feature_set.temporal_features is not None
        assert feature_set.statistical_features is not None
        assert feature_set.domain_features is not None

    def test_extract_sequence_features(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(200) * 20 + 600
        sequences = engineer.extract_sequence_features(data, sequence_length=100)
        assert sequences.shape[1] == 100
        assert sequences.shape[2] == 2

    def test_extract_sequence_features_short_data(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.random.randn(50) * 20 + 600
        sequences = engineer.extract_sequence_features(data, sequence_length=100)
        assert sequences.shape[0] == 1
        assert sequences.shape[1] == 100

    def test_fourier_features_short_data(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.array([1.0, 2.0])
        features = engineer._fourier_features(data)
        assert len(features) == 4

    def test_autocorrelation(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.sin(np.linspace(0, 4 * np.pi, 100))
        autocorr = engineer._autocorrelation(data, lag=1)
        assert abs(autocorr) <= 1.01

    def test_autocorrelation_constant_data(self):
        from app.services.feature_engineering import FeatureEngineer

        engineer = FeatureEngineer()
        data = np.ones(100)
        autocorr = engineer._autocorrelation(data, lag=1)
        assert autocorr == 0.0


# ============================================================
# AnomalyDetector
# ============================================================

class TestAnomalyDetectorAlgorithms:
    """异常检测核心算法测试"""

    def test_isolation_forest_fit_predict(self):
        from app.services.anomaly_detection import IsolationForestDetector

        np.random.seed(42)
        data = np.random.randn(200) * 20 + 600
        data[100] = 2000
        data[150] = -100
        detector = IsolationForestDetector(contamination=0.05)
        detector.fit(data)
        labels, scores = detector.predict(data)
        assert len(labels) == len(data)
        assert len(scores) == len(data)

    def test_isolation_forest_detect(self):
        from app.services.anomaly_detection import IsolationForestDetector

        np.random.seed(42)
        data = np.random.randn(200) * 20 + 600
        data[100] = 2000
        detector = IsolationForestDetector(contamination=0.05)
        result = detector.detect(data)
        assert result.total_points == 200
        assert result.anomaly_count > 0
        assert len(result.cleaned_data) < 200

    def test_zscore_detection(self):
        from app.services.anomaly_detection import StatisticalAnomalyDetector

        np.random.seed(42)
        data = np.random.randn(100) * 10 + 500
        data[50] = 1000
        detector = StatisticalAnomalyDetector(zscore_threshold=3.0)
        mask, scores = detector.detect_zscore(data)
        assert mask[50] == True

    def test_iqr_detection(self):
        from app.services.anomaly_detection import StatisticalAnomalyDetector

        np.random.seed(42)
        data = np.random.randn(100) * 10 + 500
        data[50] = 2000
        detector = StatisticalAnomalyDetector(iqr_multiplier=1.5)
        mask, bounds = detector.detect_iqr(data)
        assert mask[50] == True
        assert bounds[0] < bounds[1]

    def test_sudden_change_detection(self):
        from app.services.anomaly_detection import StatisticalAnomalyDetector

        data = np.concatenate([np.ones(50) * 500, np.ones(50) * 800])
        detector = StatisticalAnomalyDetector()
        mask = detector.detect_sudden_change(data, threshold_ratio=0.3)
        assert mask[50] == True

    def test_sudden_change_short_data(self):
        from app.services.anomaly_detection import StatisticalAnomalyDetector

        data = np.array([500.0])
        detector = StatisticalAnomalyDetector()
        mask = detector.detect_sudden_change(data)
        assert len(mask) == 1
        assert not mask[0]

    def test_combined_detector_all_methods(self):
        from app.services.anomaly_detection import AnomalyDetector

        np.random.seed(42)
        data = np.random.randn(200) * 20 + 600
        data[100] = 2000
        data[150] = -100
        detector = AnomalyDetector()
        result = detector.detect(data)
        assert result.anomaly_count > 0

    def test_combined_detector_selective_methods(self):
        from app.services.anomaly_detection import AnomalyDetector

        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        detector = AnomalyDetector()
        result_zscore = detector.detect(data, methods=['zscore'])
        result_all = detector.detect(data, methods=['isolation_forest', 'zscore', 'iqr', 'range', 'sudden_change'])
        assert result_all.anomaly_count >= result_zscore.anomaly_count

    def test_range_detection(self):
        from app.services.anomaly_detection import AnomalyDetector

        data = np.random.randn(100) * 20 + 600
        data[50] = 2000
        data[75] = 50
        detector = AnomalyDetector()
        result = detector.detect(data, methods=['range'])
        assert result.anomaly_count >= 2

    def test_anomaly_record_dataclass(self):
        from app.services.anomaly_detection import AnomalyRecord, AnomalyType

        record = AnomalyRecord(
            index=10, value=999.0, anomaly_type=AnomalyType.ZSCORE,
            score=3.5, details={'zscore': 3.5}
        )
        assert record.index == 10
        assert record.anomaly_type == AnomalyType.ZSCORE


# ============================================================
# Metrics
# ============================================================

class TestMetricsAlgorithms:
    """评估指标核心算法测试"""

    def test_classification_metrics_evaluate(self):
        from app.core.metrics import ClassificationMetrics

        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 1, 1, 0, 2, 2])
        metrics = ClassificationMetrics()
        result = metrics.evaluate(y_true, y_pred)
        assert 0 <= result.accuracy <= 1
        assert result.confusion_matrix is not None
        assert result.per_class_metrics is not None

    def test_classification_with_probabilities(self):
        from app.core.metrics import ClassificationMetrics

        y_true = np.array([0, 1, 2, 0])
        y_proba = np.array([
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.7, 0.2, 0.1],
        ])
        metrics = ClassificationMetrics(class_names=['A', 'B', 'C'])
        result = metrics.evaluate_with_probabilities(y_true, y_proba)
        assert 'classification_result' in result
        assert 'mean_confidence' in result

    def test_regression_metrics(self):
        from app.core.metrics import RegressionMetrics

        y_true = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
        y_pred = np.array([110.0, 190.0, 310.0, 390.0, 510.0])
        metrics = RegressionMetrics()
        result = metrics.evaluate(y_true, y_pred)
        assert result.mae > 0
        assert result.rmse > 0
        assert result.mse > 0
        assert result.r2 is not None
        assert result.mape is not None

    def test_regression_metrics_zero_true(self):
        from app.core.metrics import RegressionMetrics

        y_true = np.array([0.0, 0.0, 0.0])
        y_pred = np.array([1.0, 2.0, 3.0])
        metrics = RegressionMetrics()
        result = metrics.evaluate(y_true, y_pred)
        assert result.mape is None

    def test_time_series_metrics(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([100, 200, 300, 400, 500])
        y_pred = np.array([110, 190, 310, 390, 510])
        metrics = TimeSeriesMetrics()
        result = metrics.evaluate(y_true, y_pred)
        assert 'mae' in result
        assert 'rmse' in result
        assert 'mape' in result
        assert 'smape' in result
        assert 'directional_accuracy' in result

    def test_time_series_mape(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([100, 200, 300])
        y_pred = np.array([110, 210, 290])
        mape = TimeSeriesMetrics.mape(y_true, y_pred)
        assert mape >= 0

    def test_time_series_smape(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([100, 200, 300])
        y_pred = np.array([110, 210, 290])
        smape = TimeSeriesMetrics.smape(y_true, y_pred)
        assert smape >= 0

    def test_directional_accuracy(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([100, 200, 300, 200, 100])
        y_pred = np.array([110, 210, 310, 210, 110])
        accuracy = TimeSeriesMetrics.directional_accuracy(y_true, y_pred)
        assert accuracy == 1.0

    def test_directional_accuracy_short_data(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([100.0])
        y_pred = np.array([110.0])
        accuracy = TimeSeriesMetrics.directional_accuracy(y_true, y_pred)
        assert accuracy == 0.0

    def test_model_evaluator_classification(self):
        from app.core.metrics import ModelEvaluator

        evaluator = ModelEvaluator()
        y_true = np.array([0, 1, 2, 0, 1])
        y_pred = np.array([0, 1, 1, 0, 2])
        result = evaluator.evaluate_classification(y_true, y_pred)
        assert 'accuracy' in result
        assert 'f1' in result

    def test_model_evaluator_regression(self):
        from app.core.metrics import ModelEvaluator

        evaluator = ModelEvaluator()
        y_true = np.array([100.0, 200.0, 300.0])
        y_pred = np.array([110.0, 190.0, 310.0])
        result = evaluator.evaluate_regression(y_true, y_pred)
        assert 'mae' in result
        assert 'r2' in result

    def test_model_evaluator_timeseries(self):
        from app.core.metrics import ModelEvaluator

        evaluator = ModelEvaluator()
        y_true = np.array([100, 200, 300, 400])
        y_pred = np.array([110, 190, 310, 390])
        result = evaluator.evaluate_timeseries(y_true, y_pred)
        assert 'directional_accuracy' in result

    def test_model_evaluator_generate_report(self):
        from app.core.metrics import ModelEvaluator

        evaluator = ModelEvaluator()
        y_true = np.array([0, 1, 2, 0])
        y_pred = np.array([0, 1, 1, 0])
        report = evaluator.generate_report('classification', y_true, y_pred)
        assert 'model_type' in report
        assert 'metrics' in report

    def test_model_evaluator_unknown_type(self):
        from app.core.metrics import ModelEvaluator

        evaluator = ModelEvaluator()
        with pytest.raises(ValueError):
            evaluator.generate_report('unknown', np.array([1]), np.array([1]))

    def test_time_series_mape_zero_denominator(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([0.0, 0.0])
        y_pred = np.array([1.0, 2.0])
        mape = TimeSeriesMetrics.mape(y_true, y_pred)
        assert mape == 0.0

    def test_time_series_smape_zero_denominator(self):
        from app.core.metrics import TimeSeriesMetrics

        y_true = np.array([0.0, 0.0])
        y_pred = np.array([0.0, 0.0])
        smape = TimeSeriesMetrics.smape(y_true, y_pred)
        assert smape == 0.0


# ============================================================
# Integration Tests - Cross-module
# ============================================================

class TestCrossModuleIntegration:
    """跨模块集成测试"""

    def test_preprocessing_to_prediction_pipeline(self):
        from app.services.preprocessing import DataPreprocessor
        from app.models.bolt_lstm import BoltLSTMModel

        np.random.seed(42)
        raw_data = np.random.randn(200) * 20 + 600

        preprocessor = DataPreprocessor()
        processed = preprocessor.process(raw_data, remove_anomalies=True, normalize=False, smooth=True)

        model = BoltLSTMModel(bolt_id='integration_test')
        pred_class, confidence, _ = model.predict(processed.data)
        assert 0 <= pred_class <= 4

    def test_feature_engineering_to_risk_assessment(self):
        from app.services.feature_engineering import FeatureEngineer
        from app.models.risk_model import BayesianRiskModel

        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        engineer = FeatureEngineer()
        features = engineer.extract_features(data)
        assert features.combined_features is not None

        risk_model = BayesianRiskModel()
        assessment = risk_model.assess_risk(data)
        assert 1 <= assessment.score <= 10

    def test_fault_classifier_with_risk_model(self):
        from app.models.fault_classifier import FaultClassifier
        from app.models.risk_model import BayesianRiskModel

        np.random.seed(42)
        data = np.concatenate([np.random.randn(80) * 20 + 600, np.linspace(600, 50, 20)])
        classifier = FaultClassifier()
        fault_result = classifier.classify(data)
        assert fault_result.severity >= 1

        risk_model = BayesianRiskModel()
        risk_result = risk_model.assess_risk(data)
        assert risk_result.score is not None

    def test_ensemble_with_warning_strategy(self):
        from app.models.ensemble_model import EnsemblePredictor
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        np.random.seed(42)
        data = np.random.randn(100) * 20 + 600
        predictor = EnsemblePredictor(method='weighted_voting')
        ensemble_result = predictor.predict(data)

        policy = WarningStrategyPolicy(strategy_type=1)
        adjusted_code, adjusted_label = policy.apply(
            ensemble_result.final_prediction,
            'test',
            ensemble_result.final_confidence
        )
        assert 0 <= adjusted_code <= 4

    def test_kalman_then_anomaly_detection(self):
        from app.services.kalman_filter import KalmanFilterService
        from app.services.anomaly_detection import AnomalyDetector

        np.random.seed(42)
        data = np.random.randn(200) * 20 + 600
        data[100] = 2000

        service = KalmanFilterService()
        smoothed = service.smooth(data, method='standard')

        detector = AnomalyDetector()
        result = detector.detect(smoothed, methods=['zscore', 'iqr'])
        assert result.total_points > 0

    def test_temperature_coupling_with_prediction(self):
        from app.models.multivariate_model import TemperatureCouplingModel, MultivariatePredictor, MultivariateInput

        np.random.seed(42)
        temp = np.linspace(10, 50, 150)
        preload = 600 - 0.5 * (temp - 20) + np.random.randn(150) * 10

        coupling = TemperatureCouplingModel()
        coupling.fit(preload, temp)
        compensated = coupling.compensate(preload, temp)
        assert len(compensated) == len(preload)

        mv_input = MultivariateInput(preload=preload, temperature=temp)
        predictor = MultivariatePredictor()
        result = predictor.predict(mv_input)
        assert 0 <= result.status_code <= 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# ============================================================
# Uncertainty Quantification (MC Dropout)
# ============================================================

class TestMCDropoutUncertainty:
    """Monte Carlo Dropout 不确定性量化测试"""

    def test_predict_with_uncertainty_output_keys(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        result = model.predict_with_uncertainty(data, n_samples=10)

        expected_keys = [
            'predicted_class', 'status_prob_mean', 'status_prob_std',
            'epistemic_uncertainty', 'confidence', 'confidence_lower',
            'confidence_upper', 'n_samples', 'all_probs',
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_predict_with_uncertainty_shapes(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        result = model.predict_with_uncertainty(data, n_samples=15)

        assert result['status_prob_mean'].shape == (5,)
        assert result['status_prob_std'].shape == (5,)
        assert result['all_probs'].shape == (15, 5)
        assert result['n_samples'] == 15

    def test_predict_with_uncertainty_probability_sums_to_one(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        result = model.predict_with_uncertainty(data, n_samples=10)

        assert abs(result['status_prob_mean'].sum() - 1.0) < 1e-5

    def test_predict_with_uncertainty_confidence_bounds(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        result = model.predict_with_uncertainty(data, n_samples=20)

        assert result['confidence_lower'] <= result['confidence']
        assert result['confidence_upper'] >= result['confidence']

    def test_predict_with_uncertainty_epistemic_non_negative(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        result = model.predict_with_uncertainty(data, n_samples=10)

        assert result['epistemic_uncertainty'] >= 0.0

    def test_predict_with_uncertainty_minimum_samples(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        result = model.predict_with_uncertainty(data, n_samples=1)
        assert result['n_samples'] >= 2

    def test_predict_with_uncertainty_with_features(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty_fe', feature_dim=8)
        data = np.random.randn(100) * 20 + 600
        features = np.random.randn(8).astype(np.float32)

        result = model.predict_with_uncertainty(data, n_samples=5, features=features)
        assert 'status_prob_mean' in result
        assert result['status_prob_mean'].shape == (5,)

    def test_predict_with_uncertainty_model_returns_eval_mode(self):
        from app.models.bolt_lstm import BoltLSTMModel

        model = BoltLSTMModel(bolt_id='test_uncertainty')
        data = np.random.randn(100) * 20 + 600

        _ = model.predict_with_uncertainty(data, n_samples=5)

        assert not model.model.training


class TestUncertaintyStrategyLinkage:
    """不确定性策略联动测试"""

    def test_strategy_two_high_uncertainty_medium_risk_manual_review(self):
        from app.services.prediction.warning_strategy import (
            WarningStrategyPolicy,
            STATUS_MANUAL_REVIEW,
            STATUS_LABEL_MANUAL_REVIEW,
        )

        policy = WarningStrategyPolicy(strategy_type=2)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.96,
            risk_level='中',
            lstm_confidence=0.8,
            epistemic_uncertainty=0.4,
        )
        assert code == STATUS_MANUAL_REVIEW
        assert status == STATUS_LABEL_MANUAL_REVIEW

    def test_strategy_two_critical_uncertainty_manual_review(self):
        from app.services.prediction.warning_strategy import (
            WarningStrategyPolicy,
            STATUS_MANUAL_REVIEW,
            STATUS_LABEL_MANUAL_REVIEW,
        )

        policy = WarningStrategyPolicy(strategy_type=2)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.96,
            risk_level='高',
            lstm_confidence=0.8,
            epistemic_uncertainty=0.6,
        )
        assert code == STATUS_MANUAL_REVIEW
        assert status == STATUS_LABEL_MANUAL_REVIEW

    def test_strategy_two_normal_uncertainty_not_triggered(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=2)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.96,
            risk_level='中',
            lstm_confidence=0.8,
            epistemic_uncertainty=0.1,
        )
        assert code == 2

    def test_strategy_one_critical_uncertainty_manual_review(self):
        from app.services.prediction.warning_strategy import (
            WarningStrategyPolicy,
            STATUS_MANUAL_REVIEW,
            STATUS_LABEL_MANUAL_REVIEW,
        )

        policy = WarningStrategyPolicy(strategy_type=1)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.8,
            epistemic_uncertainty=0.6,
        )
        assert code == STATUS_MANUAL_REVIEW
        assert status == STATUS_LABEL_MANUAL_REVIEW

    def test_strategy_one_normal_uncertainty(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=1)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.8,
            epistemic_uncertainty=0.1,
        )
        assert code == 2

    def test_classify_uncertainty_levels(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        result_normal = WarningStrategyPolicy.classify_uncertainty(0.1)
        assert result_normal['level'] == 'normal'

        result_high = WarningStrategyPolicy.classify_uncertainty(0.35)
        assert result_high['level'] == 'high'

        result_critical = WarningStrategyPolicy.classify_uncertainty(0.6)
        assert result_critical['level'] == 'critical'

    def test_strategy_two_high_uncertainty_high_risk_not_medium_risk(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=2)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.96,
            risk_level='高',
            lstm_confidence=0.8,
            epistemic_uncertainty=0.35,
        )
        assert code == 2

    def test_strategy_two_no_uncertainty_backward_compatible(self):
        from app.services.prediction.warning_strategy import WarningStrategyPolicy

        policy = WarningStrategyPolicy(strategy_type=2)

        code, status = policy.apply(
            status_code=2,
            status='检查级预警',
            confidence=0.96,
            risk_level='中',
            lstm_confidence=0.3,
        )
        assert code == 0
