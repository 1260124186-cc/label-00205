"""
TimescaleDB 时序数据库后端实现

基于 PostgreSQL + TimescaleDB 扩展的时序数据库实现，
完全支持 SQL 查询，适合复杂历史分析场景。

注意：使用可选依赖 psycopg2 / sqlalchemy + timescale，
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


class TimescaleDBRepository(TimeSeriesRepository):
    """
    TimescaleDB 时序数据库仓库实现

    基于 TimescaleDB (PostgreSQL 扩展)，支持：
    - 完整的 SQL 查询能力
    - 原生 hypertables 和连续聚合
    - 高效的批量写入
    - 复杂的历史分析查询
    """

    RAW_TABLE = "bolt_data_raw"
    MINUTE_TABLE = "bolt_data_minute"
    HOUR_TABLE = "bolt_data_hour"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "postgres",
        password: str = "",
        database: str = "bolt_timeseries",
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        """
        初始化 TimescaleDB 连接

        Args:
            host: 主机地址
            port: 端口
            user: 用户名
            password: 密码
            database: 数据库名
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
        """
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
            import psycopg2
        except ImportError:
            raise ImportError(
                "psycopg2 和 sqlalchemy 未安装，请运行: pip install psycopg2-binary sqlalchemy"
            )

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self._dsn = (
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        )
        self._engine = create_engine(
            self._dsn,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        self._Session = sessionmaker(bind=self._engine)
        self._text = text

        self._ensure_schema()

        logger.info(
            f"TimescaleDB 连接成功: {host}:{port}/{database}, "
            f"pool_size={pool_size}"
        )

    # ---------- 写入接口 ----------

    def write_point(self, point: TimeSeriesDataPoint) -> bool:
        """写入单个数据点"""
        try:
            import json

            with self._Session() as session:
                fields_json = json.dumps(
                    {k: v for k, v in point.fields.items()} if point.fields else {}
                )
                tags_json = json.dumps(
                    {k: v for k, v in point.tags.items()} if point.tags else {}
                )

                sql = self._text(f"""
                    INSERT INTO {self.RAW_TABLE}
                    (time, sensor_id, value, fields, tags)
                    VALUES (:time, :sensor_id, :value, CAST(:fields AS JSONB), CAST(:tags AS JSONB))
                """)

                session.execute(sql, {
                    'time': point.timestamp,
                    'sensor_id': point.sensor_id,
                    'value': point.value,
                    'fields': fields_json,
                    'tags': tags_json,
                })
                session.commit()
                return True
        except Exception as e:
            logger.error(f"TimescaleDB 写入失败: {e}")
            return False

    def write_batch(self, points: List[TimeSeriesDataPoint]) -> int:
        """批量写入数据点"""
        if not points:
            return 0

        try:
            import json

            with self._Session() as session:
                rows = []
                for point in points:
                    fields_json = json.dumps(
                        {k: v for k, v in point.fields.items()} if point.fields else {}
                    )
                    tags_json = json.dumps(
                        {k: v for k, v in point.tags.items()} if point.tags else {}
                    )
                    rows.append({
                        'time': point.timestamp,
                        'sensor_id': point.sensor_id,
                        'value': point.value,
                        'fields': fields_json,
                        'tags': tags_json,
                    })

                sql = self._text(f"""
                    INSERT INTO {self.RAW_TABLE}
                    (time, sensor_id, value, fields, tags)
                    VALUES (:time, :sensor_id, :value, CAST(:fields AS JSONB), CAST(:tags AS JSONB))
                """)

                session.execute(sql, rows)
                session.commit()
                return len(points)
        except Exception as e:
            logger.error(f"TimescaleDB 批量写入失败: {e}")
            return 0

    # ---------- 查询接口 ----------

    def query_raw(self, query: TimeSeriesQuery) -> List[TimeSeriesDataPoint]:
        """查询原始时序数据"""
        if not query.validate():
            logger.warning("查询参数无效")
            return []

        try:
            where_clause = self._build_where_clause(query)
            order_clause = f"ORDER BY time {query.order}"
            limit_clause = ""
            if query.limit:
                limit_clause = f"LIMIT {query.limit} OFFSET {query.offset}"

            sql = self._text(f"""
                SELECT time, sensor_id, value, fields, tags
                FROM {self.RAW_TABLE}
                {where_clause}
                {order_clause}
                {limit_clause}
            """)

            params = self._build_query_params(query)

            with self._Session() as session:
                result = session.execute(sql, params)
                rows = result.fetchall()

            points = []
            for row in rows:
                point = TimeSeriesDataPoint(
                    timestamp=row.time,
                    sensor_id=str(row.sensor_id),
                    value=float(row.value),
                    fields=dict(row.fields) if row.fields else {},
                    tags=dict(row.tags) if row.tags else {},
                )
                points.append(point)

            return points
        except Exception as e:
            logger.error(f"TimescaleDB 查询失败: {e}")
            return []

    def query_aggregated(self, query: TimeSeriesQuery) -> List[AggregatedDataPoint]:
        """查询聚合时序数据"""
        if not query.validate():
            logger.warning("查询参数无效")
            return []

        table = self._get_agg_table(query.aggregation_level)
        interval = self._get_interval_sql(query.aggregation_level)

        try:
            if query.aggregation_level == AggregationLevel.RAW:
                raw_points = self.query_raw(query)
                from app.timeseries.downsampling import DownsamplingEngine
                engine = DownsamplingEngine(self)
                return engine.aggregate_points(raw_points, AggregationLevel.MINUTE)

            where_clause = self._build_where_clause(query, time_col="bucket")
            order_clause = f"ORDER BY bucket {query.order}"
            limit_clause = ""
            if query.limit:
                limit_clause = f"LIMIT {query.limit} OFFSET {query.offset}"

            sql = self._text(f"""
                SELECT
                    bucket,
                    sensor_id,
                    open,
                    high,
                    low,
                    close,
                    mean,
                    stddev,
                    count,
                    sum
                FROM {table}
                {where_clause}
                {order_clause}
                {limit_clause}
            """)

            params = self._build_query_params(query, time_col="bucket")

            with self._Session() as session:
                result = session.execute(sql, params)
                rows = result.fetchall()

            agg_points = []
            for row in rows:
                agg_point = AggregatedDataPoint(
                    timestamp=row.bucket,
                    sensor_id=str(row.sensor_id),
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    mean=float(row.mean),
                    std=float(row.stddev),
                    count=int(row.count),
                    sum=float(row.sum),
                    level=query.aggregation_level,
                )
                agg_points.append(agg_point)

            return agg_points
        except Exception as e:
            logger.error(f"TimescaleDB 聚合查询失败: {e}")
            return []

    def query_latest(
        self,
        sensor_id: str,
        limit: int = 100,
    ) -> List[TimeSeriesDataPoint]:
        """查询最近 N 个数据点"""
        try:
            sql = self._text(f"""
                SELECT time, sensor_id, value, fields, tags
                FROM {self.RAW_TABLE}
                WHERE sensor_id = :sensor_id
                ORDER BY time DESC
                LIMIT :limit
            """)

            with self._Session() as session:
                result = session.execute(sql, {'sensor_id': sensor_id, 'limit': limit})
                rows = result.fetchall()

            points = []
            for row in reversed(rows):
                point = TimeSeriesDataPoint(
                    timestamp=row.time,
                    sensor_id=str(row.sensor_id),
                    value=float(row.value),
                    fields=dict(row.fields) if row.fields else {},
                    tags=dict(row.tags) if row.tags else {},
                )
                points.append(point)

            return points
        except Exception as e:
            logger.error(f"TimescaleDB 查询最新数据失败: {e}")
            return []

    # ---------- 统计接口 ----------

    def count_points(
        self,
        query: TimeSeriesQuery,
    ) -> int:
        """统计数据点数量"""
        try:
            where_parts = []
            params = {}

            if query.sensor_id:
                where_parts.append("sensor_id = :sensor_id")
                params['sensor_id'] = query.sensor_id

            if query.start_time:
                where_parts.append("time >= :start_time")
                params['start_time'] = query.start_time

            if query.end_time:
                where_parts.append("time <= :end_time")
                params['end_time'] = query.end_time

            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)

            sql = self._text(f"""
                SELECT COUNT(*) as cnt
                FROM {self.RAW_TABLE}
                {where_clause}
            """)

            with self._Session() as session:
                result = session.execute(sql, params)
                row = result.fetchone()
                return int(row.cnt) if row else 0
        except Exception as e:
            logger.error(f"TimescaleDB 统计数据点失败: {e}")
            return 0

    def _delete_before(
        self,
        level: AggregationLevel,
        cutoff_time: datetime,
    ) -> int:
        """删除指定级别 cutoff_time 之前的数据"""
        try:
            if level == AggregationLevel.RAW:
                table = self.RAW_TABLE
                time_col = "time"
            else:
                table = self._get_agg_table(level)
                time_col = "bucket"

            sql = self._text(f"""
                DELETE FROM {table}
                WHERE {time_col} < :cutoff
            """)

            with self._Session() as session:
                result = session.execute(sql, {'cutoff': cutoff_time})
                count = result.rowcount
                session.commit()

            logger.info(f"过期清理 [{level.value}] 删除 {count} 条（cutoff={cutoff_time}）")
            return count
        except Exception as e:
            logger.error(f"TimescaleDB 过期清理失败 [{level.value}]: {e}")
            return 0

    def _delete_sensor_at_level(
        self,
        sensor_id: str,
        level: AggregationLevel,
    ) -> int:
        """删除某个传感器指定级别的数据"""
        try:
            if level == AggregationLevel.RAW:
                table = self.RAW_TABLE
                time_col = "time"
            else:
                table = self._get_agg_table(level)
                time_col = "bucket"

            sql = self._text(f"""
                DELETE FROM {table}
                WHERE sensor_id = :sensor_id
            """)

            with self._Session() as session:
                result = session.execute(sql, {'sensor_id': str(sensor_id)})
                count = result.rowcount
                session.commit()

            return count
        except Exception as e:
            logger.error(f"TimescaleDB 删除传感器 {sensor_id} 数据失败 [{level.value}]: {e}")
            return 0

    def list_sensors(self) -> List[str]:
        """列出所有传感器ID"""
        try:
            sql = self._text(f"""
                SELECT DISTINCT sensor_id
                FROM {self.RAW_TABLE}
                ORDER BY sensor_id
            """)

            with self._Session() as session:
                result = session.execute(sql)
                return [str(row.sensor_id) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"TimescaleDB 查询传感器列表失败: {e}")
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
        if level == AggregationLevel.RAW:
            logger.warning("RAW 级别不需要降采样")
            return 0

        target_table = self._get_agg_table(level)
        source_level = (
            AggregationLevel.MINUTE if level == AggregationLevel.HOUR
            else AggregationLevel.RAW
        )
        source_table = self._get_agg_table(source_level)
        interval = self._get_interval_sql(level)

        if end_time is None:
            end_time = datetime.now()

        if start_time is None:
            start_time = end_time - timedelta(days=7)

        try:
            sensor_filter = ""
            params = {
                'start_time': start_time,
                'end_time': end_time,
            }

            if sensor_ids:
                placeholders = ", ".join(
                    [f":sensor_{i}" for i in range(len(sensor_ids))]
                )
                sensor_filter = f"AND sensor_id IN ({placeholders})"
                for i, sid in enumerate(sensor_ids):
                    params[f'sensor_{i}'] = sid

            sql = self._text(f"""
                INSERT INTO {target_table} (bucket, sensor_id, open, high, low, close, mean, stddev, count, sum)
                SELECT
                    time_bucket(:interval, time) AS bucket,
                    sensor_id,
                    first(value, time) AS open,
                    max(value) AS high,
                    min(value) AS low,
                    last(value, time) AS close,
                    avg(value) AS mean,
                    stddev(value) AS stddev,
                    count(*) AS count,
                    sum(value) AS sum
                FROM {source_table}
                WHERE time >= :start_time
                  AND time < :end_time
                  {sensor_filter}
                GROUP BY bucket, sensor_id
                ON CONFLICT (bucket, sensor_id) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    mean = EXCLUDED.mean,
                    stddev = EXCLUDED.stddev,
                    count = EXCLUDED.count,
                    sum = EXCLUDED.sum
                RETURNING 1
            """)
            params['interval'] = interval

            with self._Session() as session:
                result = session.execute(sql, params)
                count = result.rowcount
                session.commit()

            logger.info(
                f"降采样完成: {source_level.value} -> {level.value}, "
                f"生成/更新 {count} 条聚合记录"
            )
            return count
        except Exception as e:
            logger.error(f"TimescaleDB 降采样失败: {e}")
            return 0

    # ---------- 管理接口 ----------

    def health_check(self) -> bool:
        """健康检查"""
        try:
            with self._Session() as session:
                session.execute(self._text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"TimescaleDB 健康检查失败: {e}")
            return False

    def close(self) -> None:
        """关闭连接"""
        try:
            self._engine.dispose()
            logger.info("TimescaleDB 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 TimescaleDB 连接失败: {e}")

    # ---------- SQL 查询接口 ----------

    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行原生 SQL 查询

        Args:
            sql: SQL 查询语句
            params: 查询参数字典

        Returns:
            查询结果字典列表
        """
        try:
            with self._Session() as session:
                result = session.execute(self._text(sql), params or {})
                columns = result.keys()
                return [
                    dict(zip(columns, row))
                    for row in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"TimescaleDB SQL 执行失败: {e}")
            return []

    # ---------- 内部方法 ----------

    def _ensure_schema(self) -> None:
        """确保数据库表结构存在"""
        try:
            with self._Session() as session:
                session.execute(self._text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                session.commit()

                self._create_raw_table(session)
                self._create_agg_table(session, self.MINUTE_TABLE, AggregationLevel.MINUTE)
                self._create_agg_table(session, self.HOUR_TABLE, AggregationLevel.HOUR)

                session.commit()

            logger.info("TimescaleDB 表结构初始化完成")
        except Exception as e:
            logger.error(f"TimescaleDB 表结构初始化失败: {e}")

    def _create_raw_table(self, session) -> None:
        """创建原始数据表（hypertable）"""
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.RAW_TABLE} (
                time TIMESTAMPTZ NOT NULL,
                sensor_id TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                fields JSONB DEFAULT '{{}}'::jsonb,
                tags JSONB DEFAULT '{{}}'::jsonb
            )
        """
        session.execute(self._text(create_sql))

        hypertable_sql = f"""
            SELECT create_hypertable(
                '{self.RAW_TABLE}',
                'time',
                if_not_exists => TRUE,
                chunk_time_interval => INTERVAL '1 day'
            )
        """
        session.execute(self._text(hypertable_sql))

        index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{self.RAW_TABLE}_sensor_time
            ON {self.RAW_TABLE} (sensor_id, time DESC)
        """
        session.execute(self._text(index_sql))

    def _create_agg_table(self, session, table_name: str, level: AggregationLevel) -> None:
        """创建聚合数据表（materialized view / continuous aggregate）"""
        interval = self._get_interval_sql(level)

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                bucket TIMESTAMPTZ NOT NULL,
                sensor_id TEXT NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                mean DOUBLE PRECISION NOT NULL,
                stddev DOUBLE PRECISION NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 0,
                sum DOUBLE PRECISION NOT NULL DEFAULT 0,
                PRIMARY KEY (bucket, sensor_id)
            )
        """
        session.execute(self._text(create_sql))

        index_sql = f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_sensor_bucket
            ON {table_name} (sensor_id, bucket DESC)
        """
        session.execute(self._text(index_sql))

    def _get_agg_table(self, level: AggregationLevel) -> str:
        """根据聚合级别获取表名"""
        mapping = {
            AggregationLevel.RAW: self.RAW_TABLE,
            AggregationLevel.MINUTE: self.MINUTE_TABLE,
            AggregationLevel.HOUR: self.HOUR_TABLE,
        }
        return mapping[level]

    def _get_interval_sql(self, level: AggregationLevel) -> str:
        """获取 SQL 时间间隔表达式"""
        mapping = {
            AggregationLevel.RAW: "1 second",
            AggregationLevel.MINUTE: "1 minute",
            AggregationLevel.HOUR: "1 hour",
        }
        return mapping[level]

    def _build_where_clause(self, query: TimeSeriesQuery, time_col: str = "time") -> str:
        """构建 WHERE 子句"""
        parts = [f"{time_col} >= :start_time", f"{time_col} <= :end_time"]

        if query.sensor_id:
            parts.append("sensor_id = :sensor_id")

        return "WHERE " + " AND ".join(parts)

    def _build_query_params(
        self,
        query: TimeSeriesQuery,
        time_col: str = "time",
    ) -> Dict[str, Any]:
        """构建查询参数字典"""
        params = {
            'start_time': query.start_time,
            'end_time': query.end_time,
        }

        if query.sensor_id:
            params['sensor_id'] = query.sensor_id

        return params
