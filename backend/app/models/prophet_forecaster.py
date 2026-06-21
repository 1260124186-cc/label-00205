"""
Prophet时间序列预测模型 - 多周期预测与季节性分解

基于Facebook Prophet的时间序列预测，支持多horizon预测与季节性分解。

功能:
1. 多horizon预测 (7天/30天/90天)，各horizon独立置信区间
2. 季节性分解：趋势项、周周期、日周期分量
3. 节假日/停产日作为 Prophet regressor 输入
4. 异常时间点预测与不确定性量化

使用示例:
    from app.models.prophet_forecaster import ProphetForecaster, MultiHorizonForecast

    forecaster = ProphetForecaster()
    result: MultiHorizonForecast = forecaster.forecast_multi_horizon(
        historical_data=data,
        timestamps=timestamps,
        horizons=[7, 30, 90],
        holidays=holiday_df,
        shutdown_dates=shutdown_list
    )
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from loguru import logger

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet未安装，时间序列预测功能将使用备选方案")

from app.utils.config import config


@dataclass
class ForecastResult:
    """
    单 horizon 预测结果数据类

    Attributes:
        horizon_days: 预测horizon天数
        dates: 预测日期列表
        values: 预测值列表 (yhat)
        lower_bound: 下界列表 (yhat_lower)
        upper_bound: 上界列表 (yhat_upper)
        anomaly_dates: 预测的异常日期
        anomaly_type: 异常类型
        confidence: 预测置信度
        confidence_level: 置信区间水平 (如 0.95 表示 95% CI)
    """
    horizon_days: int
    dates: List[datetime]
    values: np.ndarray
    lower_bound: np.ndarray
    upper_bound: np.ndarray
    anomaly_dates: List[Tuple[datetime, datetime]]
    anomaly_type: str
    confidence: float
    confidence_level: float = 0.95


@dataclass
class SeasonalDecomposition:
    """
    季节性分解结果数据类

    Attributes:
        dates: 日期列表 (历史 + 预测)
        trend: 趋势项 (trend)
        weekly: 周周期分量 (weekly)
        daily: 日周期分量 (daily)
        yearly: 年周期分量 (yearly，如启用)
        holidays: 节假日效应分量 (holidays，如提供)
        regressors: 额外regressor效应分量
        residuals: 残差项 (y - yhat_without_noise)
    """
    dates: List[datetime]
    trend: np.ndarray
    weekly: Optional[np.ndarray] = None
    daily: Optional[np.ndarray] = None
    yearly: Optional[np.ndarray] = None
    holidays: Optional[np.ndarray] = None
    regressors: Optional[Dict[str, np.ndarray]] = None
    residuals: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        result = {
            'dates': [d.isoformat() for d in self.dates],
            'trend': self.trend.tolist(),
        }
        if self.weekly is not None:
            result['weekly'] = self.weekly.tolist()
        if self.daily is not None:
            result['daily'] = self.daily.tolist()
        if self.yearly is not None:
            result['yearly'] = self.yearly.tolist()
        if self.holidays is not None:
            result['holidays'] = self.holidays.tolist()
        if self.regressors is not None:
            result['regressors'] = {
                k: v.tolist() for k, v in self.regressors.items()
            }
        if self.residuals is not None:
            result['residuals'] = self.residuals.tolist()
        return result


@dataclass
class MultiHorizonForecast:
    """
    多 horizon 预测综合结果

    Attributes:
        forecasts: 各 horizon 的预测结果字典 {horizon_days: ForecastResult}
        decomposition: 季节性分解结果
        historical_dates: 历史数据日期
        historical_values: 历史数据值
        model_parameters: 模型参数摘要
        holidays_used: 使用的节假日信息
        shutdown_dates_used: 使用的停产日信息
    """
    forecasts: Dict[int, ForecastResult] = field(default_factory=dict)
    decomposition: Optional[SeasonalDecomposition] = None
    historical_dates: List[datetime] = field(default_factory=list)
    historical_values: np.ndarray = field(default_factory=lambda: np.array([]))
    model_parameters: Dict[str, Any] = field(default_factory=dict)
    holidays_used: Optional[List[Dict[str, Any]]] = None
    shutdown_dates_used: Optional[List[str]] = None

    def get_forecast(self, horizon_days: int) -> Optional[ForecastResult]:
        """获取指定 horizon 的预测结果"""
        return self.forecasts.get(horizon_days)

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            'historical': {
                'dates': [d.isoformat() for d in self.historical_dates],
                'values': self.historical_values.tolist(),
            },
            'forecasts': {
                str(h): {
                    'horizon_days': fr.horizon_days,
                    'dates': [d.isoformat() for d in fr.dates],
                    'values': fr.values.tolist(),
                    'lower_bound': fr.lower_bound.tolist(),
                    'upper_bound': fr.upper_bound.tolist(),
                    'anomaly_dates': [
                        (s.isoformat(), e.isoformat())
                        for s, e in fr.anomaly_dates
                    ],
                    'anomaly_type': fr.anomaly_type,
                    'confidence': fr.confidence,
                    'confidence_level': fr.confidence_level,
                }
                for h, fr in self.forecasts.items()
            },
            'decomposition': (
                self.decomposition.to_dict()
                if self.decomposition is not None
                else None
            ),
            'model_parameters': self.model_parameters,
            'holidays_used': self.holidays_used,
            'shutdown_dates_used': self.shutdown_dates_used,
        }


class ProphetForecaster:
    """
    Prophet时间序列预测器 - 多周期预测与季节性分解

    支持多horizon预测 (7/30/90天)，各horizon独立置信区间，
    输出季节性分解（趋势项、周周期、日周期），支持节假日/停产日作为regressor。

    Attributes:
        models: 各 horizon 的 Prophet 模型实例
        thresholds: 预紧力阈值配置
        is_fitted: 是否已拟合
        training_data: 训练数据
    """

    SUPPORTED_HORIZONS = [7, 30, 90]

    def __init__(self, uncertainty_samples: int = 1000):
        """
        初始化预测器

        Args:
            uncertainty_samples: 不确定性采样数，影响置信区间质量
        """
        self.models: Dict[int, Any] = {}
        self.uncertainty_samples = uncertainty_samples
        self.thresholds = config.get('risk_assessment.preload_thresholds', {
            'min_normal': 400,
            'max_normal': 800,
            'warning_deviation': 0.1,
            'critical_deviation': 0.2
        })
        self.is_fitted = False
        self.training_data: Optional[pd.DataFrame] = None
        self.last_holidays_df: Optional[pd.DataFrame] = None
        self.last_regressors: Dict[str, Any] = {}

        logger.info("Prophet多周期预测器初始化完成")

    def _prepare_holidays_dataframe(
        self,
        holidays: Optional[List[Dict[str, Any]]] = None,
        shutdown_dates: Optional[List[Union[str, datetime]]] = None,
    ) -> Optional[pd.DataFrame]:
        """
        准备节假日和停产日的 DataFrame 供 Prophet 使用

        Args:
            holidays: 节假日列表，每项格式:
                     {'ds': '2024-01-01', 'holiday': '元旦', 'lower_window': 0, 'upper_window': 1}
            shutdown_dates: 停产日日期列表

        Returns:
            Prophet 格式的 holidays DataFrame，若无可返回 None
        """
        holiday_rows = []

        if holidays:
            for h in holidays:
                row = {
                    'holiday': h.get('holiday', 'holiday'),
                    'ds': pd.to_datetime(h['ds']),
                    'lower_window': h.get('lower_window', 0),
                    'upper_window': h.get('upper_window', 0),
                }
                holiday_rows.append(row)

        if shutdown_dates:
            for sd in shutdown_dates:
                ds = pd.to_datetime(sd)
                row = {
                    'holiday': 'shutdown',
                    'ds': ds,
                    'lower_window': 0,
                    'upper_window': 0,
                }
                holiday_rows.append(row)

        if not holiday_rows:
            return None

        df = pd.DataFrame(holiday_rows)
        df['ds'] = pd.to_datetime(df['ds'])
        logger.info(f"准备节假日DataFrame完成: {len(holidays or [])}个节假日, "
                    f"{len(shutdown_dates or [])}个停产日")
        return df

    def _prepare_additional_regressors(
        self,
        df: pd.DataFrame,
        regressors: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        准备额外的 regressor 列

        Args:
            df: 原始 ds,y 数据 DataFrame
            regressors: 额外 regressor 字典 {name: values_array}

        Returns:
            (带regressor的DataFrame, regressor名称列表)
        """
        regressor_names = []
        if not regressors:
            return df, regressor_names

        for name, values in regressors.items():
            if len(values) != len(df):
                logger.warning(f"Regressor '{name}' 长度({len(values)})与数据长度({len(df)})不匹配，跳过")
                continue
            df[name] = values
            regressor_names.append(name)

        return df, regressor_names

    def _create_model(
        self,
        horizon_days: int,
        holidays_df: Optional[pd.DataFrame] = None,
        extra_regressor_names: Optional[List[str]] = None,
        yearly_seasonality: bool = False,
    ) -> Any:
        """
        创建 Prophet 模型实例

        根据 horizon 天数调整模型参数：
        - 短期 (7天): 更强的 changepoint 敏感度，适应快速变化
        - 中期 (30天): 平衡参数
        - 长期 (90天): 更强的正则化，避免过拟合

        Args:
            horizon_days: 预测天数，用于参数调优
            holidays_df: 节假日 DataFrame
            extra_regressor_names: 额外regressor名称列表
            yearly_seasonality: 是否启用年季节性

        Returns:
            Prophet 模型实例或 None
        """
        if not PROPHET_AVAILABLE:
            return None

        changepoint_prior_scale_map = {
            7: 0.10,
            30: 0.05,
            90: 0.02,
        }
        seasonality_prior_scale_map = {
            7: 15,
            30: 10,
            90: 5,
        }

        cps = changepoint_prior_scale_map.get(horizon_days, 0.05)
        sps = seasonality_prior_scale_map.get(horizon_days, 10)

        model = Prophet(
            yearly_seasonality=yearly_seasonality,
            weekly_seasonality=True,
            daily_seasonality=True,
            changepoint_prior_scale=cps,
            seasonality_prior_scale=sps,
            holidays=holidays_df,
            uncertainty_samples=self.uncertainty_samples,
            interval_width=0.95,
        )

        if extra_regressor_names:
            for name in extra_regressor_names:
                model.add_regressor(name, prior_scale=1.0, standardize='auto')

        logger.info(
            f"创建 Prophet 模型 (horizon={horizon_days}天, "
            f"changepoint_prior={cps}, seasonality_prior={sps}, "
            f"regressors={len(extra_regressor_names or [])})"
        )
        return model

    def fit(
        self,
        data: np.ndarray,
        timestamps: np.ndarray,
        holidays: Optional[List[Dict[str, Any]]] = None,
        shutdown_dates: Optional[List[Union[str, datetime]]] = None,
        extra_regressors: Optional[Dict[str, np.ndarray]] = None,
        horizons: Optional[List[int]] = None,
    ) -> None:
        """
        拟合多 horizon 模型

        Args:
            data: 预紧力数据值
            timestamps: 时间戳
            holidays: 节假日列表
            shutdown_dates: 停产日列表
            extra_regressors: 额外 regressor {name: values}
            horizons: 需要拟合的horizon列表，默认 [7, 30, 90]
        """
        horizons = horizons or self.SUPPORTED_HORIZONS
        valid_horizons = [h for h in horizons if h > 0]

        df = pd.DataFrame({
            'ds': pd.to_datetime(timestamps),
            'y': data.astype(float),
        })
        df = df.sort_values('ds').reset_index(drop=True)

        self.training_data = df.copy()

        holidays_df = self._prepare_holidays_dataframe(holidays, shutdown_dates)
        self.last_holidays_df = holidays_df
        self.last_regressors = extra_regressors or {}

        df_with_regs, reg_names = self._prepare_additional_regressors(
            df.copy(), extra_regressors
        )

        yearly_seasonality = self._should_enable_yearly(df)

        self.models.clear()
        for horizon in valid_horizons:
            if PROPHET_AVAILABLE:
                model = self._create_model(
                    horizon_days=horizon,
                    holidays_df=holidays_df,
                    extra_regressor_names=reg_names if reg_names else None,
                    yearly_seasonality=yearly_seasonality,
                )
                if model is not None:
                    try:
                        model.fit(df_with_regs)
                        self.models[horizon] = model
                        logger.info(f"Horizon {horizon}天模型拟合完成，数据点数: {len(df)}")
                    except Exception as e:
                        logger.error(f"Horizon {horizon}天模型拟合失败: {e}")
            else:
                self.models[horizon] = None

        self.is_fitted = len(self.models) > 0
        if self.is_fitted:
            logger.info(f"多horizon模型拟合完成，成功拟合 {len(self.models)}/{len(valid_horizons)} 个horizon")

    def _should_enable_yearly(self, df: pd.DataFrame) -> bool:
        """判断数据跨度是否足够启用年季节性"""
        if df.empty:
            return False
        span_days = (df['ds'].max() - df['ds'].min()).days
        return span_days >= 365 * 2

    def _extract_forecast_future(
        self,
        forecast_df: pd.DataFrame,
        training_df: pd.DataFrame,
        horizon_days: int,
    ) -> pd.DataFrame:
        """从完整forecast中提取未来部分"""
        last_train_date = training_df['ds'].max()
        future_mask = forecast_df['ds'] > last_train_date
        future = forecast_df[future_mask].head(horizon_days).copy()
        return future

    def _prophet_forecast_single(
        self,
        horizon_days: int,
    ) -> Optional[ForecastResult]:
        """
        对单个 horizon 执行 Prophet 预测

        Args:
            horizon_days: 预测天数

        Returns:
            ForecastResult 或 None
        """
        model = self.models.get(horizon_days)
        if model is None or self.training_data is None:
            return None

        future = model.make_future_dataframe(periods=horizon_days, freq='D')

        regressor_names = []
        if hasattr(model, 'extra_regressors') and model.extra_regressors:
            regressor_names = list(model.extra_regressors.keys())
            for name in regressor_names:
                if name in self.last_regressors:
                    vals = self.last_regressors[name]
                    hist_vals = list(vals[-len(self.training_data):])
                    future_vals = [hist_vals[-1]] * horizon_days
                    future[name] = hist_vals + future_vals

        forecast = model.predict(future)

        future_forecast = self._extract_forecast_future(
            forecast, self.training_data, horizon_days
        )

        if len(future_forecast) == 0:
            logger.warning(f"Horizon {horizon_days}天预测结果为空")
            return None

        dates = [pd.Timestamp(d).to_pydatetime() for d in future_forecast['ds'].tolist()]
        values = future_forecast['yhat'].values
        lower_bound = future_forecast['yhat_lower'].values
        upper_bound = future_forecast['yhat_upper'].values

        anomaly_dates, anomaly_type = self._detect_anomaly_periods(
            dates, values, lower_bound, upper_bound
        )

        confidence = self._calculate_forecast_confidence(
            values, lower_bound, upper_bound
        )

        return ForecastResult(
            horizon_days=horizon_days,
            dates=dates,
            values=values,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            anomaly_dates=anomaly_dates,
            anomaly_type=anomaly_type,
            confidence=confidence,
            confidence_level=0.95,
        )

    def _simple_forecast_single(
        self,
        horizon_days: int,
    ) -> Optional[ForecastResult]:
        """
        备选简单预测方案（Prophet不可用时）

        Args:
            horizon_days: 预测天数

        Returns:
            ForecastResult
        """
        if self.training_data is None:
            return None

        df = self.training_data
        last_date = df['ds'].max()

        n = len(df)
        x = np.arange(n)
        y = df['y'].values

        coeffs = np.polyfit(x, y, min(2, n - 1)) if n > 1 else np.array([0, np.mean(y)])
        poly = np.poly1d(coeffs)

        future_x = np.arange(n, n + horizon_days)
        predicted_values = poly(future_x)

        residuals = y - poly(x)
        std_residual = np.std(residuals) if len(residuals) > 0 else 1.0

        ci_width_scale = {
            7: 1.5,
            30: 2.0,
            90: 2.5,
        }
        scale = ci_width_scale.get(horizon_days, 2.0)
        t_factor = scale * np.sqrt(1 + (future_x - np.mean(x))**2 / np.sum((x - np.mean(x))**2))

        lower_bound = predicted_values - t_factor * std_residual
        upper_bound = predicted_values + t_factor * std_residual

        dates = [last_date + timedelta(days=i + 1) for i in range(horizon_days)]

        anomaly_dates, anomaly_type = self._detect_anomaly_periods(
            dates, predicted_values, lower_bound, upper_bound
        )

        confidence = self._calculate_forecast_confidence(
            predicted_values, lower_bound, upper_bound
        )

        return ForecastResult(
            horizon_days=horizon_days,
            dates=dates,
            values=predicted_values,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            anomaly_dates=anomaly_dates,
            anomaly_type=anomaly_type,
            confidence=confidence,
            confidence_level=0.95,
        )

    def forecast_single(
        self,
        horizon_days: int,
        historical_data: Optional[np.ndarray] = None,
        historical_timestamps: Optional[np.ndarray] = None,
        holidays: Optional[List[Dict[str, Any]]] = None,
        shutdown_dates: Optional[List[Union[str, datetime]]] = None,
    ) -> Optional[ForecastResult]:
        """
        预测单个 horizon

        Args:
            horizon_days: 预测天数
            historical_data: 历史数据（如果未拟合）
            historical_timestamps: 历史时间戳
            holidays: 节假日列表
            shutdown_dates: 停产日列表

        Returns:
            ForecastResult 或 None
        """
        if historical_data is not None and historical_timestamps is not None:
            self.fit(
                data=historical_data,
                timestamps=historical_timestamps,
                holidays=holidays,
                shutdown_dates=shutdown_dates,
                horizons=[horizon_days],
            )

        if not self.is_fitted:
            raise ValueError("模型未拟合，请先调用fit()或提供历史数据")

        model = self.models.get(horizon_days)
        if PROPHET_AVAILABLE and model is not None:
            return self._prophet_forecast_single(horizon_days)
        else:
            return self._simple_forecast_single(horizon_days)

    def forecast_multi_horizon(
        self,
        historical_data: Optional[np.ndarray] = None,
        historical_timestamps: Optional[np.ndarray] = None,
        horizons: Optional[List[int]] = None,
        holidays: Optional[List[Dict[str, Any]]] = None,
        shutdown_dates: Optional[List[Union[str, datetime]]] = None,
        extra_regressors: Optional[Dict[str, np.ndarray]] = None,
        include_decomposition: bool = True,
    ) -> MultiHorizonForecast:
        """
        多 horizon 预测 + 季节性分解（主入口方法）

        Args:
            historical_data: 历史数据值
            historical_timestamps: 历史时间戳
            horizons: 预测horizon列表，默认 [7, 30, 90]
            holidays: 节假日列表 [{'ds': '2024-01-01', 'holiday': '元旦', ...}]
            shutdown_dates: 停产日列表 ['2024-02-10', ...]
            extra_regressors: 额外 regressor {name: np.ndarray}
            include_decomposition: 是否输出季节性分解

        Returns:
            MultiHorizonForecast 综合结果
        """
        horizons = horizons or self.SUPPORTED_HORIZONS

        if historical_data is not None and historical_timestamps is not None:
            self.fit(
                data=historical_data,
                timestamps=historical_timestamps,
                holidays=holidays,
                shutdown_dates=shutdown_dates,
                extra_regressors=extra_regressors,
                horizons=horizons,
            )

        if not self.is_fitted:
            raise ValueError("模型未拟合，请先调用fit()或提供历史数据")

        result = MultiHorizonForecast()

        if self.training_data is not None:
            result.historical_dates = [
                pd.Timestamp(d).to_pydatetime()
                for d in self.training_data['ds'].tolist()
            ]
            result.historical_values = self.training_data['y'].values.copy()

        for horizon in horizons:
            if PROPHET_AVAILABLE and self.models.get(horizon) is not None:
                fr = self._prophet_forecast_single(horizon)
            else:
                fr = self._simple_forecast_single(horizon)
            if fr is not None:
                result.forecasts[horizon] = fr

        if include_decomposition:
            result.decomposition = self._perform_decomposition()

        fitted_model = self.models.get(30) or (
            self.models.get(7) if 7 in self.models else
            (self.models.get(90) if 90 in self.models else None)
        )
        result.model_parameters = {
            'prophet_available': PROPHET_AVAILABLE,
            'fitted_horizons': list(self.models.keys()),
            'uncertainty_samples': self.uncertainty_samples,
            'model_info': (
                self._extract_model_params(fitted_model)
                if PROPHET_AVAILABLE and fitted_model is not None
                else {'method': 'simple_polynomial'}
            ),
        }

        if holidays:
            result.holidays_used = holidays
        if shutdown_dates:
            result.shutdown_dates_used = [
                pd.to_datetime(sd).isoformat() for sd in shutdown_dates
            ]

        logger.info(
            f"多horizon预测完成，成功生成 {len(result.forecasts)}/{len(horizons)} 个horizon结果"
        )
        return result

    def _extract_model_params(self, model: Any) -> Dict[str, Any]:
        """提取 Prophet 模型参数摘要"""
        if model is None:
            return {}
        params = {}
        try:
            params['changepoints_count'] = (
                len(model.changepoints) if hasattr(model, 'changepoints') else 0
            )
            if hasattr(model, 'seasonalities'):
                params['seasonalities'] = {
                    name: {
                        'period': s.get('period', 0),
                        'fourier_order': s.get('fourier_order', 0),
                        'prior_scale': s.get('prior_scale', 0),
                    }
                    for name, s in model.seasonalities.items()
                }
            if hasattr(model, 'extra_regressors'):
                params['extra_regressors'] = list(model.extra_regressors.keys())
            if hasattr(model, 'holidays') and model.holidays is not None:
                params['holidays_count'] = len(model.holidays)
            if hasattr(model, 'history'):
                params['training_samples'] = len(model.history)
        except Exception as e:
            logger.debug(f"提取模型参数异常(忽略): {e}")
        return params

    def _perform_decomposition(self) -> Optional[SeasonalDecomposition]:
        """
        执行季节性分解

        使用最大 horizon 的模型进行全周期分解（历史 + 最大预测期）
        """
        if not PROPHET_AVAILABLE or self.training_data is None or len(self.models) == 0:
            return self._simple_decomposition()

        max_horizon = max(self.models.keys())
        model = self.models.get(max_horizon)
        if model is None:
            return self._simple_decomposition()

        try:
            future = model.make_future_dataframe(periods=max_horizon, freq='D')

            regressor_names = []
            if hasattr(model, 'extra_regressors') and model.extra_regressors:
                regressor_names = list(model.extra_regressors.keys())
                for name in regressor_names:
                    if name in self.last_regressors:
                        vals = self.last_regressors[name]
                        hist_vals = list(vals[-len(self.training_data):])
                        future_vals = [hist_vals[-1]] * max_horizon
                        future[name] = hist_vals + future_vals

            forecast = model.predict(future)

            dates = [pd.Timestamp(d).to_pydatetime() for d in forecast['ds'].tolist()]
            trend = forecast['trend'].values

            weekly = forecast['weekly'].values if 'weekly' in forecast.columns else None
            daily = forecast['daily'].values if 'daily' in forecast.columns else None
            yearly = forecast['yearly'].values if 'yearly' in forecast.columns else None

            holiday_cols = [c for c in forecast.columns if c.startswith('holiday')]
            holidays_effect = None
            if holiday_cols:
                holidays_effect = forecast[holiday_cols].sum(axis=1).values

            regressor_effects: Dict[str, np.ndarray] = {}
            for name in regressor_names:
                if name in forecast.columns:
                    regressor_effects[name] = forecast[name].values

            residuals = None
            if len(self.training_data) > 0:
                last_train_idx = len(self.training_data)
                y_hist = self.training_data['y'].values
                yhat_hist = forecast['yhat'].values[:last_train_idx]
                if len(y_hist) == len(yhat_hist):
                    residuals_full = np.zeros(len(forecast))
                    residuals_full[:last_train_idx] = y_hist - yhat_hist
                    residuals_full[last_train_idx:] = np.nan
                    residuals = residuals_full

            logger.info(
                f"季节性分解完成: {len(dates)}个点, "
                f"趋势+周周期+日周期"
                f"{'+年周期' if yearly is not None else ''}"
                f"{'+节假日效应' if holidays_effect is not None else ''}"
            )

            return SeasonalDecomposition(
                dates=dates,
                trend=trend,
                weekly=weekly,
                daily=daily,
                yearly=yearly,
                holidays=holidays_effect,
                regressors=regressor_effects if regressor_effects else None,
                residuals=residuals,
            )

        except Exception as e:
            logger.error(f"季节性分解失败: {e}")
            return self._simple_decomposition()

    def _simple_decomposition(self) -> Optional[SeasonalDecomposition]:
        """
        备选季节性分解（Prophet不可用时的简单移动平均分解）
        """
        if self.training_data is None:
            return None

        df = self.training_data.sort_values('ds').copy()
        y = df['y'].values
        n = len(y)

        if n < 14:
            return SeasonalDecomposition(
                dates=[pd.Timestamp(d).to_pydatetime() for d in df['ds'].tolist()],
                trend=y.astype(float),
                weekly=np.zeros(n),
                daily=np.zeros(n),
            )

        try:
            from scipy.ndimage import uniform_filter1d
            trend = uniform_filter1d(y.astype(float), size=min(7, n // 2), mode='nearest')
        except Exception:
            window = min(7, n // 3)
            kernel = np.ones(window) / window
            trend = np.convolve(y.astype(float), kernel, mode='same')

        detrended = y - trend

        weekly = np.zeros(n)
        if n >= 14:
            dow = df['ds'].dt.dayofweek.values
            for d in range(7):
                mask = dow == d
                if np.any(mask):
                    weekly[mask] = np.mean(detrended[mask])

        daily = np.zeros(n)
        if n >= 48 and np.all(df['ds'].dt.hour.value_counts() > 0):
            hod = df['ds'].dt.hour.values
            for h in range(24):
                mask = hod == h
                if np.any(mask):
                    daily[mask] = np.mean((detrended - weekly)[mask])

        residuals = detrended - weekly - daily

        return SeasonalDecomposition(
            dates=[pd.Timestamp(d).to_pydatetime() for d in df['ds'].tolist()],
            trend=trend,
            weekly=weekly,
            daily=daily,
            residuals=residuals,
        )

    def _detect_anomaly_periods(
        self,
        dates: List[datetime],
        values: np.ndarray,
        lower_bound: np.ndarray,
        upper_bound: np.ndarray,
    ) -> Tuple[List[Tuple[datetime, datetime]], str]:
        """
        检测预测中的异常时间段
        """
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']
        warning_dev = self.thresholds['warning_deviation']
        critical_dev = self.thresholds['critical_deviation']

        warning_min = min_normal * (1 - warning_dev)
        warning_max = max_normal * (1 + warning_dev)
        critical_min = min_normal * (1 - critical_dev)
        critical_max = max_normal * (1 + critical_dev)

        anomaly_periods: List[Tuple[datetime, datetime]] = []
        anomaly_type = "正常"

        in_anomaly = False
        anomaly_start: Optional[datetime] = None
        current_anomaly_type = "正常"

        for i, (date, val, lb, ub) in enumerate(zip(dates, values, lower_bound, upper_bound)):
            is_anomaly = False
            point_type = "正常"

            if val < critical_min or ub < critical_min:
                is_anomaly = True
                point_type = "松动"
            elif val > critical_max or lb > critical_max:
                is_anomaly = True
                point_type = "过载"
            elif val < warning_min or ub < warning_min:
                is_anomaly = True
                point_type = "关注级预警"
            elif val > warning_max or lb > warning_max:
                is_anomaly = True
                point_type = "关注级预警"

            if is_anomaly:
                if not in_anomaly:
                    anomaly_start = date
                    in_anomaly = True
                    current_anomaly_type = point_type
                elif (
                    point_type in ["松动", "过载"]
                    and current_anomaly_type not in ["松动", "过载"]
                ):
                    current_anomaly_type = point_type
            else:
                if in_anomaly and anomaly_start is not None:
                    anomaly_periods.append((anomaly_start, dates[i - 1]))
                    in_anomaly = False
                    anomaly_type = current_anomaly_type

        if in_anomaly and anomaly_start is not None:
            anomaly_periods.append((anomaly_start, dates[-1]))
            anomaly_type = current_anomaly_type

        return anomaly_periods, anomaly_type

    def _calculate_forecast_confidence(
        self,
        values: np.ndarray,
        lower_bound: np.ndarray,
        upper_bound: np.ndarray,
    ) -> float:
        """
        基于预测区间宽度计算置信度
        """
        interval_width = upper_bound - lower_bound
        mean_width = np.mean(interval_width) if len(interval_width) > 0 else 0.0
        mean_value = np.mean(np.abs(values)) + 1e-6

        relative_uncertainty = mean_width / mean_value

        if relative_uncertainty < 0.05:
            confidence = 0.95
        elif relative_uncertainty < 0.1:
            confidence = 0.90
        elif relative_uncertainty < 0.2:
            confidence = 0.80
        elif relative_uncertainty < 0.3:
            confidence = 0.70
        else:
            confidence = max(0.5, 1.0 - relative_uncertainty)

        return float(confidence)

    # ==================== 向后兼容方法 ====================

    def forecast(
        self,
        days: int = 30,
        historical_data: Optional[np.ndarray] = None,
        historical_timestamps: Optional[np.ndarray] = None,
    ) -> ForecastResult:
        """
        [向后兼容] 预测未来趋势（单 horizon）

        原接口保持不变，内部调用新的多horizon预测。

        Args:
            days: 预测天数
            historical_data: 历史数据
            historical_timestamps: 历史时间戳

        Returns:
            ForecastResult（旧版格式，不含horizon_days字段也能正常工作）
        """
        result = self.forecast_multi_horizon(
            historical_data=historical_data,
            historical_timestamps=historical_timestamps,
            horizons=[days],
            include_decomposition=False,
        )

        fr = result.get_forecast(days)
        if fr is None:
            raise ValueError(f"无法生成 {days} 天预测")

        return ForecastResult(
            horizon_days=days,
            dates=fr.dates,
            values=fr.values,
            lower_bound=fr.lower_bound,
            upper_bound=fr.upper_bound,
            anomaly_dates=fr.anomaly_dates,
            anomaly_type=fr.anomaly_type,
            confidence=fr.confidence,
            confidence_level=fr.confidence_level,
        )

    def predict_status(
        self,
        historical_data: np.ndarray,
        historical_timestamps: np.ndarray,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        [向后兼容] 预测未来状态和异常
        """
        forecast_result = self.forecast(
            days=days,
            historical_data=historical_data,
            historical_timestamps=historical_timestamps,
        )

        pw_type = self._determine_warning_type(forecast_result)
        fault_type = self._determine_fault_type(forecast_result)
        rec_measures = self._generate_measures(pw_type, fault_type)
        begin_time, end_time = self._get_anomaly_timeframe(forecast_result)

        return {
            'pw_type': pw_type,
            'fault_type': fault_type,
            'begin_time': begin_time,
            'end_time': end_time,
            'confidence': forecast_result.confidence,
            'rec_measures': rec_measures,
            'forecast_values': forecast_result.values,
            'forecast_dates': forecast_result.dates,
        }

    def _determine_warning_type(self, result: ForecastResult) -> str:
        """确定预警类型"""
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']

        min_pred = np.min(result.values) if len(result.values) > 0 else min_normal
        max_pred = np.max(result.values) if len(result.values) > 0 else max_normal

        if min_pred < min_normal * 0.5 or max_pred > max_normal * 1.5:
            return "故障"
        elif len(result.anomaly_dates) > 0:
            if result.anomaly_type in ["松动", "过载", "断裂"]:
                return "紧急级预警"
            else:
                total_anomaly_days = sum(
                    (end - start).days + 1
                    for start, end in result.anomaly_dates
                )
                if total_anomaly_days > 7:
                    return "检查级预警"
                else:
                    return "关注级预警"
        else:
            return "正常"

    def _determine_fault_type(self, result: ForecastResult) -> Optional[str]:
        """确定故障类型"""
        if result.anomaly_type in ["松动", "过载", "断裂"]:
            return result.anomaly_type
        return None

    def _generate_measures(self, pw_type: str, fault_type: Optional[str]) -> str:
        """生成推荐措施"""
        measures = {
            "正常": "继续保持正常监测，按照维护计划执行。",
            "关注级预警": "加强监测频率，记录异常特征，关注后续几天的变化趋势。",
            "检查级预警": "建议组织专业检查，判定异常类型，制定维护方案。",
            "紧急级预警": "需要立即采取措施，评估是否需要临时停机检修。",
            "故障": "紧急停机处理，排查故障原因，更换损坏部件。"
        }

        base_measure = measures.get(pw_type, "请联系技术人员评估。")

        if fault_type == "松动":
            base_measure += " 注意：可能出现螺栓松动，需要检查预紧力并重新紧固。"
        elif fault_type == "过载":
            base_measure += " 注意：预紧力可能超标，检查是否存在过载情况。"
        elif fault_type == "断裂":
            base_measure += " 紧急：可能发生螺栓断裂，需要立即停机检查更换。"

        return base_measure

    def _get_anomaly_timeframe(
        self,
        result: ForecastResult,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取异常时间范围"""
        if not result.anomaly_dates:
            return None, None

        first_anomaly = result.anomaly_dates[0]
        return first_anomaly[0], result.anomaly_dates[-1][1]
