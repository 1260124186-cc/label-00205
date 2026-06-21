"""
Prophet 多周期预测与季节性分解 测试
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

import pytest


class TestProphetForecaster:
    """ProphetForecaster 单元测试"""

    @pytest.fixture
    def synthetic_data(self):
        """生成合成测试数据：趋势 + 周周期 + 日周期 + 噪声"""
        np.random.seed(42)
        n_days = 180
        start_date = datetime(2024, 1, 1)

        dates = [start_date + timedelta(days=i) for i in range(n_days)]
        t = np.arange(n_days)

        base_value = 600.0
        trend_slope = -0.15
        trend = base_value + trend_slope * t

        weekly_amplitude = 15.0
        weekly = weekly_amplitude * np.sin(2 * np.pi * t / 7)

        daily_amplitude = 8.0
        daily = daily_amplitude * np.sin(2 * np.pi * t / 1)

        noise = np.random.normal(0, 5.0, n_days)

        values = trend + weekly + daily + noise

        return dates, values

    @pytest.fixture
    def holidays(self):
        """测试用节假日数据"""
        return [
            {'ds': '2024-02-10', 'holiday': '春节', 'lower_window': 3, 'upper_window': 7},
            {'ds': '2024-04-04', 'holiday': '清明节', 'lower_window': 0, 'upper_window': 1},
            {'ds': '2024-05-01', 'holiday': '劳动节', 'lower_window': 0, 'upper_window': 3},
        ]

    @pytest.fixture
    def shutdown_dates(self):
        """测试用停产日"""
        return ['2024-02-15', '2024-02-16', '2024-02-17']

    def test_imports(self):
        """测试核心模块导入"""
        from app.models.prophet_forecaster import (
            ProphetForecaster,
            ForecastResult,
            SeasonalDecomposition,
            MultiHorizonForecast,
            PROPHET_AVAILABLE,
        )
        logger.info(f"Prophet可用: {PROPHET_AVAILABLE}")
        assert ProphetForecaster is not None
        assert ForecastResult is not None
        assert SeasonalDecomposition is not None
        assert MultiHorizonForecast is not None

    def test_init(self):
        """测试初始化"""
        from app.models.prophet_forecaster import ProphetForecaster

        forecaster = ProphetForecaster(uncertainty_samples=500)
        assert forecaster is not None
        assert forecaster.uncertainty_samples == 500
        assert forecaster.is_fitted is False
        assert len(forecaster.models) == 0

    def test_fit_and_forecast_single(self, synthetic_data):
        """测试单 horizon 拟合与预测"""
        from app.models.prophet_forecaster import ProphetForecaster

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        horizons_to_test = [7, 30]
        forecaster.fit(
            data=values,
            timestamps=np.array(dates),
            horizons=horizons_to_test,
        )

        assert forecaster.is_fitted is True
        assert len(forecaster.models) == len(horizons_to_test)

        result = forecaster.forecast_single(horizon_days=30)
        assert result is not None
        assert result.horizon_days == 30
        assert len(result.dates) == 30
        assert len(result.values) == 30
        assert len(result.lower_bound) == 30
        assert len(result.upper_bound) == 30
        assert 0.0 <= result.confidence <= 1.0
        assert np.all(result.lower_bound <= result.values)
        assert np.all(result.values <= result.upper_bound)
        logger.info(
            f"单horizon预测OK: horizon={result.horizon_days}天, "
            f"置信度={result.confidence:.3f}, 异常类型={result.anomaly_type}"
        )

    def test_multi_horizon_forecast(self, synthetic_data):
        """测试多 horizon 预测主接口"""
        from app.models.prophet_forecaster import ProphetForecaster, MultiHorizonForecast

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        result = forecaster.forecast_multi_horizon(
            historical_data=values,
            historical_timestamps=np.array(dates),
            horizons=[7, 30, 90],
            include_decomposition=True,
        )

        assert isinstance(result, MultiHorizonForecast)
        assert len(result.historical_dates) == len(dates)
        assert len(result.historical_values) == len(values)

        for horizon in [7, 30, 90]:
            fr = result.get_forecast(horizon)
            assert fr is not None, f"Horizon {horizon}天的预测结果为空"
            assert fr.horizon_days == horizon
            assert len(fr.dates) == horizon
            assert len(fr.values) == horizon
            assert len(fr.lower_bound) == horizon
            assert len(fr.upper_bound) == horizon
            assert 0.0 <= fr.confidence <= 1.0

            ci_widths = fr.upper_bound - fr.lower_bound
            assert np.all(ci_widths > 0), f"Horizon {horizon}天置信区间宽度应为正"

            logger.info(
                f"  Horizon {horizon:3d}天: 置信度={fr.confidence:.3f}, "
                f"均值CI宽度={np.mean(ci_widths):.2f}, 异常={fr.anomaly_type}"
            )

        if 7 in result.forecasts and 90 in result.forecasts:
            ci_7 = np.mean(result.forecasts[7].upper_bound - result.forecasts[7].lower_bound)
            ci_90 = np.mean(result.forecasts[90].upper_bound - result.forecasts[90].lower_bound)
            logger.info(f"  CI宽度比较: 7天={ci_7:.2f}, 90天={ci_90:.2f}")

        logger.info(f"  拟合horizons: {result.model_parameters.get('fitted_horizons', [])}")

    def test_seasonal_decomposition(self, synthetic_data):
        """测试季节性分解"""
        from app.models.prophet_forecaster import ProphetForecaster

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        result = forecaster.forecast_multi_horizon(
            historical_data=values,
            historical_timestamps=np.array(dates),
            horizons=[30],
            include_decomposition=True,
        )

        dec = result.decomposition
        assert dec is not None, "季节性分解结果为空"
        assert len(dec.dates) > 0
        assert len(dec.trend) == len(dec.dates)
        logger.info(
            f"季节性分解OK: {len(dec.dates)}个点, "
            f"趋势=[{np.min(dec.trend):.2f}~{np.max(dec.trend):.2f}]"
        )

        if dec.weekly is not None:
            assert len(dec.weekly) == len(dec.dates)
            logger.info(f"  周周期: 振幅≈{np.max(dec.weekly) - np.min(dec.weekly):.2f}")

        if dec.daily is not None:
            assert len(dec.daily) == len(dec.dates)
            logger.info(f"  日周期: 振幅≈{np.max(dec.daily) - np.min(dec.daily):.2f}")

        if dec.residuals is not None:
            hist_residuals = dec.residuals[:len(values)]
            valid_residuals = hist_residuals[~np.isnan(hist_residuals)]
            if len(valid_residuals) > 0:
                logger.info(f"  历史残差: std={np.std(valid_residuals):.2f}")

        dec_dict = dec.to_dict()
        assert 'dates' in dec_dict
        assert 'trend' in dec_dict
        assert isinstance(dec_dict['dates'], list)
        assert isinstance(dec_dict['trend'], list)

    def test_holidays_and_shutdown(self, synthetic_data, holidays, shutdown_dates):
        """测试节假日/停产日作为 regressor"""
        from app.models.prophet_forecaster import ProphetForecaster

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        result = forecaster.forecast_multi_horizon(
            historical_data=values,
            historical_timestamps=np.array(dates),
            horizons=[30],
            holidays=holidays,
            shutdown_dates=shutdown_dates,
            include_decomposition=True,
        )

        assert result.holidays_used is not None
        assert len(result.holidays_used) == len(holidays)
        logger.info(f"节假日使用: {len(result.holidays_used)}个")

        assert result.shutdown_dates_used is not None
        assert len(result.shutdown_dates_used) == len(shutdown_dates)
        logger.info(f"停产日使用: {len(result.shutdown_dates_used)}个")

        fr = result.get_forecast(30)
        assert fr is not None
        logger.info(f"带节假日预测: 置信度={fr.confidence:.3f}, 异常类型={fr.anomaly_type}")

    def test_to_dict_serialization(self, synthetic_data):
        """测试序列化到字典"""
        from app.models.prophet_forecaster import ProphetForecaster

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        result = forecaster.forecast_multi_horizon(
            historical_data=values,
            historical_timestamps=np.array(dates),
            horizons=[7, 30],
            include_decomposition=True,
        )

        result_dict = result.to_dict()

        assert 'historical' in result_dict
        assert 'forecasts' in result_dict
        assert 'decomposition' in result_dict
        assert 'model_parameters' in result_dict

        assert len(result_dict['historical']['dates']) == len(dates)
        assert len(result_dict['historical']['values']) == len(values)

        for horizon in ['7', '30']:
            assert horizon in result_dict['forecasts']
            fr = result_dict['forecasts'][horizon]
            assert fr['horizon_days'] == int(horizon)
            assert len(fr['dates']) == int(horizon)
            assert len(fr['values']) == int(horizon)
            assert len(fr['lower_bound']) == int(horizon)
            assert len(fr['upper_bound']) == int(horizon)

        if result_dict['decomposition'] is not None:
            dec = result_dict['decomposition']
            assert 'trend' in dec
            assert isinstance(dec['trend'], list)
            assert len(dec['trend']) == len(dec['dates'])

        import json
        json_str = json.dumps(result_dict, default=str)
        assert len(json_str) > 0
        logger.info(f"序列化JSON OK: {len(json_str)} chars")

    def test_backward_compatible_forecast(self, synthetic_data):
        """测试向后兼容的 forecast() 和 predict_status() 方法"""
        from app.models.prophet_forecaster import ProphetForecaster

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        old_result = forecaster.forecast(
            days=30,
            historical_data=values,
            historical_timestamps=np.array(dates),
        )

        assert old_result is not None
        assert len(old_result.dates) == 30
        assert len(old_result.values) == 30
        assert 0.0 <= old_result.confidence <= 1.0
        logger.info(
            f"旧接口forecast() OK: 置信度={old_result.confidence:.3f}, "
            f"异常类型={old_result.anomaly_type}"
        )

        status_result = forecaster.predict_status(
            historical_data=values,
            historical_timestamps=np.array(dates),
            days=30,
        )

        assert 'pw_type' in status_result
        assert 'confidence' in status_result
        assert 'rec_measures' in status_result
        assert 'forecast_dates' in status_result
        assert 'forecast_values' in status_result
        logger.info(
            f"旧接口predict_status() OK: pw_type={status_result['pw_type']}, "
            f"confidence={status_result['confidence']:.3f}"
        )

    def test_simple_forecast_fallback(self, monkeypatch, synthetic_data):
        """测试 Prophet 不可用时的备选方案"""
        import app.models.prophet_forecaster as pf_module
        monkeypatch.setattr(pf_module, 'PROPHET_AVAILABLE', False)

        from app.models.prophet_forecaster import ProphetForecaster

        dates, values = synthetic_data
        forecaster = ProphetForecaster(uncertainty_samples=100)

        result = forecaster.forecast_multi_horizon(
            historical_data=values,
            historical_timestamps=np.array(dates),
            horizons=[7, 30, 90],
            include_decomposition=True,
        )

        assert result.model_parameters['prophet_available'] is False
        assert result.model_parameters['model_info']['method'] == 'simple_polynomial'

        for horizon in [7, 30, 90]:
            fr = result.get_forecast(horizon)
            assert fr is not None
            assert len(fr.dates) == horizon
            assert np.all(fr.lower_bound <= fr.values)
            assert np.all(fr.values <= fr.upper_bound)

        assert result.decomposition is not None
        logger.info(
            f"备选方案OK: 方法={result.model_parameters['model_info']['method']}, "
            f"horizons={list(result.forecasts.keys())}"
        )


class TestTimeSeriesService:
    """时序服务层 Prophet 集成测试"""

    @pytest.fixture
    def sample_data_points(self):
        """生成服务层测试数据点"""
        np.random.seed(123)
        n_days = 120
        start_date = datetime(2024, 3, 1)

        points = []
        t = np.arange(n_days)
        values = 580.0 - 0.1 * t + 12.0 * np.sin(2 * np.pi * t / 7) + np.random.normal(0, 4.0, n_days)

        for i in range(n_days):
            points.append({
                'timestamp': start_date + timedelta(days=i),
                'value': float(values[i]),
            })

        return points

    def test_service_method_exists(self):
        """测试服务层方法存在"""
        from app.services.timeseries_service import TimeSeriesAnalysisService

        assert hasattr(TimeSeriesAnalysisService, 'prophet_multi_horizon_forecast')
        logger.info("服务层prophet_multi_horizon_forecast方法存在 OK")

    def test_service_propagates_errors(self):
        """测试服务层参数错误传播"""
        from app.services.timeseries_service import TimeSeriesAnalysisService

        service = TimeSeriesAnalysisService(repository=None)

        with pytest.raises(ValueError, match="数据点不足"):
            service.prophet_multi_horizon_forecast(
                sensor_id="TEST_001",
                data_points=[],
            )

        with pytest.raises(ValueError, match="数据点不足"):
            service.prophet_multi_horizon_forecast(
                sensor_id="TEST_001",
                data_points=[{'timestamp': datetime.now(), 'value': 1.0}],
            )

        logger.info("服务层错误传播 OK")

    def test_service_full_workflow(self, sample_data_points):
        """测试服务层完整工作流"""
        from app.services.timeseries_service import TimeSeriesAnalysisService

        service = TimeSeriesAnalysisService(repository=None)

        holidays = [
            {'ds': datetime(2024, 5, 1), 'holiday': '劳动节', 'lower_window': 0, 'upper_window': 1},
        ]
        shutdown = [datetime(2024, 5, 2)]

        result = service.prophet_multi_horizon_forecast(
            sensor_id="BOLT_TEST_001",
            data_points=sample_data_points,
            horizons=[7, 30],
            holidays=holidays,
            shutdown_dates=shutdown,
            include_decomposition=True,
            uncertainty_samples=100,
        )

        assert isinstance(result, dict)
        assert 'historical' in result
        assert 'forecasts' in result
        assert 'decomposition' in result
        assert 'model_parameters' in result
        assert 'holidays_used' in result
        assert 'shutdown_dates_used' in result

        assert len(result['historical']['dates']) == len(sample_data_points)

        for h in ['7', '30']:
            assert h in result['forecasts']
            fr = result['forecasts'][h]
            assert len(fr['dates']) == int(h)
            assert len(fr['values']) == int(h)
            assert 0 <= fr['confidence'] <= 1

        if result['decomposition'] is not None:
            dec = result['decomposition']
            assert len(dec['trend']) == len(dec['dates'])

        import json
        json_str = json.dumps(result, default=str, ensure_ascii=False)
        assert len(json_str) > 0
        logger.info(f"服务层完整工作流 OK: JSON长度={len(json_str)}chars")


class TestAPIIntegration:
    """API 路由集成测试（使用 TestClient）"""

    def test_schemas_import(self):
        """测试 API schemas 导入"""
        from app.api.timeseries_schemas import (
            ProphetMultiHorizonRequest,
            ProphetMultiHorizonResponse,
            SingleHorizonForecastSchema,
            SeasonalDecompositionSchema,
            HolidayItemSchema,
            ProphetDataPointSchema,
        )
        logger.info("API Schemas 导入 OK")

    def test_schemas_validation(self):
        """测试 schema 验证逻辑"""
        from pydantic import ValidationError
        from app.api.timeseries_schemas import (
            ProphetMultiHorizonRequest,
            ProphetDataPointSchema,
            HolidayItemSchema,
        )

        points = [
            ProphetDataPointSchema(timestamp=datetime(2024, 1, 1), value=500.0),
            ProphetDataPointSchema(timestamp=datetime(2024, 1, 2), value=501.0),
        ]
        if len(points) < 30:
            for i in range(3, 35):
                points.append(ProphetDataPointSchema(
                    timestamp=datetime(2024, 1, 1) + timedelta(days=i - 1),
                    value=500.0 + i * 0.5,
                ))

        req = ProphetMultiHorizonRequest(
            sensor_id="TEST",
            data_points=points,
            horizons=[7, 30, 90],
            include_decomposition=True,
        )
        assert req.sensor_id == "TEST"
        assert len(req.data_points) >= 30
        assert req.horizons == [7, 30, 90]

        holiday = HolidayItemSchema(
            ds=datetime(2024, 10, 1),
            holiday="国庆",
            lower_window=1,
            upper_window=3,
        )
        assert holiday.holiday == "国庆"

        with pytest.raises(ValidationError):
            ProphetMultiHorizonRequest(
                sensor_id="SHORT",
                data_points=[
                    ProphetDataPointSchema(timestamp=datetime(2024, 1, 1), value=500.0),
                ],
            )

        logger.info("API Schemas 验证 OK")


def run_all_tests():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("开始 Prophet 多周期预测与季节性分解 测试")
    logger.info("=" * 60)

    pytest.main([
        __file__,
        '-v',
        '-s',
        '--tb=short',
    ])


if __name__ == '__main__':
    run_all_tests()
