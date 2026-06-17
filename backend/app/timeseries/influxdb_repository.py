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
        # 同步写入模式（保证 write() 返回后立即可查询）
        self._write_api = self._client.write_api(
            write_options=SYNCHRONOUS
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
            # InfluxDB 内部统一使用 UTC
            influx_point.time(self._to_utc(point.timestamp))
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
            # 等待 50ms 让 InfluxDB 索引更新，确保立即可查
            import time
            time.sleep(0.05)
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
                # InfluxDB 内部统一使用 UTC
                p.time(self._to_utc(point.timestamp))
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
            # 批量写入后等待 100ms 让索引更新
            import time
            time.sleep(0.1)
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
        query: TimeSeriesQuery,
    ) -> int:
        """统计数据点数量"""
        try:
            # InfluxDB 内部用 UTC，先转 UTC
            start = self._to_utc(query.start_time).isoformat() if query.start_time else "-30d"
            end = self._to_utc(query.end_time).isoformat() if query.end_time else "now()"

            sensor_filter = ""
            if query.sensor_id:
                sensor_filter = f'|> filter(fn: (r) => r["sensor_id"] == "{query.sensor_id}")'

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

    def _delete_before(
        self,
        level: AggregationLevel,
        cutoff_time: datetime,
    ) -> int:
        """删除指定级别 cutoff_time 之前的数据（InfluxDB 全级别处理）"""
        try:
            measurement_map = {
                AggregationLevel.RAW: "bolt_data",
                AggregationLevel.MINUTE: "bolt_data_minute",
                AggregationLevel.HOUR: "bolt_data_hour",
            }
            measurement = measurement_map.get(level, "bolt_data")

            delete_predicate = f'_measurement="{measurement}"'

            self._client.delete_api.delete(
                start="1970-01-01T00:00:00Z",
                # cutoff 转为 UTC
                stop=self._to_utc(cutoff_time).isoformat().replace("+00:00", "Z"),
                predicate=delete_predicate,
                bucket=self.bucket,
                org=self.org,
            )
            logger.info(f"过期清理 [{level.value}] 完成（cutoff={cutoff_time}）")
            return -1
        except Exception as e:
            logger.error(f"InfluxDB 过期清理失败 [{level.value}]: {e}")
            return 0

    def _delete_sensor_at_level(
        self,
        sensor_id: str,
        level: AggregationLevel,
    ) -> int:
        """删除某个传感器指定级别的数据"""
        try:
            measurement_map = {
                AggregationLevel.RAW: "bolt_data",
                AggregationLevel.MINUTE: "bolt_data_minute",
                AggregationLevel.HOUR: "bolt_data_hour",
            }
            measurement = measurement_map.get(level, "bolt_data")

            delete_predicate = f'_measurement="{measurement}" AND sensor_id="{sensor_id}"'

            self._client.delete_api.delete(
                start="1970-01-01T00:00:00Z",
                # stop 设为未来 1 小时 UTC，覆盖所有
                stop=self._to_utc(datetime.now()).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                predicate=delete_predicate,
                bucket=self.bucket,
                org=self.org,
            )
            return -1
        except Exception as e:
            logger.error(f"InfluxDB 删除传感器 {sensor_id} 数据失败 [{level.value}]: {e}")
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

    @staticmethod
    def _to_utc(dt: datetime) -> datetime:
        """
        将任意 datetime 转换为 UTC 带时区时间（InfluxDB 内部统一用 UTC）

        - 带时区的 → 转为 UTC
        - 不带时区的 → 按系统本地时区解释后转 UTC
        """
        from datetime import timezone as dt_timezone

        if dt.tzinfo is None:
            # 当作本地时间处理
            local_tz = datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=local_tz)
        return dt.astimezone(dt_timezone.utc)

    def _build_flux_query(self, query: TimeSeriesQuery, aggregated: bool = False) -> str:
        """构建 Flux 查询语句"""
        # InfluxDB 内部用 UTC，先转 UTC 再生成 ISO 字符串
        start = self._to_utc(query.start_time).isoformat()
        stop = self._to_utc(query.end_time).isoformat()

        sensor_filter = ""
        if query.sensor_id:
            sensor_filter = f'|> filter(fn: (r) => r["sensor_id"] == "{query.sensor_id}")'

        limit_clause = ""
        if query.limit:
            limit_clause = f"|> limit(n: {query.limit}, offset: {query.offset})"

        order_direction = "desc" if query.order == "desc" else "false"

        if aggregated:
            window_seconds = query.aggregation_level.to_seconds()

            # 多次聚合后 join 方式（注意：join 不能用 |> 链式，需直接调用）
            flux_query = f'''
                mean_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: mean, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "mean"}})

                min_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: min, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "min"}})

                max_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: max, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "max"}})

                count_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: count, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "count"}})

                sum_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: sum, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "sum"}})

                first_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: first, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "open"}})

                last_tbl = from(bucket: "{self.bucket}")
                    |> range(start: {start}, stop: {stop})
                    |> filter(fn: (r) => r["_measurement"] == "bolt_data")
                    |> filter(fn: (r) => r["_field"] == "value")
                    {sensor_filter}
                    |> aggregateWindow(every: {window_seconds}s, fn: last, createEmpty: false)
                    |> keep(columns: ["_time", "sensor_id", "_value"])
                    |> rename(columns: {{"_value": "close"}})

                // 多次 join（不能用 |> 链式，必须直接传 tables）
                step1 = join(tables: {{mean: mean_tbl, min: min_tbl}}, on: ["_time", "sensor_id"])
                step2 = join(tables: {{step1: step1, max: max_tbl}}, on: ["_time", "sensor_id"])
                step3 = join(tables: {{step2: step2, count: count_tbl}}, on: ["_time", "sensor_id"])
                step4 = join(tables: {{step3: step3, sum: sum_tbl}}, on: ["_time", "sensor_id"])
                step5 = join(tables: {{step4: step4, open: first_tbl}}, on: ["_time", "sensor_id"])
                step6 = join(tables: {{step5: step5, close: last_tbl}}, on: ["_time", "sensor_id"])

                step6
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
