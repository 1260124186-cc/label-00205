"""
时序分析服务

提供基于时序数据库的历史分析功能：
- 趋势分析
- 统计聚合
- 同比环比分析
- 异常检测历史回溯
- 自定义 SQL 查询（TimescaleDB 后端）
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger

from app.timeseries.base import (
    TimeSeriesRepository,
    TimeSeriesQuery,
    AggregationLevel,
    AggregatedDataPoint,
    TimeSeriesDataPoint,
)
from app.timeseries.factory import get_timeseries_repository


class TimeSeriesAnalysisService:
    """
    时序分析服务

    提供高层的时序数据分析接口，封装底层 Repository 的查询。
    """

    def __init__(self, repository: Optional[TimeSeriesRepository] = None):
        """
        初始化时序分析服务

        Args:
            repository: 时序数据库仓库，默认使用全局实例
        """
        self.repository = repository or get_timeseries_repository()
        if self.repository is None:
            logger.warning("时序数据库未启用，时序分析服务不可用")

    def is_available(self) -> bool:
        """检查时序数据库是否可用"""
        return self.repository is not None and self.repository.health_check()

    # ---------- 趋势查询 ----------

    def get_trend(
        self,
        sensor_id: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: str = "auto",
    ) -> Dict[str, Any]:
        """
        获取趋势数据

        根据时间范围自动选择合适的聚合级别，
        确保返回合适数量的数据点（约100-300个）。

        Args:
            sensor_id: 传感器ID
            start_time: 起始时间
            end_time: 结束时间
            aggregation: 聚合级别 (raw/minute/hour/auto)

        Returns:
            趋势数据字典
        """
        if not self.is_available():
            return {'sensor_id': sensor_id, 'points': [], 'aggregation': 'none'}

        if aggregation == "auto":
            level = self._auto_select_aggregation(start_time, end_time)
        else:
            level = AggregationLevel(aggregation)

        query = TimeSeriesQuery(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time,
            aggregation_level=level,
            order="asc",
        )

        if level == AggregationLevel.RAW:
            points = self.repository.query_raw(query)
            return {
                'sensor_id': sensor_id,
                'aggregation': level.value,
                'point_count': len(points),
                'points': [
                    {
                        'timestamp': p.timestamp.isoformat(),
                        'value': p.value,
                    }
                    for p in points
                ],
            }
        else:
            points = self.repository.query_aggregated(query)
            return {
                'sensor_id': sensor_id,
                'aggregation': level.value,
                'point_count': len(points),
                'points': [
                    {
                        'timestamp': p.timestamp.isoformat(),
                        'open': p.open,
                        'high': p.high,
                        'low': p.low,
                        'close': p.close,
                        'mean': p.mean,
                        'std': p.std,
                        'count': p.count,
                    }
                    for p in points
                ],
            }

    # ---------- 统计分析 ----------

    def get_statistics(
        self,
        sensor_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """
        获取指定时间范围的统计数据

        Args:
            sensor_id: 传感器ID
            start_time: 起始时间
            end_time: 结束时间

        Returns:
            统计数据字典
        """
        if not self.is_available():
            return {'sensor_id': sensor_id, 'error': '时序数据库不可用'}

        query = TimeSeriesQuery(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time,
            aggregation_level=AggregationLevel.MINUTE,
            order="asc",
        )

        points = self.repository.query_aggregated(query)

        if not points:
            return {
                'sensor_id': sensor_id,
                'count': 0,
                'mean': 0,
                'std': 0,
                'min': 0,
                'max': 0,
                'trend': 'flat',
            }

        values = [p.mean for p in points]
        counts = [p.count for p in points]
        total_count = sum(counts)

        import numpy as np

        values_arr = np.array(values)

        # 计算趋势斜率
        if len(values_arr) > 1:
            x = np.arange(len(values_arr))
            slope, intercept = np.polyfit(x, values_arr, 1)
            if slope > 0.01 * values_arr.mean():
                trend = "rising"
            elif slope < -0.01 * values_arr.mean():
                trend = "falling"
            else:
                trend = "flat"
        else:
            trend = "flat"

        return {
            'sensor_id': sensor_id,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
            },
            'total_points': total_count,
            'aggregated_points': len(points),
            'statistics': {
                'mean': float(np.mean(values_arr)),
                'std': float(np.std(values_arr)),
                'min': float(np.min(values_arr)),
                'max': float(np.max(values_arr)),
                'median': float(np.median(values_arr)),
                'range': float(np.max(values_arr) - np.min(values_arr)),
            },
            'trend': {
                'direction': trend,
                'slope': float(slope) if len(values_arr) > 1 else 0,
                'change_pct': (
                    float((values_arr[-1] - values_arr[0]) / values_arr[0] * 100)
                    if len(values_arr) > 1 and values_arr[0] != 0
                    else 0
                ),
            },
        }

    # ---------- 同比环比分析 ----------

    def get_period_compare(
        self,
        sensor_id: str,
        current_start: datetime,
        current_end: datetime,
        compare_type: str = "mom",
    ) -> Dict[str, Any]:
        """
        周期对比分析

        Args:
            sensor_id: 传感器ID
            current_start: 当前周期起始
            current_end: 当前周期结束
            compare_type: 对比类型 (mom=环比, yoy=同比)

        Returns:
            对比分析结果
        """
        if not self.is_available():
            return {'sensor_id': sensor_id, 'error': '时序数据库不可用'}

        duration = current_end - current_start

        if compare_type == "mom":
            prev_start = current_start - duration
            prev_end = current_start
        elif compare_type == "yoy":
            prev_start = current_start.replace(year=current_start.year - 1)
            prev_end = current_end.replace(year=current_end.year - 1)
        else:
            raise ValueError(f"不支持的对比类型: {compare_type}")

        current_stats = self.get_statistics(sensor_id, current_start, current_end)
        prev_stats = self.get_statistics(sensor_id, prev_start, prev_end)

        curr_mean = current_stats.get('statistics', {}).get('mean', 0)
        prev_mean = prev_stats.get('statistics', {}).get('mean', 0)

        if prev_mean != 0:
            change_pct = (curr_mean - prev_mean) / prev_mean * 100
        else:
            change_pct = 0

        return {
            'sensor_id': sensor_id,
            'compare_type': compare_type,
            'current_period': {
                'start': current_start.isoformat(),
                'end': current_end.isoformat(),
                'mean': curr_mean,
            },
            'previous_period': {
                'start': prev_start.isoformat(),
                'end': prev_end.isoformat(),
                'mean': prev_mean,
            },
            'comparison': {
                'change_pct': change_pct,
                'change_abs': curr_mean - prev_mean,
                'direction': 'up' if change_pct > 0 else 'down' if change_pct < 0 else 'flat',
            },
        }

    # ---------- 批量传感器趋势 ----------

    def get_multi_sensor_trend(
        self,
        sensor_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        aggregation: str = "auto",
    ) -> Dict[str, Any]:
        """
        批量获取多个传感器的趋势数据

        Args:
            sensor_ids: 传感器ID列表
            start_time: 起始时间
            end_time: 结束时间
            aggregation: 聚合级别

        Returns:
            多传感器趋势数据
        """
        if not self.is_available():
            return {'sensors': [], 'error': '时序数据库不可用'}

        results = {}
        for sensor_id in sensor_ids:
            trend = self.get_trend(sensor_id, start_time, end_time, aggregation)
            results[sensor_id] = trend

        return {
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
            },
            'aggregation': aggregation,
            'sensors': results,
        }

    # ---------- SQL 查询（仅 TimescaleDB） ----------

    def execute_sql_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行自定义 SQL 查询

        注意：仅 TimescaleDB 后端支持完整的 SQL 查询。
        InfluxDB 后端会返回错误。

        Args:
            sql: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果
        """
        if not self.is_available():
            return {'error': '时序数据库不可用', 'results': []}

        try:
            results = self.repository.execute_sql(sql, params)
            return {
                'success': True,
                'row_count': len(results),
                'columns': list(results[0].keys()) if results else [],
                'results': results,
            }
        except Exception as e:
            logger.error(f"SQL 查询执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
            }

    # ---------- 内部方法 ----------

    def _auto_select_aggregation(
        self,
        start_time: datetime,
        end_time: datetime,
        target_points: int = 200,
    ) -> AggregationLevel:
        """
        根据时间范围自动选择合适的聚合级别

        Args:
            start_time: 起始时间
            end_time: 结束时间
            target_points: 目标数据点数

        Returns:
            推荐的聚合级别
        """
        duration_seconds = (end_time - start_time).total_seconds()

        # 计算各级别的数据点数
        raw_points = duration_seconds  # 假设1秒1个点
        minute_points = duration_seconds / 60
        hour_points = duration_seconds / 3600

        # 选择最接近目标点数的级别
        if abs(raw_points - target_points) < abs(minute_points - target_points):
            if raw_points > 0 and raw_points <= 1000:
                return AggregationLevel.RAW

        if abs(minute_points - target_points) < abs(hour_points - target_points):
            if minute_points > 0:
                return AggregationLevel.MINUTE

        return AggregationLevel.HOUR


    def prophet_multi_horizon_forecast(
        self,
        sensor_id: str,
        data_points: List[Dict[str, Any]],
        horizons: Optional[List[int]] = None,
        holidays: Optional[List[Dict[str, Any]]] = None,
        shutdown_dates: Optional[List[Any]] = None,
        extra_regressors: Optional[Dict[str, List[float]]] = None,
        include_decomposition: bool = True,
        uncertainty_samples: int = 1000,
    ) -> Dict[str, Any]:
        """
        Prophet 多周期预测 + 季节性分解（服务层入口）

        Args:
            sensor_id: 传感器ID
            data_points: 历史数据点列表 [{'timestamp': datetime, 'value': float}, ...]
            horizons: 预测horizon列表，默认 [7, 30, 90]
            holidays: 节假日列表 [{'ds': datetime, 'holiday': str, 'lower_window': int, 'upper_window': int}, ...]
            shutdown_dates: 停产日列表
            extra_regressors: 额外 regressor {name: values_list}
            include_decomposition: 是否包含季节性分解
            uncertainty_samples: 不确定性采样数

        Returns:
            可序列化的结果字典
        """
        import numpy as np
        import pandas as pd
        from app.models.prophet_forecaster import ProphetForecaster

        if not data_points or len(data_points) < 2:
            raise ValueError("历史数据点不足，至少需要2个数据点")

        try:
            timestamps = np.array([
                pd.Timestamp(p['timestamp']).to_pydatetime()
                for p in data_points
            ])
            values = np.array([float(p['value']) for p in data_points], dtype=np.float64)
        except Exception as e:
            raise ValueError(f"历史数据解析失败: {e}")

        valid_mask = ~np.isnan(values)
        if np.sum(valid_mask) < 2:
            raise ValueError("有效值数据点不足（NaN过多）")
        timestamps = timestamps[valid_mask]
        values = values[valid_mask]

        sort_idx = np.argsort(timestamps)
        timestamps = timestamps[sort_idx]
        values = values[sort_idx]

        regressors_np = None
        if extra_regressors:
            regressors_np = {}
            for name, vals in extra_regressors.items():
                arr = np.array(vals, dtype=np.float64)
                if len(arr) == len(valid_mask):
                    arr = arr[valid_mask][sort_idx]
                regressors_np[name] = arr

        if horizons is None:
            horizons = [7, 30, 90]

        forecaster = ProphetForecaster(uncertainty_samples=uncertainty_samples)

        try:
            forecast_result = forecaster.forecast_multi_horizon(
                historical_data=values,
                historical_timestamps=timestamps,
                horizons=horizons,
                holidays=holidays,
                shutdown_dates=shutdown_dates,
                extra_regressors=regressors_np,
                include_decomposition=include_decomposition,
            )
        except Exception as e:
            logger.error(f"ProphetForecaster执行失败: {e}")
            raise

        return forecast_result.to_dict()


# 全局服务单例
_analysis_service: Optional[TimeSeriesAnalysisService] = None


def get_timeseries_analysis_service() -> Optional[TimeSeriesAnalysisService]:
    """获取时序分析服务单例"""
    global _analysis_service
    if _analysis_service is None:
        repo = get_timeseries_repository()
        if repo is not None:
            _analysis_service = TimeSeriesAnalysisService(repo)
    if _analysis_service is None:
        _analysis_service = TimeSeriesAnalysisService(repository=None)
    return _analysis_service
