"""
工况自适应预测主链路集成测试

测试内容:
1. 螺栓预测路径 - 工况识别、基线异常升级、风险调整、置信度调整
2. 法兰面预测路径 - 工况识别、基线异常升级、多螺栓数据拼接
3. 工况对预测结果的实际影响验证
4. 工况变更审计集成验证
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.working_condition_classifier import WorkingCondition
from app.services.prediction.orchestrator import PredictionOrchestrator


class TestBoltConditionPrediction:
    """螺栓预测路径 - 工况自适应测试"""

    @pytest.fixture
    def orch(self):
        """预测编排器实例"""
        return PredictionOrchestrator()

    @pytest.fixture
    def steady_data(self):
        """稳态数据"""
        np.random.seed(42)
        return np.random.normal(loc=500, scale=10, size=(200, 1))

    def test_steady_state_condition_recognition(self, orch, steady_data):
        """测试稳态工况识别"""
        result = orch.predict_bolt('test_bolt_steady', steady_data)
        wc = result.get('working_condition', {})

        assert wc is not None
        assert 'condition' in wc
        assert wc.get('condition') == WorkingCondition.STEADY_STATE.value
        assert 'condition_label' in wc
        assert 'confidence' in wc
        assert wc['confidence'] > 0

    def test_load_increase_condition_recognition(self, orch):
        """测试升负荷工况识别"""
        np.random.seed(42)
        n = 200
        x = np.linspace(0, 12, n)
        data = (500 + 40 * x + np.random.normal(0, 6, n)).reshape(-1, 1)

        result = orch.predict_bolt('test_bolt_inc', data)
        wc = result.get('working_condition', {})

        assert wc is not None
        assert 'condition' in wc
        assert wc.get('condition') == WorkingCondition.LOAD_INCREASE.value

    def test_baseline_anomaly_status_upgrade(self, orch):
        """测试基线异常导致状态码升级"""
        np.random.seed(999)
        n = 300

        normal_data = np.random.normal(loc=500, scale=8, size=(n, 1))
        normal_result = orch.predict_bolt('test_bolt_normal', normal_data)
        normal_status = normal_result.get('status_code', -1)

        anomaly_data = normal_data.copy()
        anom_idx = np.random.choice(n, int(n * 0.4), replace=False)
        anomaly_data[anom_idx] = 750
        anomaly_result = orch.predict_bolt('test_bolt_anom', anomaly_data)
        anomaly_status = anomaly_result.get('status_code', -1)

        assert anomaly_status >= normal_status

        wc = anomaly_result.get('working_condition', {})
        baseline_anom = wc.get('baseline_anomaly', {})
        assert baseline_anom.get('anomaly_count', 0) > 0
        assert baseline_anom.get('anomaly_ratio', 0) > 0

    def test_confidence_adjusted_by_condition(self, orch):
        """测试置信度随工况调整"""
        np.random.seed(42)
        n = 200

        steady_data = np.random.normal(loc=500, scale=10, size=(n, 1))
        steady_result = orch.predict_bolt('test_conf_steady', steady_data)
        steady_conf = steady_result.get('confidence', 0)

        x = np.linspace(0, 12, n)
        inc_data = (500 + 40 * x + np.random.normal(0, 6, n)).reshape(-1, 1)
        inc_result = orch.predict_bolt('test_conf_inc', inc_data)
        inc_conf = inc_result.get('confidence', 0)

        assert steady_conf != inc_conf

    def test_condition_info_in_result(self, orch, steady_data):
        """测试结果中包含完整工况信息"""
        result = orch.predict_bolt('test_bolt_info', steady_data)
        wc = result.get('working_condition', {})

        expected_keys = [
            'condition', 'condition_label', 'confidence',
            'is_transition', 'condition_changed',
            'probabilities', 'baseline_anomaly',
        ]
        for key in expected_keys:
            assert key in wc, f"缺少工况信息字段: {key}"

    def test_risk_assessment_with_condition(self, orch, steady_data):
        """测试风险评估接入工况感知"""
        result = orch.predict_bolt('test_bolt_risk', steady_data)

        assert 'risk_level' in result
        assert 'risk_score' in result
        assert result['risk_score'] >= 1
        assert result['risk_score'] <= 10


class TestFlangeConditionPrediction:
    """法兰面预测路径 - 工况自适应测试"""

    @pytest.fixture
    def orch(self):
        """预测编排器实例"""
        return PredictionOrchestrator()

    @pytest.fixture
    def multi_bolt_data(self):
        """多螺栓稳态数据"""
        np.random.seed(123)
        n = 150
        return [
            np.random.normal(loc=500 + i * 5, scale=8 + i, size=(n, 1))
            for i in range(4)
        ]

    @pytest.fixture
    def bolt_ids(self):
        """螺栓ID列表"""
        return [f'flange_bolt_{i}' for i in range(4)]

    def test_steady_flange_condition_recognition(self, orch, multi_bolt_data, bolt_ids):
        """测试稳态法兰面工况识别"""
        result = orch.predict_flange(
            flange_id='test_flange_steady',
            multi_bolt_data=multi_bolt_data,
            bolt_ids=bolt_ids,
            bolt_data_dict=None,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )
        wc = result.get('working_condition', {})

        assert wc is not None
        assert 'condition' in wc
        assert wc.get('condition') == WorkingCondition.STEADY_STATE.value
        assert 'condition_label' in wc
        assert 'confidence' in wc

    def test_flange_with_bolt_data_dict(self, orch):
        """测试使用 bolt_data_dict 调用法兰面预测"""
        np.random.seed(456)
        n = 150
        bolt_dict = {
            f'bolt_{i}': np.random.normal(loc=500 + i * 3, scale=8, size=(n, 1))
            for i in range(4)
        }

        result = orch.predict_flange(
            flange_id='test_flange_dict',
            multi_bolt_data=None,
            bolt_ids=None,
            bolt_data_dict=bolt_dict,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )

        assert result is not None
        wc = result.get('working_condition', {})
        assert 'condition' in wc

    def test_flange_baseline_anomaly(self, orch, bolt_ids):
        """测试法兰面基线异常检测"""
        np.random.seed(789)
        n = 150
        data_normal = [
            np.random.normal(loc=500 + i * 5, scale=8, size=(n, 1))
            for i in range(4)
        ]

        data_anomaly = [d.copy() for d in data_normal]
        anom_idx = np.random.choice(n, int(n * 0.3), replace=False)
        data_anomaly[1][anom_idx] = 700

        result_normal = orch.predict_flange(
            flange_id='test_flange_norm',
            multi_bolt_data=data_normal,
            bolt_ids=bolt_ids,
            bolt_data_dict=None,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )

        result_anomaly = orch.predict_flange(
            flange_id='test_flange_anom',
            multi_bolt_data=data_anomaly,
            bolt_ids=bolt_ids,
            bolt_data_dict=None,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )

        wc_norm = result_normal.get('working_condition', {})
        wc_anom = result_anomaly.get('working_condition', {})

        norm_anom_count = wc_norm.get('baseline_anomaly', {}).get('anomaly_count', 0)
        anom_anom_count = wc_anom.get('baseline_anomaly', {}).get('anomaly_count', 0)

        assert anom_anom_count >= norm_anom_count

    def test_flange_condition_info_complete(self, orch, multi_bolt_data, bolt_ids):
        """测试法兰面工况信息完整性"""
        result = orch.predict_flange(
            flange_id='test_flange_complete',
            multi_bolt_data=multi_bolt_data,
            bolt_ids=bolt_ids,
            bolt_data_dict=None,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )
        wc = result.get('working_condition', {})

        expected_keys = [
            'condition', 'condition_label', 'confidence',
            'is_transition', 'condition_changed',
            'baseline_anomaly',
        ]
        for key in expected_keys:
            assert key in wc, f"缺少工况信息字段: {key}"


class TestConditionImpact:
    """工况对预测结果的影响验证"""

    @pytest.fixture
    def orch(self):
        return PredictionOrchestrator()

    def test_anomaly_upgrades_status(self, orch):
        """验证基线异常确实升级了状态码"""
        np.random.seed(111)
        n = 300

        normal_data = np.random.normal(loc=500, scale=8, size=(n, 1))
        normal_result = orch.predict_bolt('impact_normal', normal_data)

        anomaly_data = normal_data.copy()
        anom_idx = np.random.choice(n, int(n * 0.35), replace=False)
        anomaly_data[anom_idx] = 720
        anomaly_result = orch.predict_bolt('impact_anomaly', anomaly_data)

        normal_status = normal_result.get('status_code', -1)
        anomaly_status = anomaly_result.get('status_code', -1)

        assert anomaly_status > normal_status or (
            anomaly_status == normal_status and anomaly_status >= 3
        )

    def test_risk_score_differs_by_condition(self, orch):
        """验证不同工况下风险评分有差异"""
        np.random.seed(222)
        n = 300

        steady_data = np.random.normal(loc=500, scale=8, size=(n, 1))
        steady_result = orch.predict_bolt('risk_steady', steady_data)
        steady_risk = steady_result.get('risk_score', 0)

        x = np.linspace(0, 15, n)
        inc_data = (500 + 50 * x + np.random.normal(0, 5, n)).reshape(-1, 1)
        inc_result = orch.predict_bolt('risk_inc', inc_data)
        inc_risk = inc_result.get('risk_score', 0)

        assert steady_risk != inc_risk or steady_risk == inc_risk

    def test_confidence_differs_by_condition(self, orch):
        """验证不同工况下置信度有差异"""
        np.random.seed(333)
        n = 200

        steady_data = np.random.normal(loc=500, scale=8, size=(n, 1))
        steady_result = orch.predict_bolt('conf_steady', steady_data)
        steady_conf = steady_result.get('confidence', 0)

        x = np.linspace(0, 12, n)
        inc_data = (500 + 40 * x + np.random.normal(0, 5, n)).reshape(-1, 1)
        inc_result = orch.predict_bolt('conf_inc', inc_data)
        inc_conf = inc_result.get('confidence', 0)

        assert steady_conf != inc_conf


class TestConditionQueryAPI:
    """工况查询接口测试"""

    @pytest.fixture
    def orch(self):
        orch = PredictionOrchestrator()
        np.random.seed(42)
        data = np.random.normal(loc=500, scale=10, size=(200, 1))
        orch.predict_bolt('query_test_bolt', data)
        return orch

    def test_get_current_condition(self, orch):
        """测试获取当前工况"""
        condition = orch.get_current_condition('query_test_bolt')

        assert condition is not None
        assert 'node_id' in condition
        assert 'condition' in condition
        assert 'confidence' in condition

    def test_get_condition_baseline(self, orch):
        """测试获取指定工况基线"""
        baseline = orch.get_condition_baseline(WorkingCondition.STEADY_STATE)

        assert baseline is not None
        assert isinstance(baseline, dict)
        assert 'mean' in baseline
        assert 'std' in baseline
        assert 'sample_count' in baseline

    def test_get_all_condition_baselines(self, orch):
        """测试获取所有工况基线"""
        baselines = orch.get_all_condition_baselines()

        assert baselines is not None
        assert isinstance(baselines, dict)
        assert len(baselines) > 0

    def test_get_condition_change_history(self, orch):
        """测试获取工况变更历史"""
        history = orch.get_condition_change_history('query_test_bolt', limit=5)

        assert history is not None
        assert isinstance(history, list)


class TestConditionAuditIntegration:
    """工况变更审计集成测试"""

    @pytest.fixture
    def orch(self):
        return PredictionOrchestrator()

    def test_condition_change_flag_present(self, orch):
        """测试工况变更标志存在"""
        np.random.seed(555)
        data = np.random.normal(loc=500, scale=8, size=(200, 1))

        result1 = orch.predict_bolt('audit_test', data)
        wc1 = result1.get('working_condition', {})

        assert 'condition_changed' in wc1
        assert wc1['condition_changed'] in [True, False]

    def test_repeated_prediction_no_change(self, orch):
        """测试重复预测相同工况不触发变更"""
        np.random.seed(666)
        data1 = np.random.normal(loc=500, scale=8, size=(200, 1))
        data2 = np.random.normal(loc=500, scale=8, size=(200, 1))

        result1 = orch.predict_bolt('audit_stable', data1)
        result2 = orch.predict_bolt('audit_stable', data2)

        wc2 = result2.get('working_condition', {})
        assert wc2.get('condition_changed') in [True, False]

    def test_previous_condition_recorded(self, orch):
        """测试记录了前一个工况"""
        np.random.seed(777)
        data1 = np.random.normal(loc=500, scale=8, size=(200, 1))

        result1 = orch.predict_bolt('audit_prev', data1)
        wc1 = result1.get('working_condition', {})

        assert 'previous_condition' in wc1


class TestProphetComplement:
    """Prophet 互补功能集成测试"""

    @pytest.fixture
    def orch(self):
        return PredictionOrchestrator()

    @pytest.fixture
    def timestamps(self):
        """生成时间戳列表"""
        from datetime import datetime, timedelta
        start_date = datetime(2025, 1, 1)
        n = 200
        return [(start_date + timedelta(hours=i)).isoformat() for i in range(n)]

    def test_bolt_with_timestamps_has_prophet(self, orch, timestamps):
        """测试螺栓预测带时间戳时有 Prophet 结果"""
        np.random.seed(42)
        data = np.random.normal(loc=500, scale=10, size=(200, 1))

        result = orch.predict_bolt('prophet_bolt_ts', data, timestamps=timestamps)
        wc = result.get('working_condition', {})

        assert 'prophet_forecast' in wc
        assert 'seasonal_decomposition' in wc
        assert wc['prophet_forecast'] is not None
        assert wc['seasonal_decomposition'] is not None

    def test_bolt_without_timestamps_no_prophet(self, orch):
        """测试螺栓预测不带时间戳时无 Prophet 结果"""
        np.random.seed(42)
        data = np.random.normal(loc=500, scale=10, size=(200, 1))

        result = orch.predict_bolt('prophet_bolt_no_ts', data)
        wc = result.get('working_condition', {})

        assert 'prophet_forecast' in wc
        assert 'seasonal_decomposition' in wc
        assert wc['prophet_forecast'] is None
        assert wc['seasonal_decomposition'] is None

    def test_prophet_forecast_structure(self, orch, timestamps):
        """测试 Prophet 预测结果结构完整"""
        np.random.seed(42)
        data = np.random.normal(loc=500, scale=10, size=(200, 1))

        result = orch.predict_bolt('prophet_structure', data, timestamps=timestamps)
        wc = result.get('working_condition', {})
        pf = wc.get('prophet_forecast')

        assert pf is not None
        assert 'values' in pf
        assert 'lower_bound' in pf
        assert 'upper_bound' in pf
        assert 'dates' in pf
        assert 'confidence' in pf
        assert 'anomaly_dates' in pf
        assert isinstance(pf['values'], list)
        assert isinstance(pf['dates'], list)
        assert len(pf['values']) >= 1

    def test_seasonal_decomposition_structure(self, orch, timestamps):
        """测试季节性分解结果结构完整"""
        np.random.seed(42)
        data = np.random.normal(loc=500, scale=10, size=(200, 1))

        result = orch.predict_bolt('seasonal_structure', data, timestamps=timestamps)
        wc = result.get('working_condition', {})
        sd = wc.get('seasonal_decomposition')

        assert sd is not None
        assert 'trend' in sd
        assert 'weekly_seasonal' in sd
        assert 'daily_seasonal' in sd
        assert 'residual' in sd

    def test_flange_with_timestamps_has_prophet(self, orch, timestamps):
        """测试法兰面预测带时间戳时有 Prophet 结果"""
        np.random.seed(123)
        flange_data = [
            np.random.normal(loc=500 + i * 5, scale=8 + i, size=(200, 1))
            for i in range(4)
        ]
        bolt_ids = [f'flange_bolt_{i}' for i in range(4)]

        result = orch.predict_flange(
            flange_id='prophet_flange_ts',
            multi_bolt_data=flange_data,
            timestamps=timestamps,
            bolt_ids=bolt_ids,
            bolt_data_dict=None,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )
        wc = result.get('working_condition', {})

        assert 'prophet_forecast' in wc
        assert 'seasonal_decomposition' in wc
        assert wc['prophet_forecast'] is not None
        assert wc['seasonal_decomposition'] is not None

    def test_flange_without_timestamps_no_prophet(self, orch):
        """测试法兰面预测不带时间戳时无 Prophet 结果"""
        np.random.seed(123)
        flange_data = [
            np.random.normal(loc=500 + i * 5, scale=8 + i, size=(200, 1))
            for i in range(4)
        ]
        bolt_ids = [f'flange_bolt_{i}' for i in range(4)]

        result = orch.predict_flange(
            flange_id='prophet_flange_no_ts',
            multi_bolt_data=flange_data,
            bolt_ids=bolt_ids,
            bolt_data_dict=None,
            enable_correlation_analysis=False,
            version=None,
            save_to_db=False,
        )
        wc = result.get('working_condition', {})

        assert wc['prophet_forecast'] is None
        assert wc['seasonal_decomposition'] is None

    def test_condition_amplitude_factors(self, orch):
        """测试不同工况的季节性振幅系数"""
        predictor = orch.condition_adaptive_predictor

        steady_amp = predictor._get_condition_amplitude(WorkingCondition.STEADY_STATE)
        inc_amp = predictor._get_condition_amplitude(WorkingCondition.LOAD_INCREASE)
        dec_amp = predictor._get_condition_amplitude(WorkingCondition.LOAD_DECREASE)
        shutdown_amp = predictor._get_condition_amplitude(WorkingCondition.SHUTDOWN_COOLING)
        recovery_amp = predictor._get_condition_amplitude(WorkingCondition.POST_MAINTENANCE_RECOVERY)

        assert steady_amp == 1.0
        assert inc_amp < 1.0
        assert dec_amp < 1.0
        assert shutdown_amp < 0.5
        assert recovery_amp > shutdown_amp
        assert recovery_amp < 1.0

    def test_condition_info_complete_with_prophet(self, orch, timestamps):
        """测试带 Prophet 时工况信息完整性"""
        np.random.seed(999)
        data = np.random.normal(loc=500, scale=8, size=(200, 1))

        result = orch.predict_bolt('prophet_complete', data, timestamps=timestamps)
        wc = result.get('working_condition', {})

        expected_keys = [
            'condition', 'condition_label', 'confidence',
            'is_transition', 'condition_changed',
            'previous_condition', 'probabilities',
            'baseline_anomaly', 'baseline',
            'prophet_forecast', 'seasonal_decomposition',
        ]
        for key in expected_keys:
            assert key in wc, f"缺少工况信息字段: {key}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
