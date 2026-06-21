"""
数据库连接池统一管理模块

提供高性能的数据库连接池管理功能，作为全系统唯一数据库访问入口。

功能:
1. 连接池管理（单例，所有 Repository / Service 经同一入口获取 Session）
2. 自动重试机制
3. 连接健康检查与泄漏检测
4. 慢查询日志（>500ms）
5. N+1 检测（同一 Session 短时间大量单行查询）
6. 连接池指标暴露（checkout_count、overflow、latency_ms）
7. 批量预测与分片任务连接池配额（防止连接耗尽）
8. 读写分离预留（主库写、从库读配置开关）

使用示例:
    from app.utils.db_pool import db_pool

    with db_pool.get_session() as session:
        data = session.query(BoltData).limit(100).all()

    with db_pool.get_session(read_only=True) as session:
        data = session.query(BoltData).all()

    with db_pool.quota_scope("batch_prediction", max_connections=3) as quota:
        with db_pool.get_session() as session:
            ...
"""

import time
import threading
import traceback
from collections import defaultdict
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from loguru import logger

from app.utils.config import config


SLOW_QUERY_THRESHOLD_MS = 500.0
N_PLUS_ONE_WINDOW_SECONDS = 2.0
N_PLUS_ONE_THRESHOLD = 10


@dataclass
class ConnectionStats:
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    overflow_connections: int = 0
    checkout_count: int = 0
    checkin_count: int = 0
    invalidated_count: int = 0
    slow_query_count: int = 0
    n_plus_one_detected: int = 0
    latency_samples: List[float] = field(default_factory=list)
    _latency_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_latency(self, ms: float) -> None:
        with self._latency_lock:
            self.latency_samples.append(ms)
            if len(self.latency_samples) > 1000:
                self.latency_samples = self.latency_samples[-500:]

    def get_latency_ms(self) -> Optional[float]:
        with self._latency_lock:
            if not self.latency_samples:
                return None
            return round(sum(self.latency_samples) / len(self.latency_samples), 2)


class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, error: Exception) -> bool:
        if attempt >= self.max_retries:
            return False
        if isinstance(error, OperationalError):
            return True
        return False


class NPlusOneDetector:
    def __init__(self, window_seconds: float = N_PLUS_ONE_WINDOW_SECONDS, threshold: int = N_PLUS_ONE_THRESHOLD):
        self._window_seconds = window_seconds
        self._threshold = threshold
        self._lock = threading.Lock()
        self._sessions: Dict[int, List[float]] = {}

    def record_query(self, session_id: int) -> bool:
        now = time.time()
        detected = False
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            timestamps = self._sessions[session_id]
            cutoff = now - self._window_seconds
            timestamps[:] = [t for t in timestamps if t >= cutoff]
            timestamps.append(now)
            if len(timestamps) >= self._threshold:
                detected = True
                caller = traceback.format_stack(limit=6)[-3].strip()
                logger.warning(
                    f"N+1 检测: session_id={session_id} 在 {self._window_seconds}s 内执行了 "
                    f"{len(timestamps)} 次查询 (阈值={self._threshold}), 调用位置: {caller}"
                )
        return detected

    def clear_session(self, session_id: int) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


class ConnectionQuota:
    def __init__(self, name: str, max_connections: int):
        self.name = name
        self.max_connections = max_connections
        self._current = 0
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_connections)

    def acquire(self, timeout: float = 30.0) -> bool:
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._current += 1
        return acquired

    def release(self) -> None:
        with self._lock:
            self._current = max(0, self._current - 1)
        self._semaphore.release()

    @property
    def current(self) -> int:
        with self._lock:
            return self._current

    @property
    def available(self) -> int:
        with self._lock:
            return self.max_connections - self._current


class DatabasePool:
    _instance: Optional['DatabasePool'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'DatabasePool':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        db_config = config.get('database', {})

        self.db_url = self._build_url(db_config)

        self._pool_config = {
            'pool_size': db_config.get('pool_size', 10),
            'max_overflow': db_config.get('max_overflow', 20),
            'pool_timeout': db_config.get('pool_timeout', 30),
            'pool_recycle': db_config.get('pool_recycle', 1800),
            'pool_pre_ping': True,
        }

        self.retry_policy = RetryPolicy(
            max_retries=db_config.get('max_retries', 3),
            base_delay=0.5
        )

        self.engine = None
        self.session_factory = None
        self.stats = ConnectionStats()

        self._slow_query_threshold_ms = db_config.get('slow_query_threshold_ms', SLOW_QUERY_THRESHOLD_MS)
        self._n_plus_one_detector = NPlusOneDetector(
            window_seconds=db_config.get('n_plus_one_window_seconds', N_PLUS_ONE_WINDOW_SECONDS),
            threshold=db_config.get('n_plus_one_threshold', N_PLUS_ONE_THRESHOLD),
        )

        self._read_write_split = db_config.get('read_write_split', {})
        self._slave_engine = None
        self._slave_session_factory = None

        self._quotas: Dict[str, ConnectionQuota] = {}
        self._quotas_lock = threading.Lock()

        quotas_config = db_config.get('quotas', {})
        for name, quota_cfg in quotas_config.items():
            max_conn = quota_cfg.get('max_connections', 3) if isinstance(quota_cfg, dict) else int(quota_cfg)
            quota = ConnectionQuota(name=name, max_connections=max_conn)
            self._quotas[name] = quota
            logger.info(f"注册连接池配额: name={name}, max_connections={max_conn}")

        self._initialized = True
        self._healthy = False

        logger.info(f"数据库连接池配置完成: pool_size={self._pool_config['pool_size']}")

    def _build_url(self, db_config: Dict) -> str:
        host = db_config.get('host', '127.0.0.1')
        port = db_config.get('port', 3306)
        user = db_config.get('user', 'root')
        password = db_config.get('password', '')
        database = db_config.get('database', 'bolt_preload')
        charset = db_config.get('charset', 'utf8mb4')
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"

    def _build_slave_url(self, slave_config: Dict) -> Optional[str]:
        host = slave_config.get('host')
        if not host:
            return None
        port = slave_config.get('port', 3306)
        user = slave_config.get('user', 'root')
        password = slave_config.get('password', '')
        database = slave_config.get('database')
        if not database:
            db_config = config.get('database', {})
            database = db_config.get('database', 'bolt_preload')
        charset = slave_config.get('charset', 'utf8mb4')
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"

    def _init_engine(self) -> bool:
        try:
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                **self._pool_config
            )
            self._register_events(self.engine)
            self.session_factory = sessionmaker(bind=self.engine)

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self._healthy = True

            self._init_slave_engine()

            logger.info("数据库连接池初始化成功")
            return True

        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            self._healthy = False
            return False

    def _init_slave_engine(self) -> None:
        if not self._read_write_split.get('enabled', False):
            return
        slave_config = self._read_write_split.get('slave', {})
        slave_url = self._build_slave_url(slave_config)
        if not slave_url:
            logger.warning("读写分离已启用但从库配置缺失，从库引擎未初始化")
            return
        try:
            slave_pool_config = {
                'pool_size': slave_config.get('pool_size', self._pool_config['pool_size']),
                'max_overflow': slave_config.get('max_overflow', self._pool_config['max_overflow']),
                'pool_timeout': slave_config.get('pool_timeout', self._pool_config['pool_timeout']),
                'pool_recycle': slave_config.get('pool_recycle', self._pool_config['pool_recycle']),
                'pool_pre_ping': True,
            }
            self._slave_engine = create_engine(
                slave_url,
                poolclass=QueuePool,
                **slave_pool_config
            )
            with self._slave_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._slave_session_factory = sessionmaker(bind=self._slave_engine)
            logger.info("从库连接池初始化成功")
        except Exception as e:
            logger.warning(f"从库连接池初始化失败，将回退到主库: {e}")
            self._slave_engine = None
            self._slave_session_factory = None

    def _register_events(self, engine) -> None:
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            self.stats.checkout_count += 1
            self.stats.active_connections += 1

        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_conn, connection_record):
            self.stats.checkin_count += 1
            self.stats.active_connections = max(0, self.stats.active_connections - 1)

        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            self.stats.invalidated_count += 1
            logger.warning(f"连接失效: {exception}")

        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            elapsed_ms = (time.time() - getattr(context, '_query_start_time', time.time())) * 1000
            self.stats.record_latency(elapsed_ms)
            if elapsed_ms > self._slow_query_threshold_ms:
                self.stats.slow_query_count += 1
                logger.warning(
                    f"慢查询 ({elapsed_ms:.1f}ms > {self._slow_query_threshold_ms}ms): "
                    f"{statement[:200]}"
                )

    def register_quota(self, name: str, max_connections: int) -> ConnectionQuota:
        with self._quotas_lock:
            if name in self._quotas:
                return self._quotas[name]
            quota = ConnectionQuota(name=name, max_connections=max_connections)
            self._quotas[name] = quota
            logger.info(f"注册连接池配额: name={name}, max_connections={max_connections}")
            return quota

    def get_quota(self, name: str) -> Optional[ConnectionQuota]:
        with self._quotas_lock:
            return self._quotas.get(name)

    @contextmanager
    def quota_scope(self, name: str, max_connections: int = 3) -> Generator[ConnectionQuota, None, None]:
        quota = self.register_quota(name, max_connections)
        acquired = quota.acquire(timeout=30.0)
        if not acquired:
            logger.warning(f"连接池配额 {name} 获取超时，当前 {quota.current}/{quota.max_connections}")
            yield quota
            return
        try:
            yield quota
        finally:
            quota.release()

    @contextmanager
    def get_session(self, read_only: bool = False) -> Generator[Optional[Session], None, None]:
        if self.engine is None:
            if not self._init_engine():
                yield None
                return

        use_slave = (
            read_only
            and self._read_write_split.get('enabled', False)
            and self._slave_session_factory is not None
        )
        session_factory = self._slave_session_factory if use_slave else self.session_factory
        session = None
        last_error = None
        session_id = id(threading.current_thread())

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                session = session_factory()
                self._n_plus_one_detector.clear_session(session_id)
                start = time.time()
                yield session
                elapsed_ms = (time.time() - start) * 1000
                self.stats.record_latency(elapsed_ms)
                session.commit()
                return

            except OperationalError as e:
                last_error = e
                if session:
                    session.rollback()
                if self.retry_policy.should_retry(attempt, e):
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(f"数据库操作失败，{delay:.1f}秒后重试 ({attempt + 1}/{self.retry_policy.max_retries})")
                    time.sleep(delay)
                else:
                    break

            except Exception as e:
                last_error = e
                if session:
                    session.rollback()
                break

            finally:
                if session:
                    self._n_plus_one_detector.clear_session(session_id)
                    session.close()

        logger.error(f"数据库操作最终失败: {last_error}")
        yield None

    @contextmanager
    def get_connection(self) -> Generator[Optional[Session], None, None]:
        with self.get_session() as session:
            yield session

    def track_query(self, session: Session) -> bool:
        session_id = id(session)
        detected = self._n_plus_one_detector.record_query(session_id)
        if detected:
            self.stats.n_plus_one_detected += 1
        return detected

    def execute_with_retry(
        self,
        query: str,
        params: Optional[Dict] = None,
        read_only: bool = False,
    ) -> Optional[Any]:
        with self.get_session(read_only=read_only) as session:
            if session is None:
                return None
            try:
                result = session.execute(text(query), params or {})
                return result
            except Exception as e:
                logger.error(f"SQL执行失败: {e}")
                return None

    def health_check(self) -> Dict[str, Any]:
        result = {
            'healthy': False,
            'latency_ms': None,
            'pool_stats': None,
            'slave_healthy': None,
            'error': None
        }

        if self.engine is None:
            if not self._init_engine():
                result['error'] = "无法初始化连接池"
                return result

        try:
            start = time.time()
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000

            result['healthy'] = True
            result['latency_ms'] = round(latency, 2)
            result['pool_stats'] = {
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'invalidated': self.stats.invalidated_count
            }

            if self._slave_engine is not None:
                try:
                    slave_start = time.time()
                    with self._slave_engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    slave_latency = (time.time() - slave_start) * 1000
                    result['slave_healthy'] = True
                    result['slave_latency_ms'] = round(slave_latency, 2)
                except Exception as e:
                    result['slave_healthy'] = False
                    result['slave_error'] = str(e)

        except Exception as e:
            result['error'] = str(e)
            self._healthy = False

        return result

    def get_stats(self) -> Dict[str, Any]:
        if self.engine is None:
            return {'status': 'not_initialized'}

        stats = {
            'pool_size': self.engine.pool.size(),
            'active': self.engine.pool.checkedout(),
            'idle': self.engine.pool.checkedin(),
            'overflow': self.engine.pool.overflow(),
            'checkout_count': self.stats.checkout_count,
            'checkin_count': self.stats.checkin_count,
            'invalidated': self.stats.invalidated_count,
            'slow_query_count': self.stats.slow_query_count,
            'n_plus_one_detected': self.stats.n_plus_one_detected,
            'latency_ms': self.stats.get_latency_ms(),
            'quotas': {},
        }

        with self._quotas_lock:
            for name, quota in self._quotas.items():
                stats['quotas'][name] = {
                    'current': quota.current,
                    'max': quota.max_connections,
                    'available': quota.available,
                }

        if self._slave_engine is not None:
            stats['slave'] = {
                'pool_size': self._slave_engine.pool.size(),
                'active': self._slave_engine.pool.checkedout(),
                'idle': self._slave_engine.pool.checkedin(),
                'overflow': self._slave_engine.pool.overflow(),
            }

        return stats

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        if self.engine is None:
            return {}
        return {
            'db_pool_checkout_count': self.stats.checkout_count,
            'db_pool_overflow': self.engine.pool.overflow(),
            'db_pool_latency_ms': self.stats.get_latency_ms() or 0.0,
            'db_pool_active': self.engine.pool.checkedout(),
            'db_pool_idle': self.engine.pool.checkedin(),
            'db_pool_size': self.engine.pool.size(),
            'db_pool_slow_query_count': self.stats.slow_query_count,
            'db_pool_n_plus_one_detected': self.stats.n_plus_one_detected,
            'db_pool_invalidated': self.stats.invalidated_count,
        }

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()
        if self._slave_engine:
            self._slave_engine.dispose()
        logger.info("数据库连接池已关闭")


db_pool = DatabasePool()
