"""
内存发布/订阅事件总线模块

提供轻量级的进程内 pub/sub 机制，用于配置热更新通知。

使用示例:
    from app.core.event_bus import event_bus, EventType

    # 订阅配置变更
    def on_config_change(event):
        print(f"配置变更: {event.data}")

    event_bus.subscribe(EventType.CONFIG_CHANGED, on_config_change)

    # 发布配置变更
    event_bus.publish(EventType.CONFIG_CHANGED, {"version": 1, "changes": [...]})
"""

import threading
import enum
import time
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from loguru import logger


class EventType(str, enum.Enum):
    """
    事件类型枚举

    - CONFIG_CHANGED: 配置已变更（持久化后）
    - CONFIG_PRE_RELOAD: 配置即将重载通知
    - CONFIG_POST_RELOAD: 配置重载完成通知
    - SCHEDULER_CONFIG_CHANGED: 调度器配置变更
    - STREAM_CONFIG_CHANGED: 流式配置变更
    - LOG_LEVEL_CHANGED: 日志级别变更
    - STRATEGY_CONFIG_CHANGED: 策略配置变更
    - REDIS_CONFIG_SYNC: 跨实例Redis同步事件
    - MODEL_DRIFT_DETECTED: 检测到模型漂移
    """
    CONFIG_CHANGED = "config_changed"
    CONFIG_PRE_RELOAD = "config_pre_reload"
    CONFIG_POST_RELOAD = "config_post_reload"
    SCHEDULER_CONFIG_CHANGED = "scheduler_config_changed"
    STREAM_CONFIG_CHANGED = "stream_config_changed"
    LOG_LEVEL_CHANGED = "log_level_changed"
    STRATEGY_CONFIG_CHANGED = "strategy_config_changed"
    REDIS_CONFIG_SYNC = "redis_config_sync"
    MODEL_DRIFT_DETECTED = "model_drift_detected"


@dataclass
class Event:
    """
    事件数据结构

    Attributes:
        event_type: 事件类型
        data: 事件数据（字典）
        timestamp: 事件时间戳
        source: 事件来源（实例ID）
        event_id: 事件唯一ID
    """
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "local"
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"{self.event_type.value}-{self.timestamp}-{id(self)}"


class EventBus:
    """
    内存事件总线（发布/订阅模式）

    线程安全，支持：
    - 按事件类型订阅/取消订阅
    - 同步/异步发布
    - 一次性订阅
    - 通配符订阅（订阅所有事件）
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Dict[str, Any]]] = {}
        self._wildcard_subscribers: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._instance_id = self._generate_instance_id()
        logger.info(f"事件总线初始化完成, instance_id={self._instance_id}")

    @staticmethod
    def _generate_instance_id() -> str:
        """生成实例ID"""
        import os
        import uuid
        pid = os.getpid()
        host = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        return f"{host}-{pid}-{uuid.uuid4().hex[:8]}"

    @property
    def instance_id(self) -> str:
        return self._instance_id

    def subscribe(
        self,
        event_type: Optional[EventType],
        callback: Callable[[Event], None],
        *,
        once: bool = False,
        priority: int = 0,
        filter_func: Optional[Callable[[Event], bool]] = None,
    ) -> str:
        """
        订阅事件

        Args:
            event_type: 事件类型，None 表示订阅所有事件（通配符）
            callback: 回调函数
            once: 是否一次性订阅（触发后自动取消）
            priority: 优先级（数值越大越先执行）
            filter_func: 过滤函数，返回True才触发回调

        Returns:
            订阅ID，可用于取消订阅
        """
        subscriber_id = f"sub-{id(callback)}-{time.time()}-{priority}"
        subscriber_info = {
            "id": subscriber_id,
            "callback": callback,
            "once": once,
            "priority": priority,
            "filter_func": filter_func,
            "created_at": time.time(),
        }

        with self._lock:
            if event_type is None:
                self._wildcard_subscribers.append(subscriber_info)
                self._wildcard_subscribers.sort(key=lambda s: -s["priority"])
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(subscriber_info)
                self._subscribers[event_type].sort(key=lambda s: -s["priority"])

        logger.debug(
            f"订阅事件: type={event_type.value if event_type else '*'}, "
            f"sub_id={subscriber_id}, priority={priority}"
        )
        return subscriber_id

    def unsubscribe(self, subscriber_id: str) -> bool:
        """
        取消订阅

        Args:
            subscriber_id: 订阅ID

        Returns:
            是否成功取消
        """
        with self._lock:
            for event_type, subs in self._subscribers.items():
                for i, sub in enumerate(subs):
                    if sub["id"] == subscriber_id:
                        subs.pop(i)
                        logger.debug(f"取消订阅: sub_id={subscriber_id}")
                        return True

            for i, sub in enumerate(self._wildcard_subscribers):
                if sub["id"] == subscriber_id:
                    self._wildcard_subscribers.pop(i)
                    logger.debug(f"取消通配符订阅: sub_id={subscriber_id}")
                    return True

        return False

    def publish(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        *,
        source: Optional[str] = None,
        event_id: Optional[str] = None,
        asynchronous: bool = False,
    ) -> Event:
        """
        发布事件

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
            event_id: 自定义事件ID
            asynchronous: 是否异步发布（使用线程池）

        Returns:
            创建的Event对象
        """
        event = Event(
            event_type=event_type,
            data=data or {},
            source=source or self._instance_id,
            event_id=event_id or "",
        )

        self._add_to_history(event)

        if asynchronous:
            threading.Thread(
                target=self._dispatch_event,
                args=(event,),
                daemon=True,
                name=f"event-dispatch-{event_type.value}",
            ).start()
        else:
            self._dispatch_event(event)

        return event

    def _dispatch_event(self, event: Event) -> None:
        """分发事件到所有订阅者"""
        callbacks_to_remove = []

        try:
            with self._lock:
                typed_subscribers = list(
                    self._subscribers.get(event.event_type, [])
                )
                wildcard_subs = list(self._wildcard_subscribers)
                all_subscribers = typed_subscribers + wildcard_subs

            for subscriber in all_subscribers:
                try:
                    filter_func = subscriber.get("filter_func")
                    if filter_func and not filter_func(event):
                        continue

                    callback = subscriber["callback"]
                    callback(event)

                    if subscriber.get("once"):
                        callbacks_to_remove.append(subscriber["id"])

                except Exception as e:
                    logger.exception(
                        f"事件回调执行异常: type={event.event_type.value}, "
                        f"sub_id={subscriber['id']}, error={e}"
                    )

        finally:
            if callbacks_to_remove:
                for sub_id in callbacks_to_remove:
                    self.unsubscribe(sub_id)

    def _add_to_history(self, event: Event) -> None:
        """添加事件到历史记录"""
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        since_timestamp: Optional[float] = None,
    ) -> List[Event]:
        """
        获取事件历史

        Args:
            event_type: 过滤事件类型，None表示所有
            limit: 返回数量上限
            since_timestamp: 只返回此时间戳之后的事件

        Returns:
            事件列表（从新到旧）
        """
        with self._lock:
            history = list(reversed(self._event_history))

        if event_type:
            history = [e for e in history if e.event_type == event_type]

        if since_timestamp:
            history = [e for e in history if e.timestamp >= since_timestamp]

        return history[:limit]

    def clear_history(self) -> None:
        """清空事件历史"""
        with self._lock:
            self._event_history.clear()

    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """
        获取订阅者数量

        Args:
            event_type: 事件类型，None表示所有

        Returns:
            订阅者数量
        """
        with self._lock:
            if event_type is None:
                total = len(self._wildcard_subscribers)
                for subs in self._subscribers.values():
                    total += len(subs)
                return total
            return len(self._subscribers.get(event_type, []))


# 全局事件总线实例
event_bus = EventBus()
