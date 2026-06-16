"""
流式预测引擎核心模块

整合滑动窗口、背压控制、事件发布和流适配器，
实现完整的实时流式预测能力。

主要组件:
- StreamPredictionMode: 预测模式枚举
- StreamPredictionEngine: 流式预测引擎核心
"""

import time
import threading
import numpy as np
from collections import deque
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger

from app.streaming.window_manager import (
    SlidingWindowManager,
    WindowData,
    create_window_manager,
)
from app.streaming.backpressure import (
    StreamConcurrencyManager,
    create_backpressure_controller_from_config,
)
from app.streaming.event_publisher import (
    EventPublisher,
    StreamEvent,
    create_event_publisher_from_config,
)
from app.streaming.stream_adapters import (
    StreamAdapter,
    StreamMessage,
    HTTPStreamAdapter,
    create_stream_adapters_from_config,
)
from app.services.prediction import PredictionOrchestrator
from app.utils.config import config
from app.core.prometheus import metrics


class StreamPredictionMode(str, Enum):
    """
    预测模式

    - BATCH: 批处理模式
    - STREAM: 流式模式
    """
    BATCH = "batch"
    STREAM = "stream"


@dataclass
class StreamEngineStats:
    """
    流引擎统计信息

    Attributes:
        is_running: 是否运行中
        mode: 当前模式
        active_streams: 活跃流数
        total_predictions: 总预测次数
        status_changes: 状态变更次数
        window_manager_stats: 窗口管理器统计
        backpressure_stats: 背压统计
        event_stats: 事件统计
        adapter_stats: 适配器统计
    """
    is_running: bool
    mode: str
    active_streams: int
    total_predictions: int
    status_changes: int
    window_manager_stats: Dict[str, Any]
    backpressure_stats: Dict[str, Any]
    event_stats: Dict[str, Any]
    adapter_stats: List[Dict[str, Any]]


class StreamPredictionEngine:
    """
    流式预测引擎

    整合所有流式预测组件，提供统一的实时预测能力。

    核心特性:
    - 支持 Kafka/MQTT/HTTP 多种流输入源
    - Per-bolt 滑动窗口（内存/Redis）
    - 窗口满触发推理
    - 状态变更事件发布
    - 背压与限流控制
    - 与批处理模式共存
    """

    def __init__(
        self,
        prediction_mode: StreamPredictionMode = StreamPredictionMode.BATCH,
        window_manager: Optional[SlidingWindowManager] = None,
        backpressure_manager: Optional[StreamConcurrencyManager] = None,
        event_publisher: Optional[EventPublisher] = None,
        stream_adapters: Optional[List[StreamAdapter]] = None,
        prediction_orchestrator: Optional[PredictionOrchestrator] = None,
    ):
        """
        初始化流式预测引擎

        Args:
            prediction_mode: 预测模式
            window_manager: 滑动窗口管理器
            backpressure_manager: 背压控制器
            event_publisher: 事件发布器
            stream_adapters: 流适配器列表
            prediction_orchestrator: 预测编排器
        """
        self._prediction_mode = prediction_mode
        self._is_running = False
        self._lock = threading.Lock()
        self._total_predictions = 0
        self._status_changes = 0
        self._active_streams = set()

        # QPS统计 - 使用滑动窗口计算最近60秒的QPS
        self._ingest_timestamps: deque = deque(maxlen=10000)
        self._ingest_lock = threading.Lock()
        self._current_qps = 0.0
        self._component_name = "stream-consumer"

        # 初始化组件
        self._init_components(
            window_manager,
            backpressure_manager,
            event_publisher,
            stream_adapters,
            prediction_orchestrator,
        )

        # 注册回调
        self._register_callbacks()

        logger.info(
            f"流式预测引擎初始化完成，模式: {prediction_mode.value}"
        )

    def _init_components(
        self,
        window_manager: Optional[SlidingWindowManager],
        backpressure_manager: Optional[StreamConcurrencyManager],
        event_publisher: Optional[EventPublisher],
        stream_adapters: Optional[List[StreamAdapter]],
        prediction_orchestrator: Optional[PredictionOrchestrator],
    ) -> None:
        """
        初始化组件

        Args:
            window_manager: 滑动窗口管理器
            backpressure_manager: 背压控制器
            event_publisher: 事件发布器
            stream_adapters: 流适配器列表
            prediction_orchestrator: 预测编排器
        """
        # 滑动窗口管理器
        if window_manager is not None:
            self.window_manager = window_manager
        else:
            stream_config = config.get('stream_prediction', {})
            window_config = stream_config.get('window', {})
            self.window_manager = create_window_manager(
                storage_type=window_config.get('storage_type', 'memory'),
                window_size=window_config.get('size', 100),
                ttl_seconds=window_config.get('ttl_seconds', 3600),
                redis_url=window_config.get('redis_url', 'redis://localhost:6379/0'),
            )

        # 背压控制器
        if backpressure_manager is not None:
            self.backpressure_manager = backpressure_manager
        else:
            self.backpressure_manager = create_backpressure_controller_from_config()

        # 事件发布器
        if event_publisher is not None:
            self.event_publisher = event_publisher
        else:
            self.event_publisher = create_event_publisher_from_config()

        # 流适配器
        if stream_adapters is not None:
            self.stream_adapters = stream_adapters
        else:
            self.stream_adapters = create_stream_adapters_from_config()

        # 预测编排器
        if prediction_orchestrator is not None:
            self.prediction_orchestrator = prediction_orchestrator
        else:
            self.prediction_orchestrator = PredictionOrchestrator()

    def _register_callbacks(self) -> None:
        """注册回调函数"""
        # 注册窗口满回调
        self.window_manager.register_callback(self._on_window_full)

        # 注册流适配器消息处理器
        for adapter in self.stream_adapters:
            adapter.register_message_handler(self._on_stream_message)

        # 注册背压事件回调
        self.backpressure_manager.backpressure.register_callback(
            'reject', self._on_stream_rejected
        )
        self.backpressure_manager.backpressure.register_callback(
            'backpressure', self._on_backpressure
        )
        self.backpressure_manager.backpressure.register_callback(
            'recover', self._on_backpressure_recover
        )

    # ============ 公共接口 ============

    @property
    def prediction_mode(self) -> StreamPredictionMode:
        """获取当前预测模式"""
        return self._prediction_mode

    @prediction_mode.setter
    def prediction_mode(self, mode: StreamPredictionMode) -> None:
        """
        设置预测模式

        Args:
            mode: 预测模式
        """
        with self._lock:
            old_mode = self._prediction_mode
            self._prediction_mode = mode
            logger.info(f"预测模式切换: {old_mode.value} -> {mode.value}")

    def set_prediction_mode(self, mode: str) -> bool:
        """
        设置预测模式（字符串形式）

        Args:
            mode: 模式名称 (batch / stream)

        Returns:
            bool: 是否设置成功
        """
        try:
            mode_enum = StreamPredictionMode(mode)
            self.prediction_mode = mode_enum
            return True
        except ValueError:
            logger.error(f"无效的预测模式: {mode}")
            return False

    def start(self) -> None:
        """启动流式预测引擎"""
        if self._is_running:
            logger.warning("流式预测引擎已在运行中")
            return

        with self._lock:
            self._is_running = True

            # 启动事件发布器
            try:
                self.event_publisher.start()
            except Exception as e:
                logger.error(f"启动事件发布器失败: {e}")

            # 启动流适配器
            for adapter in self.stream_adapters:
                try:
                    adapter.start()
                except Exception as e:
                    logger.error(f"启动流适配器 {adapter.name} 失败: {e}")

            # 启动后台清理任务
            self._start_cleanup_thread()

            logger.info("流式预测引擎已启动")

    def stop(self) -> None:
        """停止流式预测引擎"""
        if not self._is_running:
            logger.warning("流式预测引擎未在运行")
            return

        with self._lock:
            self._is_running = False

            # 停止流适配器
            for adapter in self.stream_adapters:
                try:
                    adapter.stop()
                except Exception as e:
                    logger.error(f"停止流适配器 {adapter.name} 失败: {e}")

            # 停止事件发布器
            try:
                self.event_publisher.stop()
            except Exception as e:
                logger.error(f"停止事件发布器失败: {e}")

            logger.info("流式预测引擎已停止")

    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._is_running

    # ============ 消息处理 ============

    def ingest_message(self, message_data: Dict[str, Any]) -> bool:
        """
        注入消息（通过HTTP接口调用）

        Args:
            message_data: 消息数据

        Returns:
            bool: 是否处理成功
        """
        if not self._is_running:
            logger.warning("流式预测引擎未启动，消息被丢弃")
            return False

        if self._prediction_mode != StreamPredictionMode.STREAM:
            logger.debug(
                f"当前为批处理模式，跳过流式处理: {self._prediction_mode.value}"
            )
            return False

        # 找到 HTTP 适配器并处理
        for adapter in self.stream_adapters:
            if isinstance(adapter, HTTPStreamAdapter):
                return adapter.handle_message(message_data)

        return False

    def ingest_data_point(
        self,
        node_type: str,
        node_id: str,
        value: float,
        timestamp: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        注入单个数据点

        Args:
            node_type: 节点类型
            node_id: 节点ID
            value: 预紧力值
            timestamp: 时间戳
            metadata: 元数据

        Returns:
            bool: 是否处理成功
        """
        message_data = {
            'node_type': node_type,
            'node_id': node_id,
            'value': value,
            'timestamp': timestamp,
            'metadata': metadata or {},
        }
        return self.ingest_message(message_data)

    def ingest_batch(
        self,
        node_type: str,
        node_id: str,
        values: List[float],
        timestamps: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        注入批量数据

        Args:
            node_type: 节点类型
            node_id: 节点ID
            values: 预紧力值列表
            timestamps: 时间戳列表
            metadata: 元数据

        Returns:
            bool: 是否处理成功
        """
        message_data = {
            'node_type': node_type,
            'node_id': node_id,
            'values': values,
            'timestamps': timestamps,
            'metadata': metadata or {},
        }
        return self.ingest_message(message_data)

    # ============ 回调处理 ============

    def _on_stream_message(self, message: StreamMessage) -> None:
        """
        处理流消息

        Args:
            message: 流消息
        """
        if not self._is_running:
            return

        if self._prediction_mode != StreamPredictionMode.STREAM:
            return

        try:
            stream_id = message.stream_id

            # 背压检查
            if stream_id not in self._active_streams:
                if not self.backpressure_manager.try_register_stream(stream_id):
                    logger.warning(
                        f"流被拒绝（背压）: {stream_id}"
                    )
                    return
                self._active_streams.add(stream_id)

            # 限流检查
            if not self.backpressure_manager.try_accept_message(stream_id):
                logger.debug(f"消息被限流: {stream_id}")
                return

            # 记录数据摄入QPS指标
            data_count = len(message.values)
            self._record_ingest(node_type=message.node_type, count=data_count)
            
            # 更新窗口填充度指标
            window = self.window_manager.get_window(message.node_id)
            if window:
                fill_ratio = min(len(window.values) / window.window_size, 1.0)
                metrics.update_window_fill_ratio(
                    component=self._component_name,
                    bolt_id=message.node_id,
                    ratio=fill_ratio
                )
            
            # 添加到滑动窗口
            if message.is_batch():
                is_full = self.window_manager.add_batch(
                    bolt_id=message.node_id,
                    values=message.values,
                    timestamps=message.timestamps,
                )
            else:
                is_full = self.window_manager.add_point(
                    bolt_id=message.node_id,
                    value=message.values[0],
                    timestamp=message.timestamps[0],
                )

            logger.debug(
                f"消息处理完成: {stream_id}, "
                f"batch_size={len(message.values)}, "
                f"window_full={is_full}, "
                f"current_qps={self._current_qps:.2f}"
            )

        except Exception as e:
            logger.error(f"处理流消息失败: {e}")

    def _on_window_full(self, bolt_id: str, window_data: WindowData) -> None:
        """
        窗口满回调，触发预测

        Args:
            bolt_id: 螺栓ID
            window_data: 窗口数据
        """
        if not self._is_running:
            return

        try:
            # 执行预测
            result = self._run_prediction(bolt_id, window_data)

            if result:
                self._total_predictions += 1

                # 检查状态变更
                old_status = window_data.last_prediction_status
                new_status = result.get('status_code', 0)

                if old_status != new_status:
                    self._status_changes += 1
                    self.window_manager.update_prediction_status(
                        bolt_id, new_status
                    )

                    # 发布状态变更事件
                    self.event_publisher.publish_status_change(
                        node_type='bolt',
                        node_id=bolt_id,
                        old_status=old_status,
                        new_status=new_status,
                        prediction_data=result,
                        metadata={
                            'window_size': window_data.window_size,
                            'prediction_count': window_data.prediction_count + 1,
                        },
                    )
                else:
                    # 发布普通预测事件
                    self.event_publisher.publish_prediction(
                        node_type='bolt',
                        node_id=bolt_id,
                        prediction_data=result,
                    )

                logger.info(
                    f"流式预测完成: bolt={bolt_id}, "
                    f"status={result.get('status', 'unknown')}, "
                    f"confidence={result.get('confidence', 0):.3f}"
                )

        except Exception as e:
            logger.error(f"窗口满预测失败 bolt={bolt_id}: {e}")

    def _run_prediction(
        self, bolt_id: str, window_data: WindowData
    ) -> Optional[Dict[str, Any]]:
        """
        执行预测

        Args:
            bolt_id: 螺栓ID
            window_data: 窗口数据

        Returns:
            预测结果字典
        """
        try:
            values, timestamps = window_data.get_window()
            data = np.array(values).reshape(-1, 1)

            # 调用预测编排器
            result = self.prediction_orchestrator.predict_bolt(
                bolt_id=bolt_id,
                data=data,
                timestamps=timestamps,
                save_to_db=False,  # 流式预测不直接保存到DB，由事件驱动
            )

            return result

        except Exception as e:
            logger.error(f"执行预测失败 bolt={bolt_id}: {e}")
            return None

    def _on_stream_rejected(self, stream_id: str, reason: str) -> None:
        """
        流被拒绝回调

        Args:
            stream_id: 流ID
            reason: 拒绝原因
        """
        logger.warning(f"流被拒绝: {stream_id}, 原因: {reason}")

    def _on_backpressure(self, queue_size: int, active_streams: int) -> None:
        """
        背压触发回调

        Args:
            queue_size: 队列大小
            active_streams: 活跃流数
        """
        logger.warning(
            f"背压触发: queue_size={queue_size}, active_streams={active_streams}"
        )

    def _on_backpressure_recover(self, queue_size: int) -> None:
        """
        背压恢复回调

        Args:
            queue_size: 队列大小
        """
        logger.info(f"背压恢复: queue_size={queue_size}")

    # ============ 后台任务 ============

    def _start_cleanup_thread(self) -> None:
        """启动清理线程"""
        cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="stream-cleanup",
        )
        cleanup_thread.start()

    def _record_ingest(self, node_type: str, count: int = 1) -> None:
        """记录数据摄入并更新QPS指标"""
        now = time.time()
        with self._ingest_lock:
            for _ in range(count):
                self._ingest_timestamps.append(now)
        
        metrics.record_stream_ingest(
            component=self._component_name,
            node_type=node_type,
            success=True,
            count=count
        )
        
        self._update_qps_metric(node_type)
    
    def _update_qps_metric(self, node_type: str) -> None:
        """更新QPS指标 - 计算最近60秒的QPS"""
        now = time.time()
        cutoff = now - 60.0
        
        with self._ingest_lock:
            recent_count = sum(1 for ts in self._ingest_timestamps if ts >= cutoff)
        
        qps = recent_count / 60.0
        self._current_qps = qps
        
        metrics.update_stream_qps(
            component=self._component_name,
            node_type=node_type,
            qps=qps
        )
        
        metrics.update_stream_active_count(
            component=self._component_name,
            count=len(self._active_streams)
        )
    
    def _cleanup_loop(self) -> None:
        """清理循环"""
        while self._is_running:
            try:
                # 清理过期窗口
                self.window_manager.cleanup_expired()

                # 清理空闲流
                active_bolts = set(self.window_manager.list_bolts())
                streams_to_remove = [
                    s for s in self._active_streams
                    if s.split(':')[-1] not in active_bolts
                ]
                for stream_id in streams_to_remove:
                    self.backpressure_manager.unregister_stream(stream_id)
                    self._active_streams.discard(stream_id)
                
                # 更新活跃流数指标
                metrics.update_stream_active_count(
                    component=self._component_name,
                    count=len(self._active_streams)
                )
                
                # 定期更新QPS指标（即使没有新数据）
                if len(self._ingest_timestamps) > 0:
                    self._update_qps_metric("bolt")

                # 每30秒执行一次
                time.sleep(30)
            except Exception as e:
                logger.error(f"清理任务异常: {e}")
                time.sleep(30)

    # ============ 查询接口 ============

    def get_window_status(self, bolt_id: str) -> Optional[Dict[str, Any]]:
        """
        获取窗口状态

        Args:
            bolt_id: 螺栓ID

        Returns:
            窗口状态字典
        """
        window = self.window_manager.get_window(bolt_id)
        if window:
            return {
                'bolt_id': window.bolt_id,
                'window_size': window.window_size,
                'current_size': len(window.values),
                'is_full': window.is_full(),
                'last_updated': window.last_updated,
                'last_prediction_status': window.last_prediction_status,
                'prediction_count': window.prediction_count,
                'first_timestamp': window.timestamps[0] if window.timestamps else None,
                'last_timestamp': window.timestamps[-1] if window.timestamps else None,
            }
        return None

    def get_stats(self) -> StreamEngineStats:
        """
        获取引擎统计信息

        Returns:
            StreamEngineStats
        """
        window_bolts = self.window_manager.list_bolts()

        return StreamEngineStats(
            is_running=self._is_running,
            mode=self._prediction_mode.value,
            active_streams=len(self._active_streams),
            total_predictions=self._total_predictions,
            status_changes=self._status_changes,
            window_manager_stats={
                'active_bolts': len(window_bolts),
                'bolt_ids': window_bolts[:10],  # 只返回前10个
            },
            backpressure_stats=self.backpressure_manager.get_stats(),
            event_stats={
                'event_count': self.event_publisher.get_event_count(),
            },
            adapter_stats=[
                adapter.get_stats() for adapter in self.stream_adapters
            ],
            qps_stats={
                'current_qps': self._current_qps,
                'recent_ingest_count': len(self._ingest_timestamps),
            },
        )

    def get_stats_dict(self) -> Dict[str, Any]:
        """
        获取引擎统计信息（字典形式）

        Returns:
            统计信息字典
        """
        stats = self.get_stats()
        return {
            'is_running': stats.is_running,
            'mode': stats.mode,
            'active_streams': stats.active_streams,
            'total_predictions': stats.total_predictions,
            'status_changes': stats.status_changes,
            'window_manager': stats.window_manager_stats,
            'backpressure': stats.backpressure_stats,
            'events': stats.event_stats,
            'adapters': stats.adapter_stats,
        }

    # ============ 管理接口 ============

    def clear_window(self, bolt_id: str) -> bool:
        """
        清空指定螺栓的窗口

        Args:
            bolt_id: 螺栓ID

        Returns:
            bool
        """
        try:
            self.window_manager.clear_window(bolt_id)
            logger.info(f"已清空窗口: {bolt_id}")
            return True
        except Exception as e:
            logger.error(f"清空窗口失败 {bolt_id}: {e}")
            return False

    def clear_all_windows(self) -> bool:
        """
        清空所有窗口

        Returns:
            bool
        """
        try:
            self.window_manager.clear_all()
            logger.info("已清空所有窗口")
            return True
        except Exception as e:
            logger.error(f"清空所有窗口失败: {e}")
            return False

    def set_window_size(self, size: int) -> bool:
        """
        设置窗口大小（注意：仅对新创建的窗口生效）

        Args:
            size: 窗口大小

        Returns:
            bool
        """
        try:
            self.window_manager.window_size = size
            logger.info(f"窗口大小已设置: {size}")
            return True
        except Exception as e:
            logger.error(f"设置窗口大小失败: {e}")
            return False

    def set_max_concurrent_streams(self, max_streams: int) -> bool:
        """
        设置最大并发流数

        Args:
            max_streams: 最大并发流数

        Returns:
            bool
        """
        try:
            self.backpressure_manager.set_max_concurrent_streams(max_streams)
            logger.info(f"最大并发流数已设置: {max_streams}")
            return True
        except Exception as e:
            logger.error(f"设置最大并发流数失败: {e}")
            return False


# 全局引擎实例
_stream_engine: Optional[StreamPredictionEngine] = None


def get_stream_engine() -> StreamPredictionEngine:
    """
    获取流式预测引擎实例（单例）

    Returns:
        StreamPredictionEngine
    """
    global _stream_engine
    if _stream_engine is None:
        _stream_engine = StreamPredictionEngine()
    return _stream_engine
