"""
实时流式预测引擎模块

提供基于滑动窗口的实时流式预测能力，支持：
- Kafka/MQTT/HTTP 多种流输入源
- 单条或微批次数据处理
- Per-bolt 滑动窗口（内存/Redis）
- 窗口满触发推理
- 状态变更事件发布
- 背压与限流控制
- 与批处理模式共存

使用方式:
    from app.streaming import StreamPredictionEngine
    
    engine = StreamPredictionEngine()
    engine.start()
"""

from app.streaming.window_manager import (
    SlidingWindowManager,
    MemoryWindowManager,
    RedisWindowManager,
    WindowData,
)
from app.streaming.backpressure import (
    BackpressureController,
    RateLimiter,
    StreamConcurrencyManager,
)
from app.streaming.event_publisher import (
    EventPublisher,
    StreamEvent,
    InProcessEventPublisher,
    KafkaEventPublisher,
    MQTTEventPublisher,
)
from app.streaming.stream_adapters import (
    StreamAdapter,
    HTTPStreamAdapter,
    KafkaStreamAdapter,
    MQTTStreamAdapter,
    StreamMessage,
)
from app.streaming.engine import StreamPredictionEngine, StreamPredictionMode

__all__ = [
    'SlidingWindowManager',
    'MemoryWindowManager',
    'RedisWindowManager',
    'WindowData',
    'BackpressureController',
    'RateLimiter',
    'StreamConcurrencyManager',
    'EventPublisher',
    'StreamEvent',
    'InProcessEventPublisher',
    'KafkaEventPublisher',
    'MQTTEventPublisher',
    'StreamAdapter',
    'HTTPStreamAdapter',
    'KafkaStreamAdapter',
    'MQTTStreamAdapter',
    'StreamMessage',
    'StreamPredictionEngine',
    'StreamPredictionMode',
]
