"""
时序数据库基础抽象

定义 TimeSeriesRepository 接口和相关数据模型，
为不同后端实现提供统一的契约。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Iterator


class AggregationLevel(str, Enum):
    """
    聚合级别

    - RAW: 原始数据（1秒粒度）
    - MINUTE: 分钟级聚合（1分钟）
    - HOUR: 小时级聚合（1小时）
    """
    RAW = "raw"
    MINUTE = "minute"
    HOUR = "hour"

    @classmethod
    def from_resolution(cls, seconds: int) -> 'AggregationLevel':
        """根据秒数推断聚合级别"""
        if seconds <= 1:
            return cls.RAW
        elif seconds <= 60:
            return cls.MINUTE
        else:
            return cls.HOUR

    def to_seconds(self) -> int:
        """转换为秒数"""
        mapping = {
            AggregationLevel.RAW: 1,
            AggregationLevel.MINUTE: 60,
            AggregationLevel.HOUR: 3600,
        }
        return mapping[self]


@dataclass
class TimeSeriesDataPoint:
    """
    时序数据点（原始数据）

    Attributes:
        timestamp: 时间戳
        sensor_id: 传感器/螺栓ID
        value: 主测量值（预紧力）
        fields: 其他测量字段（温度、湿度、振动等）
        tags: 标签/维度（采集器、分线器、位置等）
    """
    timestamp: datetime
    sensor_id: str
    value: float
    fields: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'value': self.value,
            'fields': self.fields,
            'tags': self.tags,
        }


@dataclass
class AggregatedDataPoint:
    """
    聚合数据点

    Attributes:
        timestamp: 时间窗口起始时间
        sensor_id: 传感器/螺栓ID
        open: 窗口起始值
        high: 窗口最大值
        low: 窗口最小值
        close: 窗口结束值
        mean: 窗口平均值
        std: 窗口标准差
        count: 窗口内数据点数
        sum: 窗口内值总和
        level: 聚合级别
    """
    timestamp: datetime
    sensor_id: str
    open: float
    high: float
    low: float
    close: float
    mean: float
    std: float
    count: int
    sum: float
    level: AggregationLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'mean': self.mean,
            'std': self.std,
            'count': self.count,
            'sum': self.sum,
            'level': self.level.value,
        }


@dataclass
class TimeSeriesQuery:
    """
    时序查询参数

    Attributes:
        sensor_id: 传感器ID（可选，None表示查询全部）
        start_time: 起始时间（含）
        end_time: 结束时间（含）
        aggregation_level: 聚合级别
        limit: 返回数据点上限
        offset: 分页偏移
        order: 排序方向（asc/desc）
        fields: 指定返回的字段（None表示全部）
    """
    start_time: datetime
    end_time: datetime
    sensor_id: Optional[str] = None
    aggregation_level: AggregationLevel = AggregationLevel.RAW
    limit: Optional[int] = None
    offset: int = 0
    order: str = "asc"
    fields: Optional[List[str]] = None

    def validate(self) -> bool:
        """验证查询参数"""
        if self.start_time >= self.end_time:
            return False
        if self.limit is not None and self.limit <= 0:
            return False
        if self.offset < 0:
            return False
        if self.order not in ("asc", "desc"):
            return False
        return True


class TimeSeriesRepository(ABC):
    """
    时序数据库仓库抽象接口

    定义所有时序数据库后端必须实现的操作。
    遵循 Repository 模式，将数据访问逻辑与业务逻辑分离。
    """

    # ---------- 写入接口 ----------

    @abstractmethod
    def write_point(self, point: TimeSeriesDataPoint) -> bool:
        """
        写入单个数据点（热写路径）

        Args:
            point: 时序数据点

        Returns:
            bool: 是否写入成功
        """
        pass

    @abstractmethod
    def write_batch(self, points: List[TimeSeriesDataPoint]) -> int:
        """
        批量写入数据点（热写路径）

        Args:
            points: 时序数据点列表

        Returns:
            int: 成功写入的数量
        """
        pass

    # ---------- 查询接口 ----------

    @abstractmethod
    def query_raw(
        self,
        query: TimeSeriesQuery,
    ) -> List[TimeSeriesDataPoint]:
        """
        查询原始时序数据

        Args:
            query: 查询参数

        Returns:
            原始数据点列表
        """
        pass

    @abstractmethod
    def query_aggregated(
        self,
        query: TimeSeriesQuery,
    ) -> List[AggregatedDataPoint]:
        """
        查询聚合时序数据

        Args:
            query: 查询参数（aggregation_level 指定聚合粒度）

        Returns:
            聚合数据点列表
        """
        pass

    @abstractmethod
    def query_latest(
        self,
        sensor_id: str,
        limit: int = 100,
    ) -> List[TimeSeriesDataPoint]:
        """
        查询最近 N 个数据点（预测流水线用）

        Args:
            sensor_id: 传感器ID
            limit: 返回数据点数

        Returns:
            最近的数据点列表（按时间升序）
        """
        pass

    def query_prediction_window(
        self,
        sensor_id: str,
        window_size: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """
        查询预测窗口数据（近100点）

        专为预测流水线优化的接口，返回 numpy 友好的格式。

        Args:
            sensor_id: 传感器ID
            window_size: 窗口大小（数据点数）

        Returns:
            {'data': 值数组, 'timestamps': 时间戳数组}，无数据时返回 None
        """
        import numpy as np

        points = self.query_latest(sensor_id, limit=window_size)
        if not points:
            return None

        points_sorted = sorted(points, key=lambda p: p.timestamp)

        return {
            'data': np.array([p.value for p in points_sorted]),
            'timestamps': np.array([p.timestamp for p in points_sorted]),
        }

    # ---------- 统计接口 ----------

    @abstractmethod
    def count_points(
        self,
        query: TimeSeriesQuery,
    ) -> int:
        """
        统计数据点数量

        Args:
            query: 查询参数（使用 sensor_id, start_time, end_time）

        Returns:
            数据点总数
        """
        pass

    def get_statistics(
        self,
        query: TimeSeriesQuery,
    ) -> Optional[Dict[str, float]]:
        """
        获取统计信息（均值/极值/标准差等）

        此为默认实现（基于原始数据计算），后端可覆写以优化性能。

        Args:
            query: 查询参数

        Returns:
            统计字典 {'count', 'mean', 'std', 'min', 'max', 'sum', 'first', 'last'}
            无数据时返回 None
        """
        import numpy as np

        points = self.query_raw(query)
        if not points:
            return None

        values = np.array([p.value for p in points])
        return {
            'count': int(len(values)),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)) if len(values) > 1 else 0.0,
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'sum': float(np.sum(values)),
            'first': float(values[0]),
            'last': float(values[-1]),
            'range': float(np.max(values) - np.min(values)),
        }

    @abstractmethod
    def list_sensors(self) -> List[str]:
        """
        列出所有传感器ID

        Returns:
            传感器ID列表
        """
        pass

    # ---------- 降采样接口 ----------

    @abstractmethod
    def run_downsampling(
        self,
        level: AggregationLevel,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sensor_ids: Optional[List[str]] = None,
    ) -> int:
        """
        执行降采样聚合

        将低级别的数据聚合为高级别的数据（如 raw -> minute -> hour）

        Args:
            level: 目标聚合级别
            start_time: 处理起始时间（可选，默认处理全部未聚合数据）
            end_time: 处理结束时间（可选）
            sensor_ids: 指定传感器ID列表（可选，默认全部）

        Returns:
            生成的聚合数据点数
        """
        pass

    def cleanup_expired(
        self,
        retention_days: Dict[AggregationLevel, int],
    ) -> Dict[str, int]:
        """
        清理过期数据（根据保留策略）

        Args:
            retention_days: {聚合级别: 保留天数} 字典

        Returns:
            {级别: 删除条数} 统计字典
        """
        from datetime import timedelta

        deleted = {}
        now = datetime.now()

        for level, days in retention_days.items():
            cutoff = now - timedelta(days=days)
            count = self._delete_before(level=level, cutoff_time=cutoff)
            deleted[level.value] = count

        return deleted

    @abstractmethod
    def _delete_before(
        self,
        level: AggregationLevel,
        cutoff_time: datetime,
    ) -> int:
        """
        删除指定级别 cutoff_time 之前的数据（内部实现）

        Args:
            level: 数据级别
            cutoff_time: 截止时间（此之前的数据将被删除）

        Returns:
            删除条数
        """
        pass

    def delete_by_sensor(
        self,
        sensor_id: str,
    ) -> int:
        """
        删除某个传感器的所有数据（含所有级别）

        Args:
            sensor_id: 传感器ID

        Returns:
            删除的数据点总数
        """
        deleted = 0
        for level in AggregationLevel:
            try:
                count = self._delete_sensor_at_level(sensor_id, level)
                deleted += count
            except Exception:
                continue
        return deleted

    @abstractmethod
    def _delete_sensor_at_level(
        self,
        sensor_id: str,
        level: AggregationLevel,
    ) -> int:
        """
        删除某个传感器指定级别的数据（内部实现）

        Args:
            sensor_id: 传感器ID
            level: 数据级别

        Returns:
            删除条数
        """
        pass

    # ---------- 管理接口 ----------

    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 数据库是否健康
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        关闭连接，释放资源
        """
        pass

    # ---------- SQL 查询接口（历史分析用） ----------

    @abstractmethod
    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行原生 SQL 查询（历史分析用）

        注意：仅 TimescaleDB 等支持 SQL 的后端完全支持此接口。
        InfluxDB 后端可能返回有限的 SQL 支持或抛出异常。

        Args:
            sql: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果字典列表
        """
        pass
