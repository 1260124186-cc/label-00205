"""
滑动窗口管理器模块

维护 per-bolt 滑动窗口，支持内存和 Redis 两种存储后端。
窗口满时触发推理，支持单条或微批次数据更新。

主要组件:
- WindowData: 窗口数据结构
- SlidingWindowManager: 滑动窗口管理器基类
- MemoryWindowManager: 内存版滑动窗口管理器
- RedisWindowManager: Redis版滑动窗口管理器
"""

import time
import json
from abc import ABC, abstractmethod
from collections import deque
from threading import Lock
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
from loguru import logger

from app.utils.config import config


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
    """
    bolt_id: str
    values: List[float] = field(default_factory=list)
    timestamps: List[str] = field(default_factory=list)
    window_size: int = 100
    last_updated: float = 0.0
    last_prediction_status: int = 0
    prediction_count: int = 0

    def is_full(self) -> bool:
        """判断窗口是否已满"""
        return len(self.values) >= self.window_size

    def add_point(self, value: float, timestamp: str) -> bool:
        """
        添加单个数据点

        Args:
            value: 预紧力值
            timestamp: 时间戳

        Returns:
            bool: 窗口是否已满
        """
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
        """
        批量添加数据点

        Args:
            values: 预紧力值列表
            timestamps: 时间戳列表

        Returns:
            bool: 窗口是否已满
        """
        self.values.extend(values)
        self.timestamps.extend(timestamps)
        self.last_updated = time.time()

        if len(self.values) > self.window_size:
            excess = len(self.values) - self.window_size
            self.values = self.values[excess:]
            self.timestamps = self.timestamps[excess:]

        return self.is_full()

    def get_window(self) -> Tuple[List[float], List[str]]:
        """获取完整窗口数据"""
        return self.values.copy(), self.timestamps.copy()

    def clear(self) -> None:
        """清空窗口"""
        self.values.clear()
        self.timestamps.clear()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'bolt_id': self.bolt_id,
            'values': self.values,
            'timestamps': self.timestamps,
            'window_size': self.window_size,
            'last_updated': self.last_updated,
            'last_prediction_status': self.last_prediction_status,
            'prediction_count': self.prediction_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowData':
        """从字典创建"""
        return cls(
            bolt_id=data['bolt_id'],
            values=data.get('values', []),
            timestamps=data.get('timestamps', []),
            window_size=data.get('window_size', 100),
            last_updated=data.get('last_updated', 0.0),
            last_prediction_status=data.get('last_prediction_status', 0),
            prediction_count=data.get('prediction_count', 0),
        )


class SlidingWindowManager(ABC):
    """
    滑动窗口管理器基类

    维护 per-bolt 滑动窗口，窗口满时触发回调。
    """

    def __init__(self, window_size: int = 100, ttl_seconds: int = 3600):
        """
        初始化滑动窗口管理器

        Args:
            window_size: 窗口大小（数据点数）
            ttl_seconds: 窗口过期时间（秒）
        """
        self.window_size = window_size
        self.ttl_seconds = ttl_seconds
        self._callbacks: List[callable] = []
        logger.info(
            f"滑动窗口管理器初始化完成: size={window_size}, ttl={ttl_seconds}s"
        )

    def register_callback(self, callback: callable) -> None:
        """
        注册窗口满回调

        Args:
            callback: 回调函数，接收 bolt_id 和 window_data 参数
        """
        self._callbacks.append(callback)
        logger.debug(f"已注册窗口满回调，当前回调数: {len(self._callbacks)}")

    def _trigger_callbacks(self, bolt_id: str, window_data: WindowData) -> None:
        """
        触发所有回调

        Args:
            bolt_id: 螺栓ID
            window_data: 窗口数据
        """
        for callback in self._callbacks:
            try:
                callback(bolt_id, window_data)
            except Exception as e:
                logger.error(f"窗口满回调执行失败 bolt={bolt_id}: {e}")

    @abstractmethod
    def get_window(self, bolt_id: str) -> Optional[WindowData]:
        """
        获取指定螺栓的窗口数据

        Args:
            bolt_id: 螺栓ID

        Returns:
            WindowData 或 None
        """
        pass

    @abstractmethod
    def add_point(self, bolt_id: str, value: float, timestamp: str) -> bool:
        """
        添加单个数据点

        Args:
            bolt_id: 螺栓ID
            value: 预紧力值
            timestamp: 时间戳

        Returns:
            bool: 窗口是否已满
        """
        pass

    @abstractmethod
    def add_batch(
        self, bolt_id: str, values: List[float], timestamps: List[str]
    ) -> bool:
        """
        批量添加数据点

        Args:
            bolt_id: 螺栓ID
            values: 预紧力值列表
            timestamps: 时间戳列表

        Returns:
            bool: 窗口是否已满
        """
        pass

    @abstractmethod
    def clear_window(self, bolt_id: str) -> None:
        """
        清空指定螺栓的窗口

        Args:
            bolt_id: 螺栓ID
        """
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """清空所有窗口"""
        pass

    @abstractmethod
    def list_bolts(self) -> List[str]:
        """
        列出所有有数据的螺栓ID

        Returns:
            螺栓ID列表
        """
        pass

    @abstractmethod
    def update_prediction_status(self, bolt_id: str, status_code: int) -> None:
        """
        更新预测状态

        Args:
            bolt_id: 螺栓ID
            status_code: 状态码
        """
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        清理过期窗口

        Returns:
            清理的窗口数量
        """
        pass


class MemoryWindowManager(SlidingWindowManager):
    """
    内存版滑动窗口管理器

    使用内存字典存储窗口数据，适合单节点部署。
    """

    def __init__(self, window_size: int = 100, ttl_seconds: int = 3600):
        """
        初始化内存滑动窗口管理器

        Args:
            window_size: 窗口大小
            ttl_seconds: 窗口过期时间
        """
        super().__init__(window_size, ttl_seconds)
        self._windows: Dict[str, WindowData] = {}
        self._lock = Lock()

    def get_window(self, bolt_id: str) -> Optional[WindowData]:
        """获取指定螺栓的窗口数据"""
        with self._lock:
            window = self._windows.get(bolt_id)
            if window:
                return WindowData(
                    bolt_id=window.bolt_id,
                    values=list(window.values),
                    timestamps=list(window.timestamps),
                    window_size=window.window_size,
                    last_updated=window.last_updated,
                    last_prediction_status=window.last_prediction_status,
                    prediction_count=window.prediction_count,
                )
            return None

    def _get_or_create_window(self, bolt_id: str) -> WindowData:
        """
        获取或创建窗口（内部方法，需要加锁）

        Args:
            bolt_id: 螺栓ID

        Returns:
            WindowData
        """
        if bolt_id not in self._windows:
            self._windows[bolt_id] = WindowData(
                bolt_id=bolt_id,
                window_size=self.window_size,
            )
        return self._windows[bolt_id]

    def add_point(self, bolt_id: str, value: float, timestamp: str) -> bool:
        """添加单个数据点"""
        with self._lock:
            window = self._get_or_create_window(bolt_id)
            is_full = window.add_point(value, timestamp)

        if is_full:
            window_copy = self.get_window(bolt_id)
            if window_copy:
                self._trigger_callbacks(bolt_id, window_copy)

        return is_full

    def add_batch(
        self, bolt_id: str, values: List[float], timestamps: List[str]
    ) -> bool:
        """批量添加数据点"""
        with self._lock:
            window = self._get_or_create_window(bolt_id)
            is_full = window.add_batch(values, timestamps)

        if is_full:
            window_copy = self.get_window(bolt_id)
            if window_copy:
                self._trigger_callbacks(bolt_id, window_copy)

        return is_full

    def clear_window(self, bolt_id: str) -> None:
        """清空指定螺栓的窗口"""
        with self._lock:
            if bolt_id in self._windows:
                self._windows[bolt_id].clear()

    def clear_all(self) -> None:
        """清空所有窗口"""
        with self._lock:
            self._windows.clear()

    def list_bolts(self) -> List[str]:
        """列出所有有数据的螺栓ID"""
        with self._lock:
            return list(self._windows.keys())

    def update_prediction_status(self, bolt_id: str, status_code: int) -> None:
        """更新预测状态"""
        with self._lock:
            window = self._windows.get(bolt_id)
            if window:
                window.last_prediction_status = status_code
                window.prediction_count += 1

    def cleanup_expired(self) -> int:
        """清理过期窗口"""
        now = time.time()
        count = 0
        with self._lock:
            expired_bolts = [
                bolt_id
                for bolt_id, window in self._windows.items()
                if now - window.last_updated > self.ttl_seconds
            ]
            for bolt_id in expired_bolts:
                del self._windows[bolt_id]
                count += 1
        if count > 0:
            logger.info(f"清理过期窗口: {count} 个")
        return count


class RedisWindowManager(SlidingWindowManager):
    """
    Redis版滑动窗口管理器

    使用 Redis 存储窗口数据，适合多节点部署和数据持久化。
    """

    def __init__(
        self,
        window_size: int = 100,
        ttl_seconds: int = 3600,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "stream_window",
    ):
        """
        初始化Redis滑动窗口管理器

        Args:
            window_size: 窗口大小
            ttl_seconds: 窗口过期时间
            redis_url: Redis连接URL
            key_prefix: Redis键前缀
        """
        super().__init__(window_size, ttl_seconds)
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis_client = None
        self._init_redis()

    def _init_redis(self) -> None:
        """初始化Redis连接"""
        try:
            import redis
            self._redis_client = redis.Redis.from_url(self.redis_url)
            self._redis_client.ping()
            logger.info(f"Redis窗口管理器连接成功: {self.redis_url}")
        except ImportError:
            logger.warning("redis库未安装，Redis窗口管理器不可用")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self._redis_client = None

    def _make_key(self, bolt_id: str) -> str:
        """构造Redis键"""
        return f"{self.key_prefix}:{bolt_id}"

    def _is_available(self) -> bool:
        """检查Redis是否可用"""
        return self._redis_client is not None

    def get_window(self, bolt_id: str) -> Optional[WindowData]:
        """获取指定螺栓的窗口数据"""
        if not self._is_available():
            return None

        try:
            key = self._make_key(bolt_id)
            data = self._redis_client.get(key)
            if data:
                return WindowData.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"获取Redis窗口失败 bolt={bolt_id}: {e}")
            return None

    def add_point(self, bolt_id: str, value: float, timestamp: str) -> bool:
        """添加单个数据点"""
        if not self._is_available():
            return False

        try:
            key = self._make_key(bolt_id)
            pipe = self._redis_client.pipeline()

            data = self._redis_client.get(key)
            if data:
                window = WindowData.from_dict(json.loads(data))
            else:
                window = WindowData(
                    bolt_id=bolt_id, window_size=self.window_size
                )

            is_full = window.add_point(value, timestamp)

            pipe.setex(key, self.ttl_seconds, json.dumps(window.to_dict()))
            pipe.execute()

            if is_full:
                self._trigger_callbacks(bolt_id, window)

            return is_full
        except Exception as e:
            logger.error(f"添加数据点到Redis失败 bolt={bolt_id}: {e}")
            return False

    def add_batch(
        self, bolt_id: str, values: List[float], timestamps: List[str]
    ) -> bool:
        """批量添加数据点"""
        if not self._is_available():
            return False

        try:
            key = self._make_key(bolt_id)

            data = self._redis_client.get(key)
            if data:
                window = WindowData.from_dict(json.loads(data))
            else:
                window = WindowData(
                    bolt_id=bolt_id, window_size=self.window_size
                )

            is_full = window.add_batch(values, timestamps)

            self._redis_client.setex(
                key, self.ttl_seconds, json.dumps(window.to_dict())
            )

            if is_full:
                self._trigger_callbacks(bolt_id, window)

            return is_full
        except Exception as e:
            logger.error(f"批量添加数据到Redis失败 bolt={bolt_id}: {e}")
            return False

    def clear_window(self, bolt_id: str) -> None:
        """清空指定螺栓的窗口"""
        if not self._is_available():
            return

        try:
            key = self._make_key(bolt_id)
            self._redis_client.delete(key)
        except Exception as e:
            logger.error(f"清空Redis窗口失败 bolt={bolt_id}: {e}")

    def clear_all(self) -> None:
        """清空所有窗口"""
        if not self._is_available():
            return

        try:
            pattern = f"{self.key_prefix}:*"
            keys = list(self._redis_client.scan_iter(match=pattern))
            if keys:
                self._redis_client.delete(*keys)
            logger.info(f"清空所有Redis窗口: {len(keys)} 个")
        except Exception as e:
            logger.error(f"清空所有Redis窗口失败: {e}")

    def list_bolts(self) -> List[str]:
        """列出所有有数据的螺栓ID"""
        if not self._is_available():
            return []

        try:
            pattern = f"{self.key_prefix}:*"
            keys = list(self._redis_client.scan_iter(match=pattern))
            prefix_len = len(self.key_prefix) + 1
            return [key.decode('utf-8')[prefix_len:] for key in keys]
        except Exception as e:
            logger.error(f"列出Redis窗口失败: {e}")
            return []

    def update_prediction_status(self, bolt_id: str, status_code: int) -> None:
        """更新预测状态"""
        if not self._is_available():
            return

        try:
            key = self._make_key(bolt_id)
            data = self._redis_client.get(key)
            if data:
                window = WindowData.from_dict(json.loads(data))
                window.last_prediction_status = status_code
                window.prediction_count += 1
                self._redis_client.setex(
                    key, self.ttl_seconds, json.dumps(window.to_dict())
                )
        except Exception as e:
            logger.error(f"更新预测状态失败 bolt={bolt_id}: {e}")

    def cleanup_expired(self) -> int:
        """
        清理过期窗口

        Redis 自动处理过期，这里返回0
        """
        return 0


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
            key_prefix=kwargs.get("key_prefix", "stream_window"),
        )
    else:
        return MemoryWindowManager(
            window_size=window_size, ttl_seconds=ttl_seconds
        )
