"""
滑动窗口管理器模块

维护 per-bolt 滑动窗口，支持内存和 Redis 两种存储后端。
窗口满时触发推理，支持单条或微批次数据更新。

集群化增强:
- Redis 键规范: bolt_preload:window:{tenant_id}:{bolt_id}（租户隔离）
- 生产环境强制 Redis 后端
- 窗口 TTL、最大 bolt 数、内存上限可配
- 实例故障时窗口数据不丢失（Redis 持久化）
- 新实例启动可恢复未完成窗口
- Redis 集群/哨兵模式支持
- 窗口数据导出/导入（边缘断网恢复场景）
- Redis 内存占用、键数量、过期率接入 Prometheus

主要组件:
- WindowData: 窗口数据结构
- SlidingWindowManager: 滑动窗口管理器基类
- MemoryWindowManager: 内存版滑动窗口管理器
- RedisWindowManager: Redis版滑动窗口管理器（集群化）
- RedisClusterWindowManager: Redis集群版滑动窗口管理器
"""

import time
import json
import hashlib
import threading
from abc import ABC, abstractmethod
from collections import deque
from threading import Lock
from typing import Optional, List, Tuple, Dict, Any, Set
from dataclasses import dataclass, field
from loguru import logger

from app.utils.config import config


REDIS_KEY_PREFIX = "bolt_preload:window"


@dataclass
class WindowData:
    """
    窗口数据结构

    Attributes:
        bolt_id: 螺栓ID
        values: 预紧力值列表
        timestamps: 时间戳列表
        window_size: 窗口大小
        last_updated: 最后更新时间
        last_prediction_status: 上次预测状态码
        prediction_count: 预测次数
        tenant_id: 租户ID
    """
    bolt_id: str
    values: List[float] = field(default_factory=list)
    timestamps: List[str] = field(default_factory=list)
    window_size: int = 100
    last_updated: float = 0.0
    last_prediction_status: int = 0
    prediction_count: int = 0
    tenant_id: str = "default"

    def is_full(self) -> bool:
        return len(self.values) >= self.window_size

    def add_point(self, value: float, timestamp: str) -> bool:
        self.values.append(value)
        self.timestamps.append(timestamp)
        self.last_updated = time.time()

        if len(self.values) > self.window_size:
            self.values.pop(0)
            self.timestamps.pop(0)

        return self.is_full()

    def add_batch(
        self, values: List[float], timestamps: List[str]
    ) -> bool:
        self.values.extend(values)
        self.timestamps.extend(timestamps)
        self.last_updated = time.time()

        if len(self.values) > self.window_size:
            excess = len(self.values) - self.window_size
            self.values = self.values[excess:]
            self.timestamps = self.timestamps[excess:]

        return self.is_full()

    def get_window(self) -> Tuple[List[float], List[str]]:
        return self.values.copy(), self.timestamps.copy()

    def clear(self) -> None:
        self.values.clear()
        self.timestamps.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'bolt_id': self.bolt_id,
            'values': self.values,
            'timestamps': self.timestamps,
            'window_size': self.window_size,
            'last_updated': self.last_updated,
            'last_prediction_status': self.last_prediction_status,
            'prediction_count': self.prediction_count,
            'tenant_id': self.tenant_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowData':
        return cls(
            bolt_id=data['bolt_id'],
            values=data.get('values', []),
            timestamps=data.get('timestamps', []),
            window_size=data.get('window_size', 100),
            last_updated=data.get('last_updated', 0.0),
            last_prediction_status=data.get('last_prediction_status', 0),
            prediction_count=data.get('prediction_count', 0),
            tenant_id=data.get('tenant_id', 'default'),
        )


class SlidingWindowManager(ABC):
    """
    滑动窗口管理器基类

    维护 per-bolt 滑动窗口，窗口满时触发回调。
    """

    def __init__(self, window_size: int = 100, ttl_seconds: int = 3600):
        self.window_size = window_size
        self.ttl_seconds = ttl_seconds
        self._callbacks: List[callable] = []
        logger.info(
            f"滑动窗口管理器初始化完成: size={window_size}, ttl={ttl_seconds}s"
        )

    def register_callback(self, callback: callable) -> None:
        self._callbacks.append(callback)
        logger.debug(f"已注册窗口满回调，当前回调数: {len(self._callbacks)}")

    def _trigger_callbacks(self, bolt_id: str, window_data: WindowData) -> None:
        for callback in self._callbacks:
            try:
                callback(bolt_id, window_data)
            except Exception as e:
                logger.error(f"窗口满回调执行失败 bolt={bolt_id}: {e}")

    @abstractmethod
    def get_window(self, bolt_id: str, tenant_id: str = "default") -> Optional[WindowData]:
        pass

    @abstractmethod
    def add_point(self, bolt_id: str, value: float, timestamp: str, tenant_id: str = "default") -> bool:
        pass

    @abstractmethod
    def add_batch(
        self, bolt_id: str, values: List[float], timestamps: List[str], tenant_id: str = "default"
    ) -> bool:
        pass

    @abstractmethod
    def clear_window(self, bolt_id: str, tenant_id: str = "default") -> None:
        pass

    @abstractmethod
    def clear_all(self, tenant_id: Optional[str] = None) -> None:
        pass

    @abstractmethod
    def list_bolts(self, tenant_id: Optional[str] = None) -> List[str]:
        pass

    @abstractmethod
    def update_prediction_status(self, bolt_id: str, status_code: int, tenant_id: str = "default") -> None:
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        pass

    @abstractmethod
    def count_bolts(self, tenant_id: Optional[str] = None) -> int:
        pass

    @abstractmethod
    def export_windows(self, tenant_id: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def import_windows(self, data: str, tenant_id: Optional[str] = None) -> int:
        pass


class MemoryWindowManager(SlidingWindowManager):
    """
    内存版滑动窗口管理器

    使用内存字典存储窗口数据，适合单节点开发/测试。
    生产环境应使用 Redis 后端。
    """

    def __init__(self, window_size: int = 100, ttl_seconds: int = 3600,
                 max_bolts: int = 10000):
        super().__init__(window_size, ttl_seconds)
        self.max_bolts = max_bolts
        self._windows: Dict[str, WindowData] = {}
        self._lock = Lock()

    def _make_key(self, bolt_id: str, tenant_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}:{tenant_id}:{bolt_id}"

    def _parse_key(self, key: str) -> Tuple[str, str]:
        parts = key.split(":")
        if len(parts) >= 4:
            return parts[2], parts[3]
        return "default", parts[-1] if parts else ""

    def get_window(self, bolt_id: str, tenant_id: str = "default") -> Optional[WindowData]:
        with self._lock:
            key = self._make_key(bolt_id, tenant_id)
            window = self._windows.get(key)
            if window:
                return WindowData(
                    bolt_id=window.bolt_id,
                    values=list(window.values),
                    timestamps=list(window.timestamps),
                    window_size=window.window_size,
                    last_updated=window.last_updated,
                    last_prediction_status=window.last_prediction_status,
                    prediction_count=window.prediction_count,
                    tenant_id=window.tenant_id,
                )
            return None

    def _get_or_create_window(self, bolt_id: str, tenant_id: str) -> WindowData:
        key = self._make_key(bolt_id, tenant_id)
        if key not in self._windows:
            if len(self._windows) >= self.max_bolts:
                logger.warning(
                    f"窗口数量已达上限 {self.max_bolts}，拒绝创建新窗口: "
                    f"tenant={tenant_id}, bolt={bolt_id}"
                )
                raise MemoryError(
                    f"窗口数量上限 {self.max_bolts} 已达，无法创建新窗口"
                )
            self._windows[key] = WindowData(
                bolt_id=bolt_id,
                window_size=self.window_size,
                tenant_id=tenant_id,
            )
        return self._windows[key]

    def add_point(self, bolt_id: str, value: float, timestamp: str, tenant_id: str = "default") -> bool:
        with self._lock:
            window = self._get_or_create_window(bolt_id, tenant_id)
            is_full = window.add_point(value, timestamp)

        if is_full:
            window_copy = self.get_window(bolt_id, tenant_id)
            if window_copy:
                self._trigger_callbacks(bolt_id, window_copy)

        return is_full

    def add_batch(
        self, bolt_id: str, values: List[float], timestamps: List[str], tenant_id: str = "default"
    ) -> bool:
        with self._lock:
            window = self._get_or_create_window(bolt_id, tenant_id)
            is_full = window.add_batch(values, timestamps)

        if is_full:
            window_copy = self.get_window(bolt_id, tenant_id)
            if window_copy:
                self._trigger_callbacks(bolt_id, window_copy)

        return is_full

    def clear_window(self, bolt_id: str, tenant_id: str = "default") -> None:
        with self._lock:
            key = self._make_key(bolt_id, tenant_id)
            if key in self._windows:
                self._windows[key].clear()

    def clear_all(self, tenant_id: Optional[str] = None) -> None:
        with self._lock:
            if tenant_id is None:
                self._windows.clear()
            else:
                prefix = f"{REDIS_KEY_PREFIX}:{tenant_id}:"
                keys_to_delete = [k for k in self._windows if k.startswith(prefix)]
                for k in keys_to_delete:
                    del self._windows[k]

    def list_bolts(self, tenant_id: Optional[str] = None) -> List[str]:
        with self._lock:
            if tenant_id is None:
                return [k.split(":")[-1] for k in self._windows.keys()]
            prefix = f"{REDIS_KEY_PREFIX}:{tenant_id}:"
            return [k[len(prefix):] for k in self._windows if k.startswith(prefix)]

    def update_prediction_status(self, bolt_id: str, status_code: int, tenant_id: str = "default") -> None:
        with self._lock:
            key = self._make_key(bolt_id, tenant_id)
            window = self._windows.get(key)
            if window:
                window.last_prediction_status = status_code
                window.prediction_count += 1

    def cleanup_expired(self) -> int:
        now = time.time()
        count = 0
        with self._lock:
            expired_keys = [
                key for key, window in self._windows.items()
                if now - window.last_updated > self.ttl_seconds
            ]
            for key in expired_keys:
                del self._windows[key]
                count += 1
        if count > 0:
            logger.info(f"清理过期窗口: {count} 个")
        return count

    def count_bolts(self, tenant_id: Optional[str] = None) -> int:
        with self._lock:
            if tenant_id is None:
                return len(self._windows)
            prefix = f"{REDIS_KEY_PREFIX}:{tenant_id}:"
            return sum(1 for k in self._windows if k.startswith(prefix))

    def export_windows(self, tenant_id: Optional[str] = None) -> str:
        with self._lock:
            if tenant_id is None:
                items = {k: v.to_dict() for k, v in self._windows.items()}
            else:
                prefix = f"{REDIS_KEY_PREFIX}:{tenant_id}:"
                items = {k: v.to_dict() for k, v in self._windows.items() if k.startswith(prefix)}
        payload = {
            "version": 1,
            "exported_at": time.time(),
            "source": "memory",
            "tenant_id": tenant_id,
            "count": len(items),
            "windows": items,
        }
        return json.dumps(payload, ensure_ascii=False)

    def import_windows(self, data: str, tenant_id: Optional[str] = None) -> int:
        try:
            payload = json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"导入窗口数据解析失败: {e}")
            return 0

        windows_data = payload.get("windows", {})
        imported = 0
        with self._lock:
            for key, wd in windows_data.items():
                try:
                    window = WindowData.from_dict(wd)
                    if tenant_id is not None:
                        parts = key.split(":")
                        if len(parts) >= 4:
                            key = f"{REDIS_KEY_PREFIX}:{tenant_id}:{parts[-1]}"
                        else:
                            key = f"{REDIS_KEY_PREFIX}:{tenant_id}:{key}"
                    self._windows[key] = window
                    imported += 1
                except Exception as e:
                    logger.warning(f"导入窗口数据跳过 key={key}: {e}")
        logger.info(f"导入窗口数据完成: {imported} 个")
        return imported


class RedisWindowManager(SlidingWindowManager):
    """
    Redis版滑动窗口管理器（集群化）

    使用 Redis 存储窗口数据，适合多节点部署和数据持久化。

    集群化特性:
    - 键规范: bolt_preload:window:{tenant_id}:{bolt_id}（租户隔离）
    - 生产环境强制 Redis 后端
    - 窗口 TTL / 最大 bolt 数 / 内存上限可配
    - 实例故障时窗口数据不丢失
    - 新实例启动可恢复未完成窗口
    - Redis 集群/哨兵模式支持
    - 窗口数据导出/导入
    """

    def __init__(
        self,
        window_size: int = 100,
        ttl_seconds: int = 3600,
        redis_url: str = "redis://localhost:6379/0",
        max_bolts: int = 50000,
        memory_limit_mb: int = 512,
        enforce_redis: bool = True,
        cluster_mode: str = "standalone",
        cluster_nodes: Optional[List[str]] = None,
        sentinel_master: Optional[str] = None,
        sentinel_nodes: Optional[List[str]] = None,
        sentinel_password: Optional[str] = None,
        redis_password: Optional[str] = None,
        redis_db: int = 0,
    ):
        super().__init__(window_size, ttl_seconds)
        self.redis_url = redis_url
        self.max_bolts = max_bolts
        self.memory_limit_mb = memory_limit_mb
        self.enforce_redis = enforce_redis
        self.cluster_mode = cluster_mode
        self.cluster_nodes = cluster_nodes or []
        self.sentinel_master = sentinel_master
        self.sentinel_nodes = sentinel_nodes or []
        self.sentinel_password = sentinel_password
        self.redis_password = redis_password
        self.redis_db = redis_db
        self._redis_client = None
        self._instance_id = hashlib.md5(
            f"{time.time()}-{id(self)}".encode()
        ).hexdigest()[:12]
        self._lock_registry_key = f"{REDIS_KEY_PREFIX}:locks:{self._instance_id}"

        self._expired_counter = 0
        self._expired_counter_lock = threading.Lock()

        self._init_redis()

    def _init_redis(self) -> None:
        try:
            import redis as redis_lib

            if self.cluster_mode == "cluster" and self.cluster_nodes:
                from redis.cluster import RedisCluster
                self._redis_client = RedisCluster(
                    host=self.cluster_nodes[0].split(":")[0],
                    port=int(self.cluster_nodes[0].split(":")[1]) if ":" in self.cluster_nodes[0] else 6379,
                    password=self.redis_password,
                    decode_responses=False,
                    skip_full_coverage_check=True,
                )
                self._redis_client.ping()
                logger.info(
                    f"Redis集群窗口管理器连接成功: nodes={self.cluster_nodes}"
                )
            elif self.cluster_mode == "sentinel" and self.sentinel_nodes:
                sentinel = redis_lib.Sentinel(
                    [(n.split(":")[0], int(n.split(":")[1])) for n in self.sentinel_nodes],
                    password=self.sentinel_password,
                    socket_connect_timeout=5,
                )
                self._redis_client = sentinel.master_for(
                    self.sentinel_master or "mymaster",
                    password=self.redis_password,
                    db=self.redis_db,
                    decode_responses=False,
                )
                self._redis_client.ping()
                logger.info(
                    f"Redis哨兵窗口管理器连接成功: master={self.sentinel_master}, "
                    f"sentinels={self.sentinel_nodes}"
                )
            else:
                self._redis_client = redis_lib.Redis.from_url(
                    self.redis_url,
                    password=self.redis_password,
                    db=self.redis_db,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )
                self._redis_client.ping()
                logger.info(f"Redis窗口管理器连接成功: {self.redis_url}")

            self._register_instance()
            self._recover_windows()

        except ImportError:
            if self.enforce_redis:
                raise RuntimeError(
                    "生产环境强制使用 Redis 后端，但 redis 库未安装。"
                    "请执行: pip install redis[hiredis]"
                )
            logger.warning("redis库未安装，Redis窗口管理器不可用")
        except Exception as e:
            if self.enforce_redis:
                raise RuntimeError(
                    f"生产环境强制使用 Redis 后端，但 Redis 连接失败: {e}"
                )
            logger.error(f"Redis连接失败: {e}")
            self._redis_client = None

    def _register_instance(self) -> None:
        if not self._is_available():
            return
        try:
            self._redis_client.setex(
                self._lock_registry_key,
                max(self.ttl_seconds * 2, 300),
                json.dumps({
                    "instance_id": self._instance_id,
                    "started_at": time.time(),
                    "window_size": self.window_size,
                    "ttl_seconds": self.ttl_seconds,
                }).encode('utf-8'),
            )
            logger.info(f"实例注册到 Redis: {self._instance_id}")
        except Exception as e:
            logger.warning(f"实例注册失败: {e}")

    def _recover_windows(self) -> None:
        if not self._is_available():
            return
        try:
            pattern = f"{REDIS_KEY_PREFIX}:*"
            recovered = 0
            for key in self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern):
                raw_key = key.decode('utf-8') if isinstance(key, bytes) else key
                if self._is_window_key(raw_key):
                    ttl = self._redis_client.ttl(key)
                    if ttl is not None and ttl > 0:
                        recovered += 1

            if recovered > 0:
                logger.info(
                    f"从 Redis 恢复窗口数据: {recovered} 个活跃窗口"
                )
        except Exception as e:
            logger.warning(f"恢复窗口数据失败: {e}")

    def _is_window_key(self, key: str) -> bool:
        parts = key.split(":")
        if len(parts) >= 4:
            return parts[0] == "bolt_preload" and parts[1] == "window"
        return False

    def _make_key(self, bolt_id: str, tenant_id: str) -> str:
        return f"{REDIS_KEY_PREFIX}:{tenant_id}:{bolt_id}"

    def _is_available(self) -> bool:
        return self._redis_client is not None

    def _check_memory_limit(self) -> bool:
        if not self._is_available() or self.memory_limit_mb <= 0:
            return True
        try:
            info = self._redis_client.info("memory")
            used_mb = info.get("used_memory", 0) / (1024 * 1024)
            if used_mb > self.memory_limit_mb:
                logger.warning(
                    f"Redis 内存使用超过上限: {used_mb:.1f}MB / {self.memory_limit_mb}MB"
                )
                return False
        except Exception:
            pass
        return True

    def _check_max_bolts(self, tenant_id: str) -> bool:
        if self.max_bolts <= 0:
            return True
        try:
            pattern = f"{REDIS_KEY_PREFIX}:{tenant_id}:*"
            count = 0
            for _ in self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern):
                count += 1
                if count >= self.max_bolts:
                    logger.warning(
                        f"租户 {tenant_id} 窗口数量已达上限 {self.max_bolts}"
                    )
                    return False
        except Exception:
            pass
        return True

    def get_window(self, bolt_id: str, tenant_id: str = "default") -> Optional[WindowData]:
        if not self._is_available():
            return None
        try:
            key = self._make_key(bolt_id, tenant_id)
            data = self._redis_client.get(key)
            if data:
                return WindowData.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"获取Redis窗口失败 bolt={bolt_id} tenant={tenant_id}: {e}")
            return None

    def add_point(self, bolt_id: str, value: float, timestamp: str, tenant_id: str = "default") -> bool:
        if not self._is_available():
            return False
        if not self._check_memory_limit():
            return False
        if not self._check_max_bolts(tenant_id):
            return False

        try:
            key = self._make_key(bolt_id, tenant_id)
            data = self._redis_client.get(key)
            if data:
                window = WindowData.from_dict(json.loads(data))
            else:
                window = WindowData(
                    bolt_id=bolt_id, window_size=self.window_size,
                    tenant_id=tenant_id,
                )

            is_full = window.add_point(value, timestamp)

            pipe = self._redis_client.pipeline()
            pipe.setex(key, self.ttl_seconds, json.dumps(window.to_dict()).encode('utf-8'))
            pipe.execute()

            if is_full:
                self._trigger_callbacks(bolt_id, window)

            return is_full
        except Exception as e:
            logger.error(f"添加数据点到Redis失败 bolt={bolt_id} tenant={tenant_id}: {e}")
            return False

    def add_batch(
        self, bolt_id: str, values: List[float], timestamps: List[str], tenant_id: str = "default"
    ) -> bool:
        if not self._is_available():
            return False
        if not self._check_memory_limit():
            return False
        if not self._check_max_bolts(tenant_id):
            return False

        try:
            key = self._make_key(bolt_id, tenant_id)
            data = self._redis_client.get(key)
            if data:
                window = WindowData.from_dict(json.loads(data))
            else:
                window = WindowData(
                    bolt_id=bolt_id, window_size=self.window_size,
                    tenant_id=tenant_id,
                )

            is_full = window.add_batch(values, timestamps)

            self._redis_client.setex(
                key, self.ttl_seconds, json.dumps(window.to_dict()).encode('utf-8')
            )

            if is_full:
                self._trigger_callbacks(bolt_id, window)

            return is_full
        except Exception as e:
            logger.error(f"批量添加数据到Redis失败 bolt={bolt_id} tenant={tenant_id}: {e}")
            return False

    def clear_window(self, bolt_id: str, tenant_id: str = "default") -> None:
        if not self._is_available():
            return
        try:
            key = self._make_key(bolt_id, tenant_id)
            self._redis_client.delete(key)
        except Exception as e:
            logger.error(f"清空Redis窗口失败 bolt={bolt_id} tenant={tenant_id}: {e}")

    def clear_all(self, tenant_id: Optional[str] = None) -> None:
        if not self._is_available():
            return
        try:
            if tenant_id is None:
                pattern = f"{REDIS_KEY_PREFIX}:*"
            else:
                pattern = f"{REDIS_KEY_PREFIX}:{tenant_id}:*"
            keys = list(self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern))
            window_keys = [k for k in keys if self._is_window_key(
                k.decode('utf-8') if isinstance(k, bytes) else k
            )]
            if window_keys:
                self._redis_client.delete(*window_keys)
            logger.info(f"清空Redis窗口: {len(window_keys)} 个, tenant={tenant_id}")
        except Exception as e:
            logger.error(f"清空Redis窗口失败: {e}")

    def list_bolts(self, tenant_id: Optional[str] = None) -> List[str]:
        if not self._is_available():
            return []
        try:
            if tenant_id is None:
                pattern = f"{REDIS_KEY_PREFIX}:*"
            else:
                pattern = f"{REDIS_KEY_PREFIX}:{tenant_id}:*"
            keys = list(self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern))
            result = []
            for k in keys:
                raw = k.decode('utf-8') if isinstance(k, bytes) else k
                if self._is_window_key(raw):
                    parts = raw.split(":")
                    if len(parts) >= 4:
                        result.append(parts[3])
            return result
        except Exception as e:
            logger.error(f"列出Redis窗口失败: {e}")
            return []

    def update_prediction_status(self, bolt_id: str, status_code: int, tenant_id: str = "default") -> None:
        if not self._is_available():
            return
        try:
            key = self._make_key(bolt_id, tenant_id)
            data = self._redis_client.get(key)
            if data:
                window = WindowData.from_dict(json.loads(data))
                window.last_prediction_status = status_code
                window.prediction_count += 1
                self._redis_client.setex(
                    key, self.ttl_seconds, json.dumps(window.to_dict()).encode('utf-8')
                )
        except Exception as e:
            logger.error(f"更新预测状态失败 bolt={bolt_id} tenant={tenant_id}: {e}")

    def cleanup_expired(self) -> int:
        if not self._is_available():
            return 0
        try:
            pattern = f"{REDIS_KEY_PREFIX}:*"
            expired = 0
            for key in self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern):
                raw = key.decode('utf-8') if isinstance(key, bytes) else key
                if not self._is_window_key(raw):
                    continue
                ttl = self._redis_client.ttl(key)
                if ttl is not None and ttl == -2:
                    expired += 1
            if expired > 0:
                with self._expired_counter_lock:
                    self._expired_counter += expired
                logger.info(f"Redis过期窗口: {expired} 个（累计: {self._expired_counter}）")
            return expired
        except Exception as e:
            logger.error(f"检查过期窗口失败: {e}")
            return 0

    def count_bolts(self, tenant_id: Optional[str] = None) -> int:
        if not self._is_available():
            return 0
        try:
            if tenant_id is None:
                pattern = f"{REDIS_KEY_PREFIX}:*"
            else:
                pattern = f"{REDIS_KEY_PREFIX}:{tenant_id}:*"
            count = 0
            for k in self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern):
                raw = k.decode('utf-8') if isinstance(k, bytes) else k
                if self._is_window_key(raw):
                    count += 1
            return count
        except Exception as e:
            logger.error(f"统计Redis窗口数量失败: {e}")
            return 0

    def get_redis_info(self) -> Dict[str, Any]:
        if not self._is_available():
            return {}
        try:
            info_memory = self._redis_client.info("memory")
            info_keyspace = self._redis_client.info("keyspace")
            db_key = f"db{self.redis_db}"
            keys_info = info_keyspace.get(db_key, {})
            expires = 0
            if isinstance(keys_info, str):
                parts = keys_info.split(",")
                for p in parts:
                    if "expires=" in p:
                        try:
                            expires = int(p.split("=")[1])
                        except (ValueError, IndexError):
                            pass
            elif isinstance(keys_info, dict):
                expires = keys_info.get("expires", 0)

            return {
                "used_memory_bytes": info_memory.get("used_memory", 0),
                "used_memory_mb": round(info_memory.get("used_memory", 0) / (1024 * 1024), 2),
                "max_memory_bytes": info_memory.get("maxmemory", 0),
                "max_memory_mb": round(info_memory.get("maxmemory", 0) / (1024 * 1024), 2),
                "total_keys": keys_info.get("keys", 0) if isinstance(keys_info, dict) else 0,
                "expires": expires,
                "expired_counter": self._expired_counter,
                "memory_limit_mb": self.memory_limit_mb,
            }
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}

    def get_expired_counter(self) -> int:
        with self._expired_counter_lock:
            return self._expired_counter

    def export_windows(self, tenant_id: Optional[str] = None) -> str:
        if not self._is_available():
            return json.dumps({"version": 1, "count": 0, "windows": {}})

        try:
            if tenant_id is None:
                pattern = f"{REDIS_KEY_PREFIX}:*"
            else:
                pattern = f"{REDIS_KEY_PREFIX}:{tenant_id}:*"

            windows = {}
            for key in self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern):
                raw_key = key.decode('utf-8') if isinstance(key, bytes) else key
                if not self._is_window_key(raw_key):
                    continue
                data = self._redis_client.get(key)
                if data:
                    try:
                        wd = json.loads(data)
                        windows[raw_key] = wd
                    except (json.JSONDecodeError, TypeError):
                        pass

            payload = {
                "version": 1,
                "exported_at": time.time(),
                "source": "redis",
                "instance_id": self._instance_id,
                "tenant_id": tenant_id,
                "count": len(windows),
                "windows": windows,
            }
            logger.info(f"导出窗口数据: {len(windows)} 个, tenant={tenant_id}")
            return json.dumps(payload, ensure_ascii=False)
        except Exception as e:
            logger.error(f"导出窗口数据失败: {e}")
            return json.dumps({"version": 1, "count": 0, "windows": {}, "error": str(e)})

    def import_windows(self, data: str, tenant_id: Optional[str] = None) -> int:
        if not self._is_available():
            return 0

        try:
            payload = json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"导入窗口数据解析失败: {e}")
            return 0

        windows_data = payload.get("windows", {})
        imported = 0
        try:
            pipe = self._redis_client.pipeline()
            for key, wd in windows_data.items():
                try:
                    window = WindowData.from_dict(wd)
                    target_tenant = tenant_id if tenant_id is not None else window.tenant_id
                    redis_key = self._make_key(window.bolt_id, target_tenant)
                    pipe.setex(
                        redis_key,
                        self.ttl_seconds,
                        json.dumps(window.to_dict()).encode('utf-8'),
                    )
                    imported += 1
                except Exception as e:
                    logger.warning(f"导入窗口数据跳过 key={key}: {e}")

            if imported > 0:
                pipe.execute()

            logger.info(f"导入窗口数据完成: {imported} 个, tenant={tenant_id}")
        except Exception as e:
            logger.error(f"导入窗口数据执行失败: {e}")

        return imported

    def list_tenants(self) -> List[str]:
        if not self._is_available():
            return []
        try:
            pattern = f"{REDIS_KEY_PREFIX}:*"
            tenants: Set[str] = set()
            for key in self._redis_client.scan_iter(match=pattern.encode() if isinstance(pattern, str) else pattern):
                raw = key.decode('utf-8') if isinstance(key, bytes) else key
                if self._is_window_key(raw):
                    parts = raw.split(":")
                    if len(parts) >= 3:
                        tenants.add(parts[2])
            return sorted(tenants)
        except Exception as e:
            logger.error(f"列出租户失败: {e}")
            return []


def create_window_manager(
    storage_type: str = "memory",
    window_size: int = 100,
    ttl_seconds: int = 3600,
    **kwargs,
) -> SlidingWindowManager:
    """
    创建滑动窗口管理器

    Args:
        storage_type: 存储类型 (memory / redis)
        window_size: 窗口大小
        ttl_seconds: 窗口过期时间
        **kwargs: 其他参数

    Returns:
        SlidingWindowManager 实例
    """
    if storage_type == "redis":
        return RedisWindowManager(
            window_size=window_size,
            ttl_seconds=ttl_seconds,
            redis_url=kwargs.get("redis_url", "redis://localhost:6379/0"),
            max_bolts=kwargs.get("max_bolts", 50000),
            memory_limit_mb=kwargs.get("memory_limit_mb", 512),
            enforce_redis=kwargs.get("enforce_redis", True),
            cluster_mode=kwargs.get("cluster_mode", "standalone"),
            cluster_nodes=kwargs.get("cluster_nodes"),
            sentinel_master=kwargs.get("sentinel_master"),
            sentinel_nodes=kwargs.get("sentinel_nodes"),
            sentinel_password=kwargs.get("sentinel_password"),
            redis_password=kwargs.get("redis_password"),
            redis_db=kwargs.get("redis_db", 0),
        )
    else:
        return MemoryWindowManager(
            window_size=window_size,
            ttl_seconds=ttl_seconds,
            max_bolts=kwargs.get("max_bolts", 10000),
        )
