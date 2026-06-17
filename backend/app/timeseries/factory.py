"""
时序数据库工厂

根据配置创建对应的时序数据库 Repository 实例。
支持通过配置动态切换后端实现。
"""

from typing import Optional
from loguru import logger

from app.utils.config import config
from app.timeseries.base import TimeSeriesRepository


class TimeSeriesBackendType:
    """时序数据库后端类型"""
    INFLUXDB = "influxdb"
    TIMESCALEDB = "timescaledb"
    NONE = "none"


def get_timeseries_config() -> dict:
    """
    获取时序数据库配置

    Returns:
        时序数据库配置字典
    """
    ts_config = config.get('timeseries', {})
    if not ts_config:
        return {
            'enabled': False,
            'backend': TimeSeriesBackendType.NONE,
        }
    return ts_config


def is_timeseries_enabled() -> bool:
    """
    检查时序数据库是否启用

    Returns:
        bool: 是否启用
    """
    ts_config = get_timeseries_config()
    return ts_config.get('enabled', False)


def create_timeseries_repository(
    backend: Optional[str] = None,
    **kwargs,
) -> Optional[TimeSeriesRepository]:
    """
    创建时序数据库 Repository 实例

    Args:
        backend: 后端类型，默认从配置读取
        **kwargs: 传递给后端构造函数的额外参数

    Returns:
        TimeSeriesRepository 实例，未启用时返回 None
    """
    ts_config = get_timeseries_config()

    if backend is None:
        backend = ts_config.get('backend', TimeSeriesBackendType.NONE)

    if not ts_config.get('enabled', False) and backend == TimeSeriesBackendType.NONE:
        logger.info("时序数据库未启用")
        return None

    try:
        if backend == TimeSeriesBackendType.INFLUXDB:
            from app.timeseries.influxdb_repository import InfluxDBRepository

            influx_config = ts_config.get('influxdb', {})
            repo = InfluxDBRepository(
                url=influx_config.get('url', 'http://localhost:8086'),
                token=influx_config.get('token', ''),
                org=influx_config.get('org', 'bolt'),
                bucket=influx_config.get('bucket', 'bolt_data'),
                **kwargs,
            )
            logger.info(f"InfluxDB Repository 创建成功: {influx_config.get('url')}")
            return repo

        elif backend == TimeSeriesBackendType.TIMESCALEDB:
            from app.timeseries.timescale_repository import TimescaleDBRepository

            timescale_config = ts_config.get('timescaledb', {})
            repo = TimescaleDBRepository(
                host=timescale_config.get('host', 'localhost'),
                port=timescale_config.get('port', 5432),
                user=timescale_config.get('user', 'postgres'),
                password=timescale_config.get('password', ''),
                database=timescale_config.get('database', 'bolt_timeseries'),
                **kwargs,
            )
            logger.info(f"TimescaleDB Repository 创建成功: {timescale_config.get('host')}")
            return repo

        else:
            logger.warning(f"未知的时序数据库后端: {backend}")
            return None

    except Exception as e:
        logger.error(f"创建时序数据库 Repository 失败: {e}")
        return None


# 全局单例
_repository_instance: Optional[TimeSeriesRepository] = None


def get_timeseries_repository() -> Optional[TimeSeriesRepository]:
    """
    获取全局时序数据库 Repository 单例

    Returns:
        TimeSeriesRepository 实例，未启用时返回 None
    """
    global _repository_instance

    if _repository_instance is None and is_timeseries_enabled():
        _repository_instance = create_timeseries_repository()

    return _repository_instance
