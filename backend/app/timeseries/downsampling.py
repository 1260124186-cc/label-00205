"""
降采样引擎

实现多级降采样策略：
- raw (1s): 原始数据，保留热数据期（如7天）
- minute (1min): 分钟级聚合，保留中期数据（如30天）
- hour (1h): 小时级聚合，保留长期历史数据（如1年+）

支持两种工作模式：
1. 连续降采样：按时间窗口连续聚合（后台定时任务）
2. 按需降采样：指定时间范围手动触发（历史数据迁移后）
"""

import math
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from loguru import logger
from dataclasses import dataclass

from app.timeseries.base import (
    TimeSeriesDataPoint,
    AggregatedDataPoint,
    AggregationLevel,
    TimeSeriesRepository,
)


@dataclass
class DownsamplingPolicy:
    """
    降采样策略配置

    Attributes:
        level: 聚合级别
        source_level: 数据来源级别
        retention_days: 保留天数
        batch_size: 每批处理的数据点数
    """
    level: AggregationLevel
    source_level: AggregationLevel
    retention_days: int
    batch_size: int = 10000


DEFAULT_POLICIES = [
    DownsamplingPolicy(
        level=AggregationLevel.RAW,
        source_level=AggregationLevel.RAW,
        retention_days=7,
        batch_size=50000,
    ),
    DownsamplingPolicy(
        level=AggregationLevel.MINUTE,
        source_level=AggregationLevel.RAW,
        retention_days=30,
        batch_size=10000,
    ),
    DownsamplingPolicy(
        level=AggregationLevel.HOUR,
        source_level=AggregationLevel.MINUTE,
        retention_days=365,
        batch_size=1000,
    ),
]


class DownsamplingEngine:
    """
    降采样引擎

    负责将高粒度时序数据聚合为低粒度数据，
    实现多级存储策略，平衡查询性能和存储成本。
    """

    def __init__(
        self,
        repository: TimeSeriesRepository,
        policies: Optional[List[DownsamplingPolicy]] = None,
    ):
        """
        初始化降采样引擎

        Args:
            repository: 时序数据库仓库
            policies: 降采样策略列表，默认使用 DEFAULT_POLICIES
        """
        self.repository = repository
        self.policies = policies or DEFAULT_POLICIES
        self._policy_map = {p.level: p for p in self.policies}

    def get_policy(self, level: AggregationLevel) -> Optional[DownsamplingPolicy]:
        """获取指定级别的降采样策略"""
        return self._policy_map.get(level)

    def aggregate_points(
        self,
        points: List[TimeSeriesDataPoint],
        target_level: AggregationLevel,
    ) -> List[AggregatedDataPoint]:
        """
        将原始数据点聚合为指定粒度

        Args:
            points: 原始数据点列表
            target_level: 目标聚合级别

        Returns:
            聚合数据点列表
        """
        if not points:
            return []

        sensor_id = points[0].sensor_id
        interval_seconds = target_level.to_seconds()

        buckets: Dict[datetime, List[float]] = {}

        for point in points:
            ts = point.timestamp
            bucket_ts = self._align_timestamp(ts, interval_seconds)
            if bucket_ts not in buckets:
                buckets[bucket_ts] = []
            buckets[bucket_ts].append(point.value)

        aggregated = []
        for bucket_ts in sorted(buckets.keys()):
            values = buckets[bucket_ts]
            if not values:
                continue

            values_arr = np.array(values)
            agg_point = AggregatedDataPoint(
                timestamp=bucket_ts,
                sensor_id=sensor_id,
                open=float(values_arr[0]),
                high=float(np.max(values_arr)),
                low=float(np.min(values_arr)),
                close=float(values_arr[-1]),
                mean=float(np.mean(values_arr)),
                std=float(np.std(values_arr)) if len(values_arr) > 1 else 0.0,
                count=len(values_arr),
                sum=float(np.sum(values_arr)),
                level=target_level,
            )
            aggregated.append(agg_point)

        return aggregated

    def aggregate_aggregated(
        self,
        points: List[AggregatedDataPoint],
        target_level: AggregationLevel,
    ) -> List[AggregatedDataPoint]:
        """
        将聚合数据点进一步聚合为更粗粒度

        Args:
            points: 已聚合的数据点列表
            target_level: 目标聚合级别

        Returns:
            更粗粒度的聚合数据点列表
        """
        if not points:
            return []

        sensor_id = points[0].sensor_id
        interval_seconds = target_level.to_seconds()

        buckets: Dict[datetime, List[AggregatedDataPoint]] = {}

        for point in points:
            bucket_ts = self._align_timestamp(point.timestamp, interval_seconds)
            if bucket_ts not in buckets:
                buckets[bucket_ts] = []
            buckets[bucket_ts].append(point)

        aggregated = []
        for bucket_ts in sorted(buckets.keys()):
            bucket_points = buckets[bucket_ts]
            if not bucket_points:
                continue

            values = [p.mean for p in bucket_points]
            counts = [p.count for p in bucket_points]

            agg_point = AggregatedDataPoint(
                timestamp=bucket_ts,
                sensor_id=sensor_id,
                open=bucket_points[0].open,
                high=max(p.high for p in bucket_points),
                low=min(p.low for p in bucket_points),
                close=bucket_points[-1].close,
                mean=float(np.average(values, weights=counts)) if sum(counts) > 0 else 0.0,
                std=self._combine_std(bucket_points),
                count=sum(counts),
                sum=sum(p.sum for p in bucket_points),
                level=target_level,
            )
            aggregated.append(agg_point)

        return aggregated

    def run_for_sensor(
        self,
        sensor_id: str,
        target_level: AggregationLevel,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """
        对单个传感器执行降采样

        Args:
            sensor_id: 传感器ID
            target_level: 目标聚合级别
            start_time: 起始时间
            end_time: 结束时间

        Returns:
            生成的聚合数据点数
        """
        policy = self.get_policy(target_level)
        if not policy:
            logger.warning(f"未找到聚合级别 {target_level.value} 的策略")
            return 0

        source_level = policy.source_level

        if source_level == target_level:
            logger.warning(f"源级别与目标级别相同，跳过: {target_level.value}")
            return 0

        if end_time is None:
            # 统一使用带本地时区的 aware datetime，避免 naive/aware 比较报错
            end_time = datetime.now().astimezone()

        if start_time is None:
            retention = timedelta(days=policy.retention_days)
            start_time = end_time - retention
        else:
            # 确保 start_time 也是 aware
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=end_time.tzinfo)

        # 确保 end_time 是 aware（若传入的是 naive，则用本地时区）
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=datetime.now().astimezone().tzinfo)

        total_aggregated = 0
        batch_size = policy.batch_size
        current_start = start_time

        interval_seconds = target_level.to_seconds()
        time_batch = timedelta(seconds=batch_size * interval_seconds * 10)

        while current_start < end_time:
            batch_end = min(current_start + time_batch, end_time)

            from app.timeseries.base import TimeSeriesQuery

            query = TimeSeriesQuery(
                sensor_id=sensor_id,
                start_time=current_start,
                end_time=batch_end,
                aggregation_level=source_level,
                order="asc",
            )

            if source_level == AggregationLevel.RAW:
                raw_points = self.repository.query_raw(query)
                agg_points = self.aggregate_points(raw_points, target_level)
            else:
                raw_points = self.repository.query_aggregated(query)
                agg_points = self.aggregate_aggregated(raw_points, target_level)

            if agg_points:
                total_aggregated += len(agg_points)

            current_start = batch_end

        logger.info(
            f"传感器 {sensor_id} 降采样完成: "
            f"{source_level.value} -> {target_level.value}, "
            f"生成 {total_aggregated} 个聚合点"
        )
        return total_aggregated

    def run_full(
        self,
        target_level: Optional[AggregationLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sensor_ids: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        执行全量降采样

        Args:
            target_level: 目标聚合级别，None表示执行所有级别
            start_time: 起始时间
            end_time: 结束时间
            sensor_ids: 指定传感器ID列表

        Returns:
            各级别生成的聚合数据点数
        """
        results: Dict[str, int] = {}

        if sensor_ids is None:
            sensor_ids = self.repository.list_sensors()

        levels = (
            [target_level]
            if target_level
            else [AggregationLevel.MINUTE, AggregationLevel.HOUR]
        )

        for level in levels:
            logger.info(f"开始执行 {level.value} 级降采样")
            total = 0

            for sensor_id in sensor_ids:
                count = self.run_for_sensor(
                    sensor_id=sensor_id,
                    target_level=level,
                    start_time=start_time,
                    end_time=end_time,
                )
                total += count

            results[level.value] = total
            logger.info(f"{level.value} 级降采样完成，共生成 {total} 个聚合点")

        return results

    def cleanup_expired(self) -> Dict[str, int]:
        """
        清理过期数据

        根据保留策略清理各级别的过期数据。

        Returns:
            各级别清理的数据点数
        """
        results: Dict[str, int] = {}
        now = datetime.now()

        for policy in self.policies:
            cutoff_time = now - timedelta(days=policy.retention_days)
            count = self._delete_before(policy.level, cutoff_time)
            results[policy.level.value] = count
            logger.info(
                f"清理 {policy.level.value} 级别过期数据: "
                f"删除 {count} 条，截止时间 {cutoff_time}"
            )

        return results

    def _align_timestamp(self, ts: datetime, interval_seconds: int) -> datetime:
        """
        将时间戳对齐到指定时间间隔的起始点

        Args:
            ts: 原始时间戳
            interval_seconds: 时间间隔（秒）

        Returns:
            对齐后的时间戳
        """
        epoch = datetime(1970, 1, 1)
        delta = ts - epoch
        total_seconds = int(delta.total_seconds())
        aligned_seconds = (total_seconds // interval_seconds) * interval_seconds
        return epoch + timedelta(seconds=aligned_seconds)

    def _combine_std(self, points: List[AggregatedDataPoint]) -> float:
        """
        合并多个聚合组的标准差

        使用加权合并公式：
        combined_std = sqrt((sum((n_i-1)*s_i^2 + n_i*(mean_i - overall_mean)^2)) / (sum(n_i) - 1))

        Args:
            points: 聚合数据点列表

        Returns:
            合并后的标准差
        """
        if len(points) == 0:
            return 0.0
        if len(points) == 1:
            return points[0].std

        total_count = sum(p.count for p in points)
        if total_count <= 1:
            return 0.0

        overall_mean = sum(p.mean * p.count for p in points) / total_count

        sum_sq = sum(
            (p.count - 1) * (p.std ** 2) + p.count * ((p.mean - overall_mean) ** 2)
            for p in points
            if p.count > 1
        )

        return math.sqrt(sum_sq / (total_count - 1))

    def _delete_before(self, level: AggregationLevel, cutoff_time: datetime) -> int:
        """
        删除指定级别、指定时间之前的数据

        由具体 Repository 实现，这里提供默认的空实现。

        Args:
            level: 聚合级别
            cutoff_time: 截止时间

        Returns:
            删除的数据条数
        """
        logger.warning(
            f"Repository 未实现 delete_before 方法，跳过清理: {level.value}"
        )
        return 0
