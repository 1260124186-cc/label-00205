"""
Prophet时间序列预测模型

基于Facebook Prophet的时间序列预测，用于预测未来30天的状态趋势。

功能:
1. 预紧力趋势预测
2. 异常时间点预测
3. 不确定性量化
4. 季节性分解

使用示例:
    from app.models.prophet_forecaster import ProphetForecaster
    
    forecaster = ProphetForecaster()
    predictions = forecaster.forecast(historical_data, days=30)
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
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
    预测结果数据类
    
    Attributes:
        dates: 预测日期列表
        values: 预测值列表
        lower_bound: 下界列表
        upper_bound: 上界列表
        anomaly_dates: 预测的异常日期
        anomaly_type: 异常类型
        confidence: 预测置信度
    """
    dates: List[datetime]
    values: np.ndarray
    lower_bound: np.ndarray
    upper_bound: np.ndarray
    anomaly_dates: List[Tuple[datetime, datetime]]
    anomaly_type: str
    confidence: float


class ProphetForecaster:
    """
    Prophet时间序列预测器
    
    使用Prophet模型进行预紧力趋势预测。
    
    Attributes:
        model: Prophet模型实例
        thresholds: 预紧力阈值配置
        is_fitted: 是否已拟合
    """
    
    def __init__(self):
        """
        初始化预测器
        """
        self.model = None
        self.thresholds = config.get('risk_assessment.preload_thresholds', {
            'min_normal': 400,
            'max_normal': 800,
            'warning_deviation': 0.1,
            'critical_deviation': 0.2
        })
        self.is_fitted = False
        self.training_data = None
        
        logger.info("Prophet预测器初始化完成")
    
    def _create_model(self) -> Any:
        """
        创建Prophet模型
        
        Returns:
            Prophet模型实例或备选模型
        """
        if PROPHET_AVAILABLE:
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=True,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10,
                uncertainty_samples=1000
            )
            return model
        else:
            return None
    
    def fit(
        self, 
        data: np.ndarray, 
        timestamps: np.ndarray
    ) -> None:
        """
        拟合模型
        
        Args:
            data: 预紧力数据
            timestamps: 时间戳
        """
        # 创建DataFrame
        df = pd.DataFrame({
            'ds': pd.to_datetime(timestamps),
            'y': data
        })
        
        self.training_data = df
        
        if PROPHET_AVAILABLE:
            self.model = self._create_model()
            self.model.fit(df)
            self.is_fitted = True
            logger.info(f"Prophet模型拟合完成，数据点数: {len(df)}")
        else:
            # 使用简单的趋势分析作为备选
            self.is_fitted = True
            logger.info("使用备选方案进行趋势分析")
    
    def forecast(
        self,
        days: int = 30,
        historical_data: Optional[np.ndarray] = None,
        historical_timestamps: Optional[np.ndarray] = None
    ) -> ForecastResult:
        """
        预测未来趋势
        
        Args:
            days: 预测天数
            historical_data: 历史数据（如果未拟合）
            historical_timestamps: 历史时间戳
            
        Returns:
            ForecastResult: 预测结果
        """
        # 如果提供了新数据，重新拟合
        if historical_data is not None and historical_timestamps is not None:
            self.fit(historical_data, historical_timestamps)
        
        if not self.is_fitted:
            raise ValueError("模型未拟合，请先调用fit()或提供历史数据")
        
        if PROPHET_AVAILABLE and self.model is not None:
            return self._prophet_forecast(days)
        else:
            return self._simple_forecast(days)
    
    def _prophet_forecast(self, days: int) -> ForecastResult:
        """
        使用Prophet进行预测
        """
        # 创建未来日期
        future = self.model.make_future_dataframe(periods=days, freq='D')
        forecast = self.model.predict(future)
        
        # 提取预测部分
        future_forecast = forecast.tail(days)
        
        dates = future_forecast['ds'].tolist()
        values = future_forecast['yhat'].values
        lower_bound = future_forecast['yhat_lower'].values
        upper_bound = future_forecast['yhat_upper'].values
        
        # 检测异常日期
        anomaly_dates, anomaly_type = self._detect_anomaly_periods(
            dates, values, lower_bound, upper_bound
        )
        
        # 计算置信度
        confidence = self._calculate_forecast_confidence(
            values, lower_bound, upper_bound
        )
        
        return ForecastResult(
            dates=dates,
            values=values,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            anomaly_dates=anomaly_dates,
            anomaly_type=anomaly_type,
            confidence=confidence
        )
    
    def _simple_forecast(self, days: int) -> ForecastResult:
        """
        使用简单方法进行预测（Prophet不可用时的备选方案）
        """
        if self.training_data is None:
            raise ValueError("无训练数据")
        
        df = self.training_data
        last_date = df['ds'].max()
        
        # 计算趋势
        n = len(df)
        x = np.arange(n)
        y = df['y'].values
        
        # 线性拟合
        coeffs = np.polyfit(x, y, 1)
        slope, intercept = coeffs
        
        # 预测未来值
        future_x = np.arange(n, n + days)
        predicted_values = slope * future_x + intercept
        
        # 估计不确定性
        residuals = y - (slope * x + intercept)
        std_residual = np.std(residuals)
        
        lower_bound = predicted_values - 2 * std_residual
        upper_bound = predicted_values + 2 * std_residual
        
        # 生成日期
        dates = [last_date + timedelta(days=i+1) for i in range(days)]
        
        # 检测异常
        anomaly_dates, anomaly_type = self._detect_anomaly_periods(
            dates, predicted_values, lower_bound, upper_bound
        )
        
        confidence = self._calculate_forecast_confidence(
            predicted_values, lower_bound, upper_bound
        )
        
        return ForecastResult(
            dates=dates,
            values=predicted_values,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            anomaly_dates=anomaly_dates,
            anomaly_type=anomaly_type,
            confidence=confidence
        )
    
    def _detect_anomaly_periods(
        self,
        dates: List[datetime],
        values: np.ndarray,
        lower_bound: np.ndarray,
        upper_bound: np.ndarray
    ) -> Tuple[List[Tuple[datetime, datetime]], str]:
        """
        检测预测中的异常时间段
        
        Returns:
            Tuple: (异常时间段列表, 异常类型)
        """
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']
        warning_dev = self.thresholds['warning_deviation']
        critical_dev = self.thresholds['critical_deviation']
        
        warning_min = min_normal * (1 - warning_dev)
        warning_max = max_normal * (1 + warning_dev)
        critical_min = min_normal * (1 - critical_dev)
        critical_max = max_normal * (1 + critical_dev)
        
        anomaly_periods = []
        anomaly_type = "正常"
        
        in_anomaly = False
        anomaly_start = None
        
        for i, (date, val, lb, ub) in enumerate(zip(dates, values, lower_bound, upper_bound)):
            is_anomaly = False
            current_type = "正常"
            
            # 检查不同类型的异常
            if val < critical_min or ub < critical_min:
                is_anomaly = True
                current_type = "松动"
            elif val > critical_max or lb > critical_max:
                is_anomaly = True
                current_type = "过载"
            elif val < warning_min or ub < warning_min:
                is_anomaly = True
                current_type = "关注级预警"
            elif val > warning_max or lb > warning_max:
                is_anomaly = True
                current_type = "关注级预警"
            
            if is_anomaly:
                if not in_anomaly:
                    anomaly_start = date
                    in_anomaly = True
                anomaly_type = current_type
            else:
                if in_anomaly:
                    anomaly_periods.append((anomaly_start, dates[i-1]))
                    in_anomaly = False
        
        # 处理最后一个异常段
        if in_anomaly:
            anomaly_periods.append((anomaly_start, dates[-1]))
        
        return anomaly_periods, anomaly_type
    
    def _calculate_forecast_confidence(
        self,
        values: np.ndarray,
        lower_bound: np.ndarray,
        upper_bound: np.ndarray
    ) -> float:
        """
        计算预测置信度
        """
        # 基于预测区间的宽度计算置信度
        interval_width = upper_bound - lower_bound
        mean_width = np.mean(interval_width)
        mean_value = np.mean(np.abs(values)) + 1e-6
        
        relative_uncertainty = mean_width / mean_value
        
        # 不确定性越小，置信度越高
        if relative_uncertainty < 0.1:
            confidence = 0.9
        elif relative_uncertainty < 0.2:
            confidence = 0.8
        elif relative_uncertainty < 0.3:
            confidence = 0.7
        else:
            confidence = max(0.5, 1.0 - relative_uncertainty)
        
        return confidence
    
    def predict_status(
        self,
        historical_data: np.ndarray,
        historical_timestamps: np.ndarray,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        预测未来状态和异常
        
        综合预测结果，返回结构化的状态预测。
        
        Args:
            historical_data: 历史预紧力数据
            historical_timestamps: 历史时间戳
            days: 预测天数
            
        Returns:
            Dict: 状态预测结果
        """
        # 执行预测
        forecast_result = self.forecast(
            days=days,
            historical_data=historical_data,
            historical_timestamps=historical_timestamps
        )
        
        # 确定预警类型
        pw_type = self._determine_warning_type(forecast_result)
        
        # 故障类型判断
        fault_type = self._determine_fault_type(forecast_result)
        
        # 推荐措施
        rec_measures = self._generate_measures(pw_type, fault_type)
        
        # 预计发生时间
        begin_time, end_time = self._get_anomaly_timeframe(forecast_result)
        
        return {
            'pw_type': pw_type,
            'fault_type': fault_type,
            'begin_time': begin_time,
            'end_time': end_time,
            'confidence': forecast_result.confidence,
            'rec_measures': rec_measures,
            'forecast_values': forecast_result.values,
            'forecast_dates': forecast_result.dates
        }
    
    def _determine_warning_type(self, result: ForecastResult) -> str:
        """确定预警类型"""
        min_normal = self.thresholds['min_normal']
        max_normal = self.thresholds['max_normal']
        
        min_pred = np.min(result.values)
        max_pred = np.max(result.values)
        
        # 检查是否有预测值超出范围
        if min_pred < min_normal * 0.5 or max_pred > max_normal * 1.5:
            return "故障"
        elif len(result.anomaly_dates) > 0:
            if result.anomaly_type in ["松动", "过载", "断裂"]:
                return "紧急级预警"
            else:
                # 根据异常持续时间判断
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
        result: ForecastResult
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取异常时间范围"""
        if not result.anomaly_dates:
            return None, None
        
        # 返回第一个异常段的起止时间
        first_anomaly = result.anomaly_dates[0]
        return first_anomaly[0], result.anomaly_dates[-1][1]
