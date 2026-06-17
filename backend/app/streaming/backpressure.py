"""
背压与限流控制器模块

提供流式预测的并发控制和限流能力，支持：
- 单节点最大并发流数可配置
- 令牌桶限流算法
- 背压机制（过载时拒绝或排队）
- 实时监控指标

主要组件:
- RateLimiter: 基础限流器（令牌桶算法）
- BackpressureController: 背压控制器（并发流数管理）
"""

import time
import threading
from collections import deque
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from loguru import logger

from app.utils.config import config
from app.core.event_bus import event_bus, EventType, Event
from app.core.config_manager import config_manager


@dataclass
class RateLimitStats:
    """
    限流统计信息

    Attributes:
        total_requests: 总请求数
        accepted_requests: 接受的请求数
        rejected_requests: 拒绝的请求数
        current_tokens: 当前令牌数
        last_refill_time: 上次补充令牌时间
    """
    total_requests: int = 0
    accepted_requests: int = 0
    rejected_requests: int = 0
    current_tokens: float = 0.0
    last_refill_time: float = 0.0


class RateLimiter:
    """
    令牌桶限流器

    使用令牌桶算法实现速率限制，支持平滑突发流量。
    """

    def __init__(
        self,
        rate: float = 100.0,
        capacity: float = 200.0,
        time_window_seconds: int = 1,
    ):
        """
        初始化令牌桶限流器

        Args:
            rate: 令牌生成速率（每秒）
            capacity: 桶容量（最大令牌数）
            time_window_seconds: 时间窗口大小（秒）
        """
        self.rate = rate
        self.capacity = capacity
        self.time_window_seconds = time_window_seconds
        self._tokens = capacity
        self._last_refill_time = time.time()
        self._lock = threading.Lock()
        self._stats = RateLimitStats(current_tokens=capacity)
        logger.info(
            f"令牌桶限流器初始化: rate={rate}/s, capacity={capacity}"
        )

    def _refill_tokens(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_refill_time
        if elapsed > 0:
            new_tokens = elapsed * self.rate
            self._tokens = min(self.capacity, self._tokens + new_tokens)
            self._last_refill_time = now
            self._stats.current_tokens = self._tokens
            self._stats.last_refill_time = now

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        尝试获取令牌

        Args:
            tokens: 需要的令牌数

        Returns:
            bool: 是否获取成功
        """
        with self._lock:
            self._refill_tokens()
            self._stats.total_requests += 1

            if self._tokens >= tokens:
                self._tokens -= tokens
                self._stats.accepted_requests += 1
                self._stats.current_tokens = self._tokens
                return True
            else:
                self._stats.rejected_requests += 1
                return False

    def acquire(self, tokens: float = 1.0, timeout: float = None) -> bool:
        """
        获取令牌（阻塞等待）

        Args:
            tokens: 需要的令牌数
            timeout: 超时时间（秒），None 则无限等待

        Returns:
            bool: 是否获取成功
        """
        start_time = time.time()
        while True:
            if self.try_acquire(tokens):
                return True

            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # 计算需要等待的时间
            with self._lock:
                deficit = tokens - self._tokens
                wait_time = deficit / self.rate if self.rate > 0 else 0.1

            time.sleep(min(wait_time, 0.01))

    def get_stats(self) -> RateLimitStats:
        """获取统计信息"""
        with self._lock:
            self._refill_tokens()
            return RateLimitStats(
                total_requests=self._stats.total_requests,
                accepted_requests=self._stats.accepted_requests,
                rejected_requests=self._stats.rejected_requests,
                current_tokens=self._tokens,
                last_refill_time=self._last_refill_time,
            )

    def reset_stats(self) -> None:
        """重置统计"""
        with self._lock:
            self._stats = RateLimitStats(current_tokens=self._tokens)

    def set_rate(self, rate: float) -> None:
        """
        设置新的速率

        Args:
            rate: 新的令牌生成速率
        """
        with self._lock:
            self._refill_tokens()
            self.rate = rate
            logger.info(f"限流器速率更新: {rate}/s")

    def set_capacity(self, capacity: float) -> None:
        """
        设置新的桶容量

        Args:
            capacity: 新的桶容量
        """
        with self._lock:
            self.capacity = capacity
            self._tokens = min(self._tokens, capacity)
            self._stats.current_tokens = self._tokens
            logger.info(f"限流器容量更新: {capacity}")


@dataclass
class BackpressureStats:
    """
    背压统计信息

    Attributes:
        active_streams: 当前活跃流数
        max_streams: 最大允许流数
        total_streams: 历史总流数
        rejected_streams: 被拒绝的流数
        queue_size: 等待队列大小
        average_wait_time: 平均等待时间（秒）
    """
    active_streams: int = 0
    max_streams: int = 0
    total_streams: int = 0
    rejected_streams: int = 0
    queue_size: int = 0
    average_wait_time: float = 0.0


class BackpressureController:
    """
    背压控制器

    管理并发流数，支持：
    - 最大并发流数限制
    - 等待队列
    - 背压告警
    - 动态调整并发数
    """

    def __init__(
        self,
        max_concurrent_streams: int = 100,
        max_queue_size: int = 500,
        queue_timeout_seconds: float = 30.0,
    ):
        """
        初始化背压控制器

        Args:
            max_concurrent_streams: 最大并发流数
            max_queue_size: 最大等待队列大小
            queue_timeout_seconds: 队列等待超时时间（秒）
        """
        self.max_concurrent_streams = max_concurrent_streams
        self.max_queue_size = max_queue_size
        self.queue_timeout_seconds = queue_timeout_seconds
        self._active_streams = 0
        self._total_streams = 0
        self._rejected_streams = 0
        self._queue: deque = deque()
        self._wait_times: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._callbacks: Dict[str, Callable] = {}
        logger.info(
            f"背压控制器初始化: max_streams={max_concurrent_streams}, "
            f"max_queue={max_queue_size}"
        )

    def register_callback(self, event: str, callback: Callable) -> None:
        """
        注册事件回调

        Args:
            event: 事件类型 (reject / backpressure / recover)
            callback: 回调函数
        """
        self._callbacks[event] = callback
        logger.debug(f"已注册背压回调: {event}")

    def _trigger_callback(self, event: str, **kwargs) -> None:
        """触发回调"""
        if event in self._callbacks:
            try:
                self._callbacks[event](**kwargs)
            except Exception as e:
                logger.error(f"背压回调执行失败 event={event}: {e}")

    def try_acquire_slot(
        self, stream_id: str, wait: bool = False
    ) -> bool:
        """
        尝试获取流槽位

        Args:
            stream_id: 流ID
            wait: 是否等待

        Returns:
            bool: 是否获取成功
        """
        with self._condition:
            if self._active_streams < self.max_concurrent_streams:
                self._active_streams += 1
                self._total_streams += 1
                return True

            if not wait:
                self._rejected_streams += 1
                self._trigger_callback(
                    'reject', stream_id=stream_id, reason='no_slot'
                )
                return False

            if len(self._queue) >= self.max_queue_size:
                self._rejected_streams += 1
                self._trigger_callback(
                    'reject', stream_id=stream_id, reason='queue_full'
                )
                return False

            # 加入队列等待
            wait_start = time.time()
            event = threading.Event()
            self._queue.append((stream_id, event))

            # 检查是否触发背压告警
            if len(self._queue) > self.max_queue_size * 0.8:
                self._trigger_callback(
                    'backpressure',
                    queue_size=len(self._queue),
                    active_streams=self._active_streams,
                )

            self._condition.wait(timeout=self.queue_timeout_seconds)

            # 检查是否超时
            if time.time() - wait_start >= self.queue_timeout_seconds:
                # 从队列中移除
                try:
                    self._queue.remove((stream_id, event))
                except ValueError:
                    pass
                self._rejected_streams += 1
                self._trigger_callback(
                    'reject', stream_id=stream_id, reason='timeout'
                )
                return False

            wait_time = time.time() - wait_start
            self._wait_times.append(wait_time)
            return True

    def release_slot(self, stream_id: str) -> None:
        """
        释放流槽位

        Args:
            stream_id: 流ID
        """
        with self._condition:
            if self._active_streams > 0:
                self._active_streams -= 1

            # 检查是否有等待的流
            if self._queue:
                _, event = self._queue.popleft()
                self._active_streams += 1
                self._total_streams += 1
                event.set()

                # 检查是否恢复正常
                if len(self._queue) < self.max_queue_size * 0.3:
                    self._trigger_callback('recover', queue_size=len(self._queue))

            self._condition.notify_all()

    def get_stats(self) -> BackpressureStats:
        """获取统计信息"""
        with self._lock:
            avg_wait = (
                sum(self._wait_times) / len(self._wait_times)
                if self._wait_times
                else 0.0
            )
            return BackpressureStats(
                active_streams=self._active_streams,
                max_streams=self.max_concurrent_streams,
                total_streams=self._total_streams,
                rejected_streams=self._rejected_streams,
                queue_size=len(self._queue),
                average_wait_time=avg_wait,
            )

    def set_max_concurrent_streams(self, max_streams: int) -> None:
        """
        设置最大并发流数

        Args:
            max_streams: 新的最大并发流数
        """
        with self._condition:
            old_max = self.max_concurrent_streams
            self.max_concurrent_streams = max_streams

            # 如果增加了并发数，尝试从队列中取出等待的流
            if max_streams > old_max:
                additional_slots = max_streams - old_max
                while additional_slots > 0 and self._queue:
                    _, event = self._queue.popleft()
                    self._active_streams += 1
                    self._total_streams += 1
                    event.set()
                    additional_slots -= 1

            self._condition.notify_all()
            logger.info(f"最大并发流数更新: {old_max} -> {max_streams}")

    def set_max_queue_size(self, max_queue: int) -> None:
        """
        设置最大队列大小

        Args:
            max_queue: 新的最大队列大小
        """
        with self._lock:
            self.max_queue_size = max_queue
            logger.info(f"最大队列大小更新: {max_queue}")

    def is_under_backpressure(self) -> bool:
        """检查是否处于背压状态"""
        with self._lock:
            return len(self._queue) > 0 or self._active_streams >= self.max_concurrent_streams

    def get_utilization(self) -> float:
        """获取资源利用率（0-1）"""
        with self._lock:
            if self.max_concurrent_streams <= 0:
                return 1.0
            return self._active_streams / self.max_concurrent_streams

    def reset_stats(self) -> None:
        """重置统计"""
        with self._lock:
            self._total_streams = 0
            self._rejected_streams = 0
            self._wait_times.clear()


class StreamConcurrencyManager:
    """
    流并发管理器

    整合限流器和背压控制器，提供统一的并发管理接口。
    """

    def __init__(
        self,
        max_concurrent_streams: int = 100,
        rate_per_stream: float = 10.0,
        max_queue_size: int = 500,
        queue_timeout_seconds: float = 30.0,
    ):
        """
        初始化流并发管理器

        Args:
            max_concurrent_streams: 最大并发流数
            rate_per_stream: 每个流的速率限制（每秒）
            max_queue_size: 最大等待队列大小
            queue_timeout_seconds: 队列等待超时时间
        """
        self.backpressure = BackpressureController(
            max_concurrent_streams=max_concurrent_streams,
            max_queue_size=max_queue_size,
            queue_timeout_seconds=queue_timeout_seconds,
        )
        self.global_rate_limiter = RateLimiter(
            rate=max_concurrent_streams * rate_per_stream,
            capacity=max_concurrent_streams * rate_per_stream * 2,
        )
        self._stream_rate_limiters: Dict[str, RateLimiter] = {}
        self._rate_per_stream = rate_per_stream
        self._lock = threading.Lock()
        logger.info(
            f"流并发管理器初始化: max_streams={max_concurrent_streams}, "
            f"rate_per_stream={rate_per_stream}/s"
        )

    def _get_stream_limiter(self, stream_id: str) -> RateLimiter:
        """
        获取或创建流级别的限流器

        Args:
            stream_id: 流ID

        Returns:
            RateLimiter
        """
        with self._lock:
            if stream_id not in self._stream_rate_limiters:
                self._stream_rate_limiters[stream_id] = RateLimiter(
                    rate=self._rate_per_stream,
                    capacity=self._rate_per_stream * 2,
                )
            return self._stream_rate_limiters[stream_id]

    def can_accept_message(self, stream_id: str) -> bool:
        """
        检查是否可以接受消息

        Args:
            stream_id: 流ID

        Returns:
            bool
        """
        # 先检查全局限流
        if not self.global_rate_limiter.try_acquire(0):
            return False

        # 再检查流级别限流
        stream_limiter = self._get_stream_limiter(stream_id)
        if not stream_limiter.try_acquire(0):
            return False

        return True

    def try_accept_message(self, stream_id: str) -> bool:
        """
        尝试接受消息

        Args:
            stream_id: 流ID

        Returns:
            bool: 是否接受
        """
        # 先获取全局令牌
        if not self.global_rate_limiter.try_acquire(1):
            return False

        # 再获取流级别令牌
        stream_limiter = self._get_stream_limiter(stream_id)
        if not stream_limiter.try_acquire(1):
            # 归还全局令牌
            # 注意：令牌桶算法不支持归还，这里只能接受这个小误差
            return False

        return True

    def try_register_stream(self, stream_id: str) -> bool:
        """
        尝试注册流

        Args:
            stream_id: 流ID

        Returns:
            bool: 是否注册成功
        """
        return self.backpressure.try_acquire_slot(stream_id, wait=False)

    def unregister_stream(self, stream_id: str) -> None:
        """
        注销流

        Args:
            stream_id: 流ID
        """
        self.backpressure.release_slot(stream_id)
        with self._lock:
            if stream_id in self._stream_rate_limiters:
                del self._stream_rate_limiters[stream_id]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        backpressure_stats = self.backpressure.get_stats()
        global_stats = self.global_rate_limiter.get_stats()

        return {
            'backpressure': {
                'active_streams': backpressure_stats.active_streams,
                'max_streams': backpressure_stats.max_streams,
                'total_streams': backpressure_stats.total_streams,
                'rejected_streams': backpressure_stats.rejected_streams,
                'queue_size': backpressure_stats.queue_size,
                'average_wait_time': backpressure_stats.average_wait_time,
                'utilization': self.backpressure.get_utilization(),
                'is_under_backpressure': self.backpressure.is_under_backpressure(),
            },
            'global_rate': {
                'total_requests': global_stats.total_requests,
                'accepted_requests': global_stats.accepted_requests,
                'rejected_requests': global_stats.rejected_requests,
                'current_tokens': global_stats.current_tokens,
                'rate': self.global_rate_limiter.rate,
                'capacity': self.global_rate_limiter.capacity,
            },
            'active_stream_count': len(self._stream_rate_limiters),
        }

    def set_max_concurrent_streams(self, max_streams: int) -> None:
        """
        设置最大并发流数

        Args:
            max_streams: 新的最大并发流数
        """
        self.backpressure.set_max_concurrent_streams(max_streams)
        # 更新全局限流速率
        new_global_rate = max_streams * self._rate_per_stream
        self.global_rate_limiter.set_rate(new_global_rate)
        self.global_rate_limiter.set_capacity(new_global_rate * 2)

    def set_rate_per_stream(self, rate: float) -> None:
        """
        设置每个流的速率限制

        Args:
            rate: 新的速率（每秒）
        """
        self._rate_per_stream = rate
        with self._lock:
            for limiter in self._stream_rate_limiters.values():
                limiter.set_rate(rate)
                limiter.set_capacity(rate * 2)

        new_global_rate = self.backpressure.max_concurrent_streams * rate
        self.global_rate_limiter.set_rate(new_global_rate)
        self.global_rate_limiter.set_capacity(new_global_rate * 2)

    def cleanup_idle_streams(self, idle_timeout_seconds: float = 300.0) -> int:
        """
        清理空闲流

        Args:
            idle_timeout_seconds: 空闲超时时间（秒）

        Returns:
            清理的流数
        """
        # 注意：这里简化处理，实际实现需要跟踪每个流的最后活跃时间
        return 0

    def reload_config(
        self,
        changed_paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        重新加载背压/并发配置（热更新）

        Args:
            changed_paths: 变更的配置路径列表

        Returns:
            {"changed": {...old->new}, "errors": {...}}
        """
        result: Dict[str, Any] = {"changed": {}, "errors": {}}

        try:
            backpressure_config = config_manager.get(
                'stream_prediction.backpressure', {}
            )

            max_concurrent = backpressure_config.get(
                'max_concurrent_streams', self.backpressure.max_concurrent_streams
            )
            if isinstance(max_concurrent, int) and max_concurrent > 0:
                old = self.backpressure.max_concurrent_streams
                if old != max_concurrent:
                    self.set_max_concurrent_streams(max_concurrent)
                    result["changed"]["max_concurrent_streams"] = f"{old} -> {max_concurrent}"

            rate_per_stream = backpressure_config.get(
                'rate_per_stream', self._rate_per_stream
            )
            if isinstance(rate_per_stream, (int, float)) and rate_per_stream > 0:
                old = self._rate_per_stream
                if old != rate_per_stream:
                    self.set_rate_per_stream(float(rate_per_stream))
                    result["changed"]["rate_per_stream"] = f"{old} -> {rate_per_stream}"

            max_queue = backpressure_config.get(
                'max_queue_size', self.backpressure.max_queue_size
            )
            if isinstance(max_queue, int) and max_queue >= 0:
                old = self.backpressure.max_queue_size
                if old != max_queue:
                    self.backpressure.set_max_queue_size(max_queue)
                    result["changed"]["max_queue_size"] = f"{old} -> {max_queue}"

            queue_timeout = backpressure_config.get(
                'queue_timeout_seconds', self.backpressure.queue_timeout_seconds
            )
            if isinstance(queue_timeout, (int, float)) and queue_timeout > 0:
                old = self.backpressure.queue_timeout_seconds
                if old != queue_timeout:
                    self.backpressure.queue_timeout_seconds = float(queue_timeout)
                    result["changed"]["queue_timeout_seconds"] = f"{old} -> {queue_timeout}"

            logger.info(
                f"背压配置热更新完成: changed={len(result['changed'])}, "
                f"errors={len(result['errors'])}"
            )
        except Exception as e:
            logger.exception(f"背压配置热更新失败: {e}")
            result["errors"]["__global__"] = str(e)

        return result


def create_backpressure_controller_from_config() -> StreamConcurrencyManager:
    """
    从配置创建背压控制器

    Returns:
        StreamConcurrencyManager
    """
    stream_config = config.get('stream_prediction', {})
    backpressure_config = stream_config.get('backpressure', {})

    max_concurrent = backpressure_config.get('max_concurrent_streams', 100)
    rate_per_stream = backpressure_config.get('rate_per_stream', 10.0)
    max_queue = backpressure_config.get('max_queue_size', 500)
    queue_timeout = backpressure_config.get('queue_timeout_seconds', 30.0)

    return StreamConcurrencyManager(
        max_concurrent_streams=max_concurrent,
        rate_per_stream=rate_per_stream,
        max_queue_size=max_queue,
        queue_timeout_seconds=queue_timeout,
    )
