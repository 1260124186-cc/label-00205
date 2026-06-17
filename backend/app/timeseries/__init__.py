"""
时序数据库接入层

提供统一的时序数据访问接口，支持多种后端实现：
- InfluxDB: 高性能时序数据库，适合高并发写入
- TimescaleDB: 基于 PostgreSQL 的时序扩展，支持 SQL 查询

核心特性：
- 统一的 Repository 抽象接口
- 多级降采样（1s 原始、1min、1h 聚合）
- 热写冷读架构
- 预测流水线窗口读取
- 历史分析 SQL 查询
"""

from app.timeseries.base import (
    TimeSeriesRepository,
    TimeSeriesDataPoint,
    TimeSeriesQuery,
    AggregationLevel,
    AggregatedDataPoint,
)
from app.timeseries.factory import create_timeseries_repository
from app.timeseries.downsampling import DownsamplingEngine

__all__ = [
    'TimeSeriesRepository',
    'TimeSeriesDataPoint',
    'TimeSeriesQuery',
    'AggregationLevel',
    'AggregatedDataPoint',
    'create_timeseries_repository',
    'DownsamplingEngine',
]
