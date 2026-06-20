"""
事件发布器模块

负责发布状态变更事件到消息队列，供告警系统等下游订阅。

主要组件:
- StreamEvent: 流事件数据结构
- EventPublisher: 事件发布器基类
- InProcessEventPublisher: 进程内事件发布器（用于测试和单节点）
- KafkaEventPublisher: Kafka 事件发布器
- MQTTEventPublisher: MQTT 事件发布器
- HttpEventPublisher: HTTP Webhook 事件发布器
"""

import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger

from app.utils.config import config


@dataclass
class StreamEvent:
    """
    流事件数据结构

    Attributes:
        event_id: 事件唯一ID
        event_type: 事件类型 (status_change / prediction / alert)
        node_type: 节点类型 (bolt / flange)
        node_id: 节点ID
        timestamp: 事件时间戳
        data: 事件数据
        source: 事件来源 (stream / batch)
        metadata: 元数据
    """
    event_id: str
    event_type: str
    node_type: str
    node_id: str
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "stream"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamEvent':
        """从字典创建"""
        return cls(
            event_id=data['event_id'],
            event_type=data['event_type'],
            node_type=data['node_type'],
            node_id=data['node_id'],
            timestamp=data['timestamp'],
            data=data.get('data', {}),
            source=data.get('source', 'stream'),
            metadata=data.get('metadata', {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'StreamEvent':
        """从 JSON 字符串创建"""
        return cls.from_dict(json.loads(json_str))


class EventPublisher:
    """
    事件发布器基类

    定义事件发布的标准接口。
    """

    def __init__(self, name: str = "default"):
        """
        初始化事件发布器

        Args:
            name: 发布器名称
        """
        self.name = name
        self._subscribers: List[Callable] = []
        self._event_count = 0
        logger.info(f"事件发布器初始化: {name}")

    def subscribe(self, callback: Callable) -> None:
        """
        订阅事件

        Args:
            callback: 回调函数，接收 StreamEvent 参数
        """
        self._subscribers.append(callback)
        logger.debug(f"已添加事件订阅者，当前订阅者数: {len(self._subscribers)}")

    def unsubscribe(self, callback: Callable) -> None:
        """
        取消订阅

        Args:
            callback: 回调函数
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.debug(f"已移除事件订阅者，当前订阅者数: {len(self._subscribers)}")

    def _notify_subscribers(self, event: StreamEvent) -> None:
        """
        通知所有订阅者

        Args:
            event: 流事件
        """
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"事件订阅者回调失败: {e}")

    def publish(self, event: StreamEvent) -> bool:
        """
        发布事件

        Args:
            event: 流事件

        Returns:
            bool: 是否发布成功
        """
        raise NotImplementedError

    def publish_status_change(
        self,
        node_type: str,
        node_id: str,
        old_status: int,
        new_status: int,
        prediction_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        发布状态变更事件

        Args:
            node_type: 节点类型
            node_id: 节点ID
            old_status: 旧状态码
            new_status: 新状态码
            prediction_data: 预测数据
            metadata: 元数据

        Returns:
            bool: 是否发布成功
        """
        import uuid

        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type='status_change',
            node_type=node_type,
            node_id=node_id,
            timestamp=datetime.now().isoformat(),
            data={
                'old_status': old_status,
                'new_status': new_status,
                'prediction': prediction_data,
            },
            source='stream',
            metadata=metadata or {},
        )
        return self.publish(event)

    def publish_prediction(
        self,
        node_type: str,
        node_id: str,
        prediction_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        发布预测事件

        Args:
            node_type: 节点类型
            node_id: 节点ID
            prediction_data: 预测数据
            metadata: 元数据

        Returns:
            bool: 是否发布成功
        """
        import uuid

        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type='prediction',
            node_type=node_type,
            node_id=node_id,
            timestamp=datetime.now().isoformat(),
            data={'prediction': prediction_data},
            source='stream',
            metadata=metadata or {},
        )
        return self.publish(event)

    def publish_alert(
        self,
        node_type: str,
        node_id: str,
        alert_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        发布告警事件

        Args:
            node_type: 节点类型
            node_id: 节点ID
            alert_data: 告警数据
            metadata: 元数据

        Returns:
            bool: 是否发布成功
        """
        import uuid

        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type='alert',
            node_type=node_type,
            node_id=node_id,
            timestamp=datetime.now().isoformat(),
            data={'alert': alert_data},
            source='stream',
            metadata=metadata or {},
        )
        return self.publish(event)

    def get_event_count(self) -> int:
        """获取已发布事件数"""
        return self._event_count

    def start(self) -> None:
        """启动发布器"""
        pass

    def stop(self) -> None:
        """停止发布器"""
        pass


class InProcessEventPublisher(EventPublisher):
    """
    进程内事件发布器

    在同一进程内通过回调方式发布事件，适用于测试和单节点部署。
    """

    def __init__(self, name: str = "in_process"):
        """
        初始化进程内事件发布器

        Args:
            name: 发布器名称
        """
        super().__init__(name)
        self._lock = threading.Lock()
        logger.info("进程内事件发布器初始化完成")

    def publish(self, event: StreamEvent) -> bool:
        """
        发布事件

        Args:
            event: 流事件

        Returns:
            bool: 是否发布成功
        """
        try:
            with self._lock:
                self._event_count += 1

            # 通知订阅者
            self._notify_subscribers(event)

            logger.debug(
                f"事件已发布: type={event.event_type}, "
                f"node={event.node_type}/{event.node_id}"
            )
            return True
        except Exception as e:
            logger.error(f"发布事件失败: {e}")
            return False


class KafkaEventPublisher(EventPublisher):
    """
    Kafka 事件发布器

    将事件发布到 Kafka 消息队列。
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "stream_events",
        name: str = "kafka",
    ):
        """
        初始化 Kafka 事件发布器

        Args:
            bootstrap_servers: Kafka 服务器地址
            topic: 主题名称
            name: 发布器名称
        """
        super().__init__(name)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer = None
        self._lock = threading.Lock()
        self._init_producer()

    def _init_producer(self) -> None:
        """初始化 Kafka 生产者"""
        try:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                linger_ms=10,
            )
            logger.info(
                f"Kafka事件发布器连接成功: {self.bootstrap_servers}, topic={self.topic}"
            )
        except ImportError:
            logger.warning("kafka-python 库未安装，Kafka事件发布器不可用")
        except Exception as e:
            logger.error(f"Kafka连接失败: {e}")
            self._producer = None

    def _is_available(self) -> bool:
        """检查是否可用"""
        return self._producer is not None

    def publish(self, event: StreamEvent) -> bool:
        """
        发布事件

        Args:
            event: 流事件

        Returns:
            bool: 是否发布成功
        """
        if not self._is_available():
            return False

        try:
            with self._lock:
                self._event_count += 1

            future = self._producer.send(
                self.topic,
                value=event.to_dict(),
                key=f"{event.node_type}:{event.node_id}".encode('utf-8'),
            )
            future.add_callback(self._on_send_success)
            future.add_errback(self._on_send_error)

            # 通知本地订阅者
            self._notify_subscribers(event)

            return True
        except Exception as e:
            logger.error(f"发布Kafka事件失败: {e}")
            return False

    def _on_send_success(self, record_metadata) -> None:
        """发送成功回调"""
        logger.debug(
            f"Kafka事件发送成功: topic={record_metadata.topic}, "
            f"partition={record_metadata.partition}, offset={record_metadata.offset}"
        )

    def _on_send_error(self, exception) -> None:
        """发送错误回调"""
        logger.error(f"Kafka事件发送失败: {exception}")

    def stop(self) -> None:
        """停止发布器"""
        if self._producer:
            self._producer.flush()
            self._producer.close()
            logger.info("Kafka事件发布器已停止")


class MQTTEventPublisher(EventPublisher):
    """
    MQTT 事件发布器

    将事件发布到 MQTT 消息队列。
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        topic_prefix: str = "stream/events",
        client_id: str = "stream_publisher",
        name: str = "mqtt",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        初始化 MQTT 事件发布器

        Args:
            broker: MQTT 代理地址
            port: 端口号
            topic_prefix: 主题前缀
            client_id: 客户端ID
            name: 发布器名称
            username: 用户名
            password: 密码
        """
        super().__init__(name)
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
        self.client_id = client_id
        self.username = username
        self.password = password
        self._client = None
        self._lock = threading.Lock()
        self._init_client()

    def _init_client(self) -> None:
        """初始化 MQTT 客户端"""
        try:
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(self.client_id)
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            self._client.connect_async(self.broker, self.port)
            self._client.loop_start()

            logger.info(
                f"MQTT事件发布器正在连接: {self.broker}:{self.port}"
            )
        except ImportError:
            logger.warning("paho-mqtt 库未安装，MQTT事件发布器不可用")
        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
            self._client = None

    def _on_connect(self, client, userdata, flags, rc) -> None:
        """连接回调"""
        if rc == 0:
            logger.info(f"MQTT事件发布器连接成功: {self.broker}:{self.port}")
        else:
            logger.error(f"MQTT连接失败，错误码: {rc}")

    def _on_disconnect(self, client, userdata, rc) -> None:
        """断开连接回调"""
        logger.warning(f"MQTT连接断开，错误码: {rc}")

    def _is_available(self) -> bool:
        """检查是否可用"""
        return self._client is not None and self._client.is_connected()

    def _make_topic(self, event: StreamEvent) -> str:
        """构造主题"""
        return f"{self.topic_prefix}/{event.event_type}/{event.node_type}/{event.node_id}"

    def publish(self, event: StreamEvent) -> bool:
        """
        发布事件

        Args:
            event: 流事件

        Returns:
            bool: 是否发布成功
        """
        if not self._is_available():
            return False

        try:
            with self._lock:
                self._event_count += 1

            topic = self._make_topic(event)
            payload = event.to_json()

            result = self._client.publish(topic, payload, qos=1)
            result.wait_for_publish()

            # 通知本地订阅者
            self._notify_subscribers(event)

            logger.debug(f"MQTT事件已发布: topic={topic}")
            return True
        except Exception as e:
            logger.error(f"发布MQTT事件失败: {e}")
            return False

    def stop(self) -> None:
        """停止发布器"""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT事件发布器已停止")


class HttpEventPublisher(EventPublisher):

    def __init__(self, name: str = "http"):
        super().__init__(name)
        self._lock = threading.Lock()
        logger.info("HTTP事件发布器初始化完成")

    def _map_event_type(self, event: StreamEvent) -> str:
        if event.event_type == 'status_change':
            return 'status_changed'
        elif event.event_type == 'alert':
            alert_data = event.data.get('alert', {})
            if alert_data.get('fault_detected'):
                return 'fault_detected'
            if alert_data.get('risk_high'):
                return 'risk_high'
            return 'alert'
        return event.event_type

    def _determine_level(self, event: StreamEvent) -> int:
        if event.event_type == 'status_change':
            return event.data.get('new_status', 0)
        elif event.event_type == 'alert':
            return event.data.get('alert', {}).get('alert_level', 0)
        return 0

    def publish(self, event: StreamEvent) -> bool:
        try:
            from app.services.webhook import (
                get_webhook_subscription_service,
                get_webhook_delivery_service,
                get_webhook_digest_manager,
            )

            subscription_service = get_webhook_subscription_service()
            delivery_service = get_webhook_delivery_service()
            digest_manager = get_webhook_digest_manager()

            webhook_event_type = self._map_event_type(event)
            level = self._determine_level(event)

            matching_subscriptions = subscription_service.get_matching_subscriptions(
                event_type=webhook_event_type,
                node_type=event.node_type,
                node_id=event.node_id,
                level=level,
            )

            for subscription in matching_subscriptions:
                if not subscription.enabled:
                    continue
                if subscription.enable_digest:
                    digest_manager.add_event(subscription, event.to_dict())
                else:
                    thread = threading.Thread(
                        target=delivery_service.deliver_to_subscription,
                        args=(subscription, event.to_dict()),
                        daemon=True,
                    )
                    thread.start()

            with self._lock:
                self._event_count += 1

            self._notify_subscribers(event)

            logger.debug(
                f"HTTP事件已发布: type={event.event_type}, "
                f"node={event.node_type}/{event.node_id}, "
                f"subscriptions={len(matching_subscriptions)}"
            )
            return True
        except Exception as e:
            logger.error(f"发布HTTP事件失败: {e}")
            return False


class CompositeEventPublisher(EventPublisher):
    """
    组合事件发布器

    同时向多个发布器发布事件。
    """

    def __init__(self, publishers: List[EventPublisher], name: str = "composite"):
        """
        初始化组合事件发布器

        Args:
            publishers: 发布器列表
            name: 发布器名称
        """
        super().__init__(name)
        self._publishers = publishers
        logger.info(
            f"组合事件发布器初始化完成，包含 {len(publishers)} 个发布器"
        )

    def publish(self, event: StreamEvent) -> bool:
        """
        发布事件到所有发布器

        Args:
            event: 流事件

        Returns:
            bool: 至少一个发布成功返回 True
        """
        success = False
        for publisher in self._publishers:
            try:
                if publisher.publish(event):
                    success = True
            except Exception as e:
                logger.error(f"发布器 {publisher.name} 发布失败: {e}")

        if success:
            self._event_count += 1

        return success

    def subscribe(self, callback: Callable) -> None:
        """
        订阅事件（订阅第一个可用的发布器）

        Args:
            callback: 回调函数
        """
        super().subscribe(callback)
        for publisher in self._publishers:
            publisher.subscribe(callback)

    def start(self) -> None:
        """启动所有发布器"""
        for publisher in self._publishers:
            try:
                publisher.start()
            except Exception as e:
                logger.error(f"启动发布器 {publisher.name} 失败: {e}")

    def stop(self) -> None:
        """停止所有发布器"""
        for publisher in self._publishers:
            try:
                publisher.stop()
            except Exception as e:
                logger.error(f"停止发布器 {publisher.name} 失败: {e}")


def create_event_publisher_from_config() -> EventPublisher:
    """
    从配置创建事件发布器

    Returns:
        EventPublisher
    """
    stream_config = config.get('stream_prediction', {})
    event_config = stream_config.get('event_publishing', {})

    publisher_type = event_config.get('type', 'in_process')
    publishers = []

    # 总是创建进程内发布器用于本地回调
    in_process = InProcessEventPublisher()
    publishers.append(in_process)

    if publisher_type == 'kafka':
        kafka_config = event_config.get('kafka', {})
        kafka_publisher = KafkaEventPublisher(
            bootstrap_servers=kafka_config.get('bootstrap_servers', 'localhost:9092'),
            topic=kafka_config.get('topic', 'stream_events'),
        )
        publishers.append(kafka_publisher)

    elif publisher_type == 'mqtt':
        mqtt_config = event_config.get('mqtt', {})
        mqtt_publisher = MQTTEventPublisher(
            broker=mqtt_config.get('broker', 'localhost'),
            port=mqtt_config.get('port', 1883),
            topic_prefix=mqtt_config.get('topic_prefix', 'stream/events'),
            username=mqtt_config.get('username'),
            password=mqtt_config.get('password'),
        )
        publishers.append(mqtt_publisher)

    elif publisher_type == 'http':
        http_publisher = HttpEventPublisher()
        publishers.append(http_publisher)

    if len(publishers) == 1:
        return publishers[0]
    else:
        return CompositeEventPublisher(publishers)
