"""
流输入适配器模块

提供多种流数据源接入能力，支持：
- HTTP 流（SSE/WebSocket/POST）
- Kafka 消息队列
- MQTT 消息队列
- 自定义适配器

主要组件:
- StreamMessage: 流消息数据结构
- StreamAdapter: 流适配器基类
- HTTPStreamAdapter: HTTP 流适配器
- KafkaStreamAdapter: Kafka 流适配器
- MQTTStreamAdapter: MQTT 流适配器
"""

import json
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from loguru import logger

from app.utils.config import config


@dataclass
class StreamMessage:
    """
    流消息数据结构

    Attributes:
        message_id: 消息唯一ID
        stream_id: 流ID（通常是 bolt_id 或 flange_id）
        node_type: 节点类型 (bolt / flange)
        node_id: 节点ID
        timestamp: 消息时间戳
        values: 数据值列表（单条或微批次）
        timestamps: 数据时间戳列表
        metadata: 元数据
        tenant_id: 租户ID（用于多租户隔离）
    """
    message_id: str
    stream_id: str
    node_type: str
    node_id: str
    timestamp: str
    values: List[float]
    timestamps: List[str]
    metadata: Dict[str, Any] = None
    tenant_id: str = "default"

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_batch(self) -> bool:
        """是否为批次数据"""
        return len(self.values) > 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'message_id': self.message_id,
            'stream_id': self.stream_id,
            'node_type': self.node_type,
            'node_id': self.node_id,
            'timestamp': self.timestamp,
            'values': self.values,
            'timestamps': self.timestamps,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamMessage':
        """从字典创建"""
        return cls(
            message_id=data['message_id'],
            stream_id=data['stream_id'],
            node_type=data['node_type'],
            node_id=data['node_id'],
            timestamp=data['timestamp'],
            values=data.get('values', []),
            timestamps=data.get('timestamps', []),
            metadata=data.get('metadata', {}),
        )


class StreamAdapter(ABC):
    """
    流适配器基类

    定义流数据接入的标准接口。
    """

    def __init__(self, name: str = "default"):
        """
        初始化流适配器

        Args:
            name: 适配器名称
        """
        self.name = name
        self._message_handlers: List[Callable] = []
        self._is_running = False
        self._message_count = 0
        logger.info(f"流适配器初始化: {name}")

    def register_message_handler(self, handler: Callable) -> None:
        """
        注册消息处理回调

        Args:
            handler: 处理函数，接收 StreamMessage 参数
        """
        self._message_handlers.append(handler)
        logger.debug(
            f"已注册消息处理器，当前处理器数: {len(self._message_handlers)}"
        )

    def unregister_message_handler(self, handler: Callable) -> None:
        """
        注销消息处理回调

        Args:
            handler: 处理函数
        """
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)
            logger.debug(
                f"已移除消息处理器，当前处理器数: {len(self._message_handlers)}"
            )

    def _dispatch_message(self, message: StreamMessage) -> None:
        """
        分发消息到所有处理器

        Args:
            message: 流消息
        """
        self._message_count += 1
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"消息处理器执行失败: {e}")

    @abstractmethod
    def start(self) -> None:
        """启动适配器"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止适配器"""
        pass

    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._is_running

    @property
    def message_count(self) -> int:
        """已处理消息数"""
        return self._message_count

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            'name': self.name,
            'is_running': self._is_running,
            'message_count': self._message_count,
            'handler_count': len(self._message_handlers),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self._message_count = 0


class HTTPStreamAdapter(StreamAdapter):
    """
    HTTP 流适配器

    通过 HTTP 接口接收流数据，支持：
    - 单条数据 POST
    - 批量数据 POST
    - SSE (Server-Sent Events)
    """

    def __init__(self, name: str = "http"):
        """
        初始化 HTTP 流适配器

        Args:
            name: 适配器名称
        """
        super().__init__(name)
        self._lock = threading.Lock()
        logger.info("HTTP流适配器初始化完成")

    def start(self) -> None:
        """启动适配器"""
        if self._is_running:
            return
        self._is_running = True
        logger.info("HTTP流适配器已启动")

    def stop(self) -> None:
        """停止适配器"""
        self._is_running = False
        logger.info("HTTP流适配器已停止")

    def handle_message(self, message_data: Dict[str, Any]) -> bool:
        """
        处理接收到的消息

        Args:
            message_data: 消息数据字典

        Returns:
            bool: 是否处理成功
        """
        if not self._is_running:
            return False

        try:
            message = self._parse_message(message_data)
            self._dispatch_message(message)
            return True
        except Exception as e:
            logger.error(f"处理HTTP消息失败: {e}")
            return False

    def _parse_message(self, data: Dict[str, Any]) -> StreamMessage:
        """
        解析消息数据

        Args:
            data: 原始数据

        Returns:
            StreamMessage
        """
        import uuid

        node_type = data.get('node_type', 'bolt')
        node_id = data.get('node_id', data.get('bolt_id', data.get('flange_id', '')))
        stream_id = f"{node_type}:{node_id}"

        # 处理单条或批量数据
        if 'value' in data and 'timestamp' in data:
            values = [float(data['value'])]
            timestamps = [str(data['timestamp'])]
        elif 'values' in data and 'timestamps' in data:
            values = [float(v) for v in data['values']]
            timestamps = [str(t) for t in data['timestamps']]
        elif 'data' in data:
            raw_data = data['data']
            if isinstance(raw_data, list) and len(raw_data) > 0:
                if isinstance(raw_data[0], list):
                    values = [float(item[1]) for item in raw_data]
                    timestamps = [str(item[0]) for item in raw_data]
                else:
                    values = [float(raw_data[1])]
                    timestamps = [str(raw_data[0])]
            else:
                values = []
                timestamps = []
        else:
            raise ValueError("无法解析消息数据，缺少必要字段")

        msg = StreamMessage(
            message_id=str(data.get('message_id', uuid.uuid4())),
            stream_id=stream_id,
            node_type=node_type,
            node_id=node_id,
            timestamp=timestamps[-1] if timestamps else str(time.time()),
            values=values,
            timestamps=timestamps,
            metadata=data.get('metadata', {}),
        )

        return msg

    def handle_sse_connect(self, client_id: str) -> bool:
        """
        处理 SSE 客户端连接

        Args:
            client_id: 客户端ID

        Returns:
            bool
        """
        logger.info(f"SSE客户端连接: {client_id}")
        return True

    def handle_sse_disconnect(self, client_id: str) -> None:
        """
        处理 SSE 客户端断开

        Args:
            client_id: 客户端ID
        """
        logger.info(f"SSE客户端断开: {client_id}")


class KafkaStreamAdapter(StreamAdapter):
    """
    Kafka 流适配器

    从 Kafka 主题消费流数据。
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "bolt_data",
        group_id: str = "stream_prediction",
        name: str = "kafka",
    ):
        """
        初始化 Kafka 流适配器

        Args:
            bootstrap_servers: Kafka 服务器地址
            topic: 主题名称
            group_id: 消费者组ID
            name: 适配器名称
        """
        super().__init__(name)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self._consumer = None
        self._thread = None
        self._lock = threading.Lock()
        logger.info(f"Kafka流适配器初始化: topic={topic}")

    def _init_consumer(self) -> None:
        """初始化 Kafka 消费者"""
        try:
            from kafka import KafkaConsumer

            self._consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            )
            logger.info(
                f"Kafka消费者连接成功: {self.bootstrap_servers}, topic={self.topic}"
            )
        except ImportError:
            logger.warning("kafka-python 库未安装，Kafka流适配器不可用")
        except Exception as e:
            logger.error(f"Kafka消费者连接失败: {e}")
            self._consumer = None

    def _is_available(self) -> bool:
        """检查是否可用"""
        return self._consumer is not None

    def start(self) -> None:
        """启动适配器"""
        if self._is_running:
            return

        self._init_consumer()
        if not self._is_available():
            logger.warning("Kafka流适配器不可用，无法启动")
            return

        self._is_running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Kafka流适配器已启动")

    def _consume_loop(self) -> None:
        """消费循环"""
        import uuid

        try:
            for message in self._consumer:
                if not self._is_running:
                    break

                try:
                    data = message.value
                    node_type = data.get('node_type', 'bolt')
                    node_id = data.get(
                        'node_id',
                        data.get('bolt_id', data.get('flange_id', ''))
                    )
                    stream_id = f"{node_type}:{node_id}"

                    if 'value' in data and 'timestamp' in data:
                        values = [float(data['value'])]
                        timestamps = [str(data['timestamp'])]
                    elif 'values' in data and 'timestamps' in data:
                        values = [float(v) for v in data['values']]
                        timestamps = [str(t) for t in data['timestamps']]
                    elif 'data' in data:
                        raw_data = data['data']
                        if isinstance(raw_data, list) and len(raw_data) > 0:
                            if isinstance(raw_data[0], list):
                                values = [float(item[1]) for item in raw_data]
                                timestamps = [str(item[0]) for item in raw_data]
                            else:
                                values = [float(raw_data[1])]
                                timestamps = [str(raw_data[0])]
                        else:
                            continue
                    else:
                        continue

                    msg = StreamMessage(
                        message_id=str(uuid.uuid4()),
                        stream_id=stream_id,
                        node_type=node_type,
                        node_id=node_id,
                        timestamp=timestamps[-1] if timestamps else str(time.time()),
                        values=values,
                        timestamps=timestamps,
                        metadata=data.get('metadata', {}),
                    )
                    self._dispatch_message(msg)

                except Exception as e:
                    logger.error(f"处理Kafka消息失败: {e}")
        except Exception as e:
            logger.error(f"Kafka消费循环异常: {e}")
        finally:
            if self._consumer:
                self._consumer.close()
            self._is_running = False
            logger.info("Kafka消费循环已停止")

    def stop(self) -> None:
        """停止适配器"""
        if not self._is_running:
            return

        self._is_running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Kafka流适配器已停止")


class MQTTStreamAdapter(StreamAdapter):
    """
    MQTT 流适配器

    从 MQTT 主题订阅流数据。
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        topic: str = "bolt/data/+",
        client_id: str = "stream_prediction",
        name: str = "mqtt",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        初始化 MQTT 流适配器

        Args:
            broker: MQTT 代理地址
            port: 端口号
            topic: 订阅主题
            client_id: 客户端ID
            name: 适配器名称
            username: 用户名
            password: 密码
        """
        super().__init__(name)
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client_id = client_id
        self.username = username
        self.password = password
        self._client = None
        self._lock = threading.Lock()
        logger.info(f"MQTT流适配器初始化: broker={broker}, topic={topic}")

    def _init_client(self) -> None:
        """初始化 MQTT 客户端"""
        try:
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(self.client_id)
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)

            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect

            self._client.connect_async(self.broker, self.port)
            logger.info(f"MQTT客户端正在连接: {self.broker}:{self.port}")
        except ImportError:
            logger.warning("paho-mqtt 库未安装，MQTT流适配器不可用")
        except Exception as e:
            logger.error(f"MQTT客户端初始化失败: {e}")
            self._client = None

    def _is_available(self) -> bool:
        """检查是否可用"""
        return self._client is not None

    def _on_connect(self, client, userdata, flags, rc) -> None:
        """连接回调"""
        if rc == 0:
            logger.info(f"MQTT流适配器连接成功，订阅主题: {self.topic}")
            client.subscribe(self.topic)
        else:
            logger.error(f"MQTT连接失败，错误码: {rc}")

    def _on_disconnect(self, client, userdata, rc) -> None:
        """断开连接回调"""
        logger.warning(f"MQTT连接断开，错误码: {rc}")

    def _on_message(self, client, userdata, msg) -> None:
        """消息接收回调"""
        import uuid

        try:
            payload = json.loads(msg.payload.decode('utf-8'))

            # 从主题中提取节点信息
            topic_parts = msg.topic.split('/')
            node_type = 'bolt'
            node_id = ''

            if len(topic_parts) >= 3:
                node_type = topic_parts[-2] if len(topic_parts) >= 2 else 'bolt'
                node_id = topic_parts[-1]

            node_id = payload.get(
                'node_id',
                payload.get('bolt_id', payload.get('flange_id', node_id))
            )
            node_type = payload.get('node_type', node_type)
            stream_id = f"{node_type}:{node_id}"

            # 解析数据
            if 'value' in payload and 'timestamp' in payload:
                values = [float(payload['value'])]
                timestamps = [str(payload['timestamp'])]
            elif 'values' in payload and 'timestamps' in payload:
                values = [float(v) for v in payload['values']]
                timestamps = [str(t) for t in payload['timestamps']]
            elif 'data' in payload:
                raw_data = payload['data']
                if isinstance(raw_data, list) and len(raw_data) > 0:
                    if isinstance(raw_data[0], list):
                        values = [float(item[1]) for item in raw_data]
                        timestamps = [str(item[0]) for item in raw_data]
                    else:
                        values = [float(raw_data[1])]
                        timestamps = [str(raw_data[0])]
                else:
                    return
            else:
                return

            message = StreamMessage(
                message_id=str(uuid.uuid4()),
                stream_id=stream_id,
                node_type=node_type,
                node_id=node_id,
                timestamp=timestamps[-1] if timestamps else str(time.time()),
                values=values,
                timestamps=timestamps,
                metadata=payload.get('metadata', {}),
            )
            self._dispatch_message(message)

        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")

    def start(self) -> None:
        """启动适配器"""
        if self._is_running:
            return

        self._init_client()
        if not self._is_available():
            logger.warning("MQTT流适配器不可用，无法启动")
            return

        self._is_running = True
        self._client.loop_start()
        logger.info("MQTT流适配器已启动")

    def stop(self) -> None:
        """停止适配器"""
        if not self._is_running:
            return

        self._is_running = False
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
        logger.info("MQTT流适配器已停止")


class CompositeStreamAdapter(StreamAdapter):
    """
    组合流适配器

    同时使用多个流适配器接收数据。
    """

    def __init__(self, adapters: List[StreamAdapter], name: str = "composite"):
        """
        初始化组合流适配器

        Args:
            adapters: 适配器列表
            name: 适配器名称
        """
        super().__init__(name)
        self._adapters = adapters
        logger.info(
            f"组合流适配器初始化完成，包含 {len(adapters)} 个适配器"
        )

    def register_message_handler(self, handler: Callable) -> None:
        """
        注册消息处理回调

        Args:
            handler: 处理函数
        """
        super().register_message_handler(handler)
        for adapter in self._adapters:
            adapter.register_message_handler(handler)

    def start(self) -> None:
        """启动所有适配器"""
        self._is_running = True
        for adapter in self._adapters:
            try:
                adapter.start()
            except Exception as e:
                logger.error(f"启动适配器 {adapter.name} 失败: {e}")
        logger.info("组合流适配器已启动")

    def stop(self) -> None:
        """停止所有适配器"""
        self._is_running = False
        for adapter in self._adapters:
            try:
                adapter.stop()
            except Exception as e:
                logger.error(f"停止适配器 {adapter.name} 失败: {e}")
        logger.info("组合流适配器已停止")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        stats = super().get_stats()
        stats['adapters'] = [
            adapter.get_stats() for adapter in self._adapters
        ]
        return stats


def create_stream_adapters_from_config() -> List[StreamAdapter]:
    """
    从配置创建流适配器列表

    Returns:
        流适配器列表
    """
    stream_config = config.get('stream_prediction', {})
    source_config = stream_config.get('sources', {})
    adapters = []

    # HTTP 适配器（总是创建，用于API接入）
    http_adapter = HTTPStreamAdapter()
    adapters.append(http_adapter)

    # Kafka 适配器
    if source_config.get('kafka', {}).get('enabled', False):
        kafka_config = source_config['kafka']
        kafka_adapter = KafkaStreamAdapter(
            bootstrap_servers=kafka_config.get('bootstrap_servers', 'localhost:9092'),
            topic=kafka_config.get('topic', 'bolt_data'),
            group_id=kafka_config.get('group_id', 'stream_prediction'),
        )
        adapters.append(kafka_adapter)

    # MQTT 适配器
    if source_config.get('mqtt', {}).get('enabled', False):
        mqtt_config = source_config['mqtt']
        mqtt_adapter = MQTTStreamAdapter(
            broker=mqtt_config.get('broker', 'localhost'),
            port=mqtt_config.get('port', 1883),
            topic=mqtt_config.get('topic', 'bolt/data/+'),
            client_id=mqtt_config.get('client_id', 'stream_prediction'),
            username=mqtt_config.get('username'),
            password=mqtt_config.get('password'),
        )
        adapters.append(mqtt_adapter)

    return adapters
