"""
InfluxDB 时序数据库后端实现

基于 InfluxDB v2.x 的时序数据库实现，
使用 Flux 查询语言进行数据查询和聚合。

注意：使用可选依赖 influxdb-client，
未安装时该模块导入失败但不影响其他后端。
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from app.timeseries.base import (
    TimeSeriesRepository,
    TimeSeriesDataPoint,
    TimeSeriesQuery,
    AggregationLevel,
    AggregatedDataPoint,
)


class InfluxDBRepository(TimeSeriesRepository):
    """
    InfluxDB 时序数据库仓库实现

    基于 InfluxDB v2.x API，支持：
    - 高并发写入（Line Protocol）
    - Flux 查询语言
    - 原生降采样（Task）
    """

    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: str = "",
        org: str = "bolt",
        bucket: str = "bolt_data",
        timeout: int = 30,
    ):
        """
        初始化 InfluxDB 连接

        Args:
            url: InfluxDB 服务地址
            token: 访问令牌
            org: 组织名称
            bucket: 存储桶名称
            timeout: 超时时间（秒）
        """
        try:
            from influxdb_client import InfluxDBClient, Point, WriteOptions
            from influxdb_client.client.write_api import SYNCHRONOUS
        except ImportError:
            raise ImportError(
                "influxdb-client 未安装，请运行: pip install influxdb-client"
            )

        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.timeout = timeout

        self._client = InfluxDBClient(
            url=url,
            token=token,
            org=org,
            timeout=timeout * 1000,
        )
        self._write_api = self._client.write_api(
            write_options=WriteOptions(
                batch_size=5000,
                flush_interval=1000,
                jitter_interval=200,
                retry_interval=5000,
                max_retries=3,
            )
        )
        self._query_api = self._client.query_api()
        self._delete_api = self._client.delete_api()

        self._Point = Point
        self._SYNCHRONOUS = SYNCHRONOUS

        logger.info(f"InfluxDB 连接成功: {url}, org={org}, bucket={bucket}")

    # ---------- 写入接口 ----------

    def write_point(self, point: TimeSeriesDataPoint) -> bool:
        """写入单个数据点"""
        try:
            influx_point = self._Point("bolt_data")
            influx_point.time(point.timestamp)
            influx_point.tag("sensor_id", point.sensor_id)
            influx_point.field("value", point.value)

            for key, val in point.fields.items():
                influx_point.field(key, val)

            for key, val in point.tags.items():
                influx_point.tag(key, val)

            self._write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=influx_point,
            )
            return True
        except Exception as e:
            logger.error(f"InfluxDB 写入失败: {e}")
            return False

    def write_batch(self, points: List[TimeSeriesDataPoint]) -> int:
        """批量写入数据点"""
        if not points:
            return 0

        try:
            influx_points = []
            for point in points:
                p = self._Point("bolt_data")
                p.time(point.timestamp)
                p.tag("sensor_id", point.sensor_id)
                p.field("value", point.value)

                for key, val in point.fields.items():
                    p.field(key, val)

                for key, val in point.tags.items():
                    p.tag(key, val)

                influx_points.append(p)

            self._write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=influx_points,
            )
            return len(points)
        except Exception as e:
            logger.error(f"InfluxDB 批量写入失败: {e}")
            return 0

    # ---------- 查询接口 ----------

    def query_raw(self, query: TimeSeriesQuery) -> List[TimeSeriesDataPoint]:
        """查询原始时序数据"""
        if not query.validate():
            logger.warning("查询参数无效")
            return []

        try:
            flux_query = self._build_flux_query(query, aggregated=False)
            tables = self._query_api.query(flux_query, org=self.org)

            points = []
            for table in tables:
                for record in table.records:
                    point = TimeSeriesDataPoint(
                        timestamp=record.get_time(),
                        sensor_id=record.values.get("sensor_id", ""),
                        value=record.get_value(),
                        fields={
                            k: v for k, v in record.values.items()
                            if k not in ("_time", "_value", "_field", "_measurement", "sensor_id")
                               and isinstance(v, (int, float))
                        },
                        tags={
                            k: str(v) for k, v in record.values.items()
                            if k not in ("_time", "_value", "_field", "_measurement")
                               and not isinstance(v, (int, float))
                        },
                    )
                    points.append(point)

            return points
        except Exception as e:
            logger.error(f"InfluxDB 查询失败: {e}")
            return []

    def query_aggregated(self, query: TimeSeriesQuery) -> List[AggregatedDataPoint]:
        """查询聚合时序数据"""
        if not query.validate():
            logger.warning("查询参数无效")
            return []

        try:
            flux_query = self._build_flux_query(query, aggregated=True)
            tables = self._query_api.query(flux_query, org=self.org)

            agg_points = []
            for table in tables:
                for record in table.records:
                    values = record.values
                    agg_point = AggregatedDataPoint(
                        timestamp=record.get_time(),
                        sensor_id=values.get("sensor_id", ""),
                        open=float(values.get("open", 0)),
                        high=float(values.get("max", 0)),
                        low=float(values.get("min", 0)),
                        close=float(values.get("close", 0)),
                        mean=float(values.get("mean", 0)),
                        std=float(values.get("stddev", 0)),
                        count=int(values.get("count", 0)),
                        sum=float(values.get("sum", 0)),
                        level=query.aggregation_level,
                    )
                    agg_points.append(agg_point)

            return agg_points
        except Exception as e:
            logger.error(f"InfluxDB 聚合查询失败: {e}")
            return []

    def query_latest(
        self,
        sensor_id: str,
        limit: int = 100,
    ) -> List[TimeSeriesDataPoint]:
        """查询最近 N 个数据点"""
        try:
            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: -{limit * 2}s)
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
                    |> filter(fn: (r) => r["_field"] == "value")
                    |> sort(columns: ["_time"], desc: true)
                    |> limit(n: {limit})
                    |> sort(columns: ["_time"], desc: false)
            '''

            tables = self._query_api.query(flux_query, org=self.org)

            points = []
            for table in tables:
                for record in table.records:
                    point = TimeSeriesDataPoint(
                        timestamp=record.get_time(),
                        sensor_id=record.values.get("sensor_id", ""),
                        value=record.get_value(),
                    )
                    points.append(point)

            return points
        except Exception as e:
            logger.error(f"InfluxDB 查询最新数据失败: {e}")
            return []

    # ---------- 统计接口 ----------

    def count_points(
        self,
        sensor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """统计数据点数量"""
        try:
            start = start_time.isoformat() if start_time else "-30d"
            end = end_time.isoformat() if end_time else "now()"

            sensor_filter = ""
            if sensor_id:
                sensor_filter = f'|> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")'

            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {end})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> count()
                    |> sum(column: "_value")
            '''

            tables = self._query_api.query(flux_query, org=self.org)
            total = 0
            for table in tables:
                for record in table.records:
                    total += int(record.get_value())
            return total
        except Exception as e:
            logger.error(f"InfluxDB 统计数据点失败: {e}")
            return 0

    def list_sensors(self) -> List[str]:
        """列出所有传感器ID"""
        try:
            flux_query = f'''
                import "influxdata/influxdb/schema"

                schema.tagValues(
                    bucket: "{self.bucket}",
                    tag: "sensor_id",
                    start: -30d
                )
            '''

            tables = self._query_api.query(flux_query, org=self.org)

            sensors = []
            for table in tables:
                for record in table.records:
                    sensors.append(record.get_value())

            return sorted(sensors)
        except Exception as e:
            logger.error(f"InfluxDB 查询传感器列表失败: {e}")
            return []

    # ---------- 降采样接口 ----------

    def run_downsampling(
        self,
        level: AggregationLevel,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sensor_ids: Optional[List[str]] = None,
    ) -> int:
        """执行降采样聚合"""
        from app.timeseries.downsampling import DownsamplingEngine

        engine = DownsamplingEngine(self)
        return engine.run_full(
            target_level=level,
            start_time=start_time,
            end_time=end_time,
            sensor_ids=sensor_ids,
        ).get(level.value, 0)

    # ---------- 管理接口 ----------

    def health_check(self) -> bool:
        """健康检查"""
        try:
            health = self._client.health()
            return health.status == "pass"
        except Exception as e:
            logger.error(f"InfluxDB 健康检查失败: {e}")
            return False

    def close(self) -> None:
        """关闭连接"""
        try:
            self._write_api.close()
            self._client.close()
            logger.info("InfluxDB 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 InfluxDB 连接失败: {e}")

    # ---------- SQL 查询接口 ----------

    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行 SQL 查询

        InfluxDB v2.x 不直接支持 SQL，此方法返回空列表。
        建议使用 Flux 查询或切换到 TimescaleDB 后端。
        """
        logger.warning("InfluxDB 不支持 SQL 查询，请使用 Flux 或切换到 TimescaleDB")
        return []

    # ---------- 内部方法 ----------

    def _build_flux_query(self, query: TimeSeriesQuery, aggregated: bool = False) -> str:
        """构建 Flux 查询语句"""
        start = query.start_time.isoformat()
        stop = query.end_time.isoformat()

        sensor_filter = ""
        if query.sensor_id:
            sensor_filter = f'|> filter(fn: (r) => r["sensor_id"] == "{query.sensor_id}")'

        limit_clause = ""
        if query.limit:
            limit_clause = f"|> limit(n: {query.limit}, offset: {query.offset})"

        order_direction = "desc" if query.order == "desc" else "false"

        if aggregated:
            window_seconds = query.aggregation_level.to_seconds()

            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(
                        every: {window_seconds}s,
                        fn: (tables=<-, column="_value") => tables
                            |> reduce(
                                identity: {{
                                    min: 0.0,
                                    max: 0.0,
                                    mean: 0.0,
                                    stddev: 0.0,
                                    count: 0.0,
                                    sum: 0.0,
                                    first: 0.0,
                                    last: 0.0
                                }},
                                fn: (r, accumulator) => {{
                                    count: accumulator.count + 1.0,
                                    sum: accumulator.sum + r._value,
                                    min: if accumulator.count == 0.0 then r._value else math.min(x: accumulator.min, y: r._value),
                                    max: if accumulator.count == 0.0 then r._value else math.max(x: accumulator.max, y: r._value),
                                    mean: (accumulator.mean * accumulator.count + r._value) / (accumulator.count + 1.0),
                                    stddev: 0.0,
                                    first: if accumulator.count == 0.0 then r._value else accumulator.first,
                                    last: r._value
                                }}
                            )
                            |> map(fn: (r) => ({{
                                r with
                                    open: r.first,
                                    close: r.last,
                                    high: r.max,
                                    low: r.min
                            }}))
                    )
                    |> sort(columns: ["_time"], desc: {order_direction})
                    {limit_clause}
            '''
        else:
            flux_query = f'''
                from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> sort(columns: ["_time"], desc: {order_direction})
                    {limit_clause}
            '''

        return flux_query
