"""
数据写入器

负责将采集到的数据写入到目标位置：
- sc_bolt_data (MySQL 数据库)
- /stream/ingest (流式预测接口)
- 两者同时写入
"""

import json
import time
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Callable
from queue import Queue, Empty
from loguru import logger
import httpx

from app.gateway.models import (
    DataPoint,
    DataSourceType,
    GatewayConfig,
)


BatchResultCallback = Callable[[List[DataPoint], List[DataPoint], bool], None]
# callback(success_points: List[DataPoint], failed_points: List[DataPoint], is_replay: bool)


class GatewayDataWriter:
    """
    网关数据写入器

    支持异步批量写入，提高写入性能。
    支持多种写入目标：数据库、流式接口。

    注意：write_point / write_batch 返回的是"入队成功"数量，
          不等于"真实写入成功"。真实写入结果通过 batch_result_callback
          异步通知给上层，由上层决定是否将失败数据回退到缓存。
    """

    def __init__(
        self,
        data_target: DataSourceType = DataSourceType.SC_BOLT_DATA,
        stream_ingest_url: str = "http://localhost:8000/stream/ingest",
        batch_size: int = 100,
        flush_interval: float = 1.0,
        batch_result_callback: Optional[BatchResultCallback] = None,
    ):
        """
        初始化数据写入器

        Args:
            data_target: 数据写入目标
            stream_ingest_url: stream/ingest 接口地址
            batch_size: 批量写入大小
            flush_interval: 刷新间隔（秒）
            batch_result_callback: 批次真实写入结果回调
                (success_points, failed_points, is_replay) -> None
        """
        self._data_target = data_target
        self._stream_ingest_url = stream_ingest_url
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._batch_result_callback = batch_result_callback

        self._write_queue: Queue = Queue()
        self._flush_thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._lock = threading.RLock()

        # 统计信息
        self._total_written: int = 0
        self._total_failed: int = 0
        self._total_enqueued: int = 0
        self._last_write_time: Optional[datetime] = None

        # HTTP 客户端
        self._http_client: Optional[httpx.Client] = None

        logger.info(
            f"数据写入器初始化完成，目标: {data_target.value}, "
            f"批量大小: {batch_size}, 刷新间隔: {flush_interval}s"
        )

    # ============ 启动/停止 ============

    def start(self) -> None:
        """启动数据写入器"""
        if self._is_running:
            logger.warning("数据写入器已在运行")
            return

        self._is_running = True
        self._http_client = httpx.Client(timeout=10.0)

        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name="gateway-data-writer",
        )
        self._flush_thread.start()

        logger.info("数据写入器已启动")

    def stop(self) -> None:
        """停止数据写入器"""
        if not self._is_running:
            return

        self._is_running = False

        # 刷新剩余数据
        self._flush_all()

        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
            self._flush_thread = None

        if self._http_client:
            self._http_client.close()
            self._http_client = None

        logger.info("数据写入器已停止")

    # ============ 结果回调 ============

    def set_batch_result_callback(self, callback: Optional[BatchResultCallback]) -> None:
        """
        设置批次结果回调

        Args:
            callback: 回调函数 (success_points, failed_points, is_replay) -> None
        """
        with self._lock:
            self._batch_result_callback = callback

    def _fire_batch_result(
        self,
        success_points: List[DataPoint],
        failed_points: List[DataPoint],
        is_replay: bool,
    ) -> None:
        """触发批次结果回调"""
        try:
            cb = self._batch_result_callback
            if cb is not None:
                cb(success_points, failed_points, is_replay)
        except Exception as e:
            logger.error(f"批次结果回调执行异常: {e}")

    # ============ 数据写入 ============

    def write_point(self, point: DataPoint) -> bool:
        """
        写入单个数据点（异步）

        Args:
            point: 数据点

        Returns:
            bool: 是否成功加入队列
        """
        if not self._is_running:
            logger.warning("数据写入器未启动")
            return False

        try:
            self._write_queue.put(point)
            with self._lock:
                self._total_enqueued += 1
            return True
        except Exception as e:
            logger.error(f"数据点加入写入队列失败: {e}")
            return False

    def write_batch(self, points: List[DataPoint]) -> int:
        """
        批量写入数据点（异步）

        注意：此方法返回的是入队数量，不是真实写入成功数量。
        真实写入结果请通过 batch_result_callback 异步获取。

        Args:
            points: 数据点列表

        Returns:
            int: 成功加入队列的数量
        """
        if not self._is_running:
            logger.warning("数据写入器未启动")
            return 0

        count = 0
        for point in points:
            if self.write_point(point):
                count += 1
        return count

    def write_batch_sync(
        self, points: List[DataPoint], is_replay: bool = True
    ) -> Tuple[int, int]:
        """
        批量同步写入（阻塞）

        续传等必须知道真实结果的场景使用。
        不走异步队列，直接执行写入逻辑并返回真实结果。

        Args:
            points: 数据点列表
            is_replay: 是否为续传场景（影响结果回调中的标记）

        Returns:
            (success_count, failed_count)
        """
        if not points:
            return 0, 0

        success_points, failed_points = self._execute_batch_write(points)

        # 更新统计
        with self._lock:
            self._total_written += len(success_points)
            self._total_failed += len(failed_points)
            self._last_write_time = datetime.now()

        # 触发回调
        self._fire_batch_result(
            success_points=success_points,
            failed_points=failed_points,
            is_replay=is_replay,
        )

        if len(success_points) > 0:
            logger.debug(
                f"同步写入完成: 成功 {len(success_points)}, "
                f"失败 {len(failed_points)} (replay={is_replay})"
            )

        return len(success_points), len(failed_points)

    # ============ 刷新逻辑 ============

    def _flush_loop(self) -> None:
        """刷新循环"""
        last_flush_time = time.time()

        while self._is_running:
            try:
                now = time.time()
                queue_size = self._write_queue.qsize()

                # 达到批量大小或时间间隔时刷新
                if queue_size >= self._batch_size or (now - last_flush_time) >= self._flush_interval:
                    if queue_size > 0:
                        self._flush_batch(min(queue_size, self._batch_size))
                        last_flush_time = now

                # 短暂休眠
                time.sleep(min(self._flush_interval / 10, 0.1))

            except Exception as e:
                logger.error(f"数据写入刷新循环异常: {e}")
                time.sleep(1.0)

    def _flush_batch(self, count: int) -> None:
        """
        刷新一批数据（异步刷新线程中调用）

        Args:
            count: 刷新数量
        """
        points: List[DataPoint] = []
        for _ in range(count):
            try:
                point = self._write_queue.get_nowait()
                points.append(point)
            except Empty:
                break

        if not points:
            return

        success_points, failed_points = self._execute_batch_write(points)

        # 更新统计
        with self._lock:
            self._total_written += len(success_points)
            self._total_failed += len(failed_points)
            self._last_write_time = datetime.now()

        # 触发结果回调（实时采集场景：is_replay=False）
        self._fire_batch_result(
            success_points=success_points,
            failed_points=failed_points,
            is_replay=False,
        )

        if failed_points:
            logger.warning(
                f"批次写入: 成功 {len(success_points)}/{len(points)}, "
                f"失败 {len(failed_points)}，将通过回调通知上层回退缓存"
            )

    def _execute_batch_write(
        self, points: List[DataPoint]
    ) -> Tuple[List[DataPoint], List[DataPoint]]:
        """
        真正执行一次批量写入，返回成功/失败的点

        对于 BOTH 模式：两个目标都失败才算失败；
        至少一个目标成功就算该点写入成功。

        Args:
            points: 待写入数据点

        Returns:
            (success_points, failed_points)
        """
        if not points:
            return [], []

        db_success = False
        stream_success = False

        if self._data_target in (DataSourceType.SC_BOLT_DATA, DataSourceType.BOTH):
            db_success = self._write_to_database(points)

        if self._data_target in (DataSourceType.STREAM_INGEST, DataSourceType.BOTH):
            stream_success = self._write_to_stream_ingest(points)

        # 判断整体结果
        if self._data_target == DataSourceType.SC_BOLT_DATA:
            overall_success = db_success
        elif self._data_target == DataSourceType.STREAM_INGEST:
            overall_success = stream_success
        elif self._data_target == DataSourceType.BOTH:
            # BOTH 模式：至少一个成功就视为成功
            overall_success = db_success or stream_success
        else:
            overall_success = False

        if overall_success:
            return points, []
        else:
            return [], points

    def _flush_all(self) -> None:
        """刷新所有数据"""
        try:
            while not self._write_queue.empty():
                self._flush_batch(min(self._batch_size, self._write_queue.qsize()))
        except Exception as e:
            logger.error(f"刷新所有数据失败: {e}")

    # ============ 数据库写入 ============

    def _write_to_database(self, points: List[DataPoint]) -> bool:
        """
        写入到 sc_bolt_data 表

        Args:
            points: 数据点列表

        Returns:
            bool: 是否成功
        """
        try:
            from app.utils.database import get_db, BoltData
            from sqlalchemy import text

            with get_db() as db:
                if db is None:
                    logger.warning("数据库连接不可用")
                    return False

                # 按 sensor_id 分组，批量插入
                bolt_data_list = []
                for point in points:
                    try:
                        sensor_id = int(point.sensor_id) if str(point.sensor_id).isdigit() else 0
                    except (ValueError, TypeError):
                        sensor_id = 0

                    bolt_data = BoltData(
                        sensor_id=sensor_id,
                        ptf=point.value,
                        data_quality=point.quality,
                        create_time=point.timestamp,
                    )
                    bolt_data_list.append(bolt_data)

                if bolt_data_list:
                    db.bulk_save_objects(bolt_data_list)
                    db.commit()
                    logger.debug(f"数据库写入成功: {len(bolt_data_list)} 条")
                    return True

                return False

        except Exception as e:
            logger.error(f"数据库写入失败: {e}")
            return False

    # ============ 流式接口写入 ============

    def _write_to_stream_ingest(self, points: List[DataPoint]) -> bool:
        """
        写入到 /stream/ingest 接口

        Args:
            points: 数据点列表

        Returns:
            bool: 是否成功
        """
        if self._http_client is None:
            return False

        try:
            # 按 sensor_id 分组
            sensor_data: Dict[str, Dict[str, Any]] = {}
            for point in points:
                sensor_id = point.sensor_id
                if sensor_id not in sensor_data:
                    sensor_data[sensor_id] = {
                        'values': [],
                        'timestamps': [],
                    }
                sensor_data[sensor_id]['values'].append(point.value)
                sensor_data[sensor_id]['timestamps'].append(
                    point.timestamp.isoformat()
                )

            # 逐个传感器发送（兼容现有接口）
            all_success = True
            for sensor_id, data in sensor_data.items():
                try:
                    payload = {
                        'node_type': 'bolt',
                        'node_id': str(sensor_id),
                        'values': data['values'],
                        'timestamps': data['timestamps'],
                        'metadata': {
                            'source': 'gateway',
                            'unit': points[0].unit if points else '',
                        },
                    }

                    response = self._http_client.post(
                        self._stream_ingest_url,
                        json=payload,
                    )

                    if response.status_code != 200:
                        logger.warning(
                            f"stream/ingest 返回非200: {response.status_code}, "
                            f"sensor={sensor_id}"
                        )
                        all_success = False

                except Exception as e:
                    logger.error(f"stream/ingest 写入失败 sensor={sensor_id}: {e}")
                    all_success = False

            if all_success:
                logger.debug(f"stream/ingest 写入成功: {len(points)} 条")
            return all_success

        except Exception as e:
            logger.error(f"stream/ingest 写入异常: {e}")
            return False

    # ============ 配置更新 ============

    def update_config(self, config: GatewayConfig) -> None:
        """
        更新配置

        Args:
            config: 网关配置
        """
        with self._lock:
            self._data_target = config.data_target
            self._stream_ingest_url = config.stream_ingest_url

        logger.info(
            f"数据写入器配置已更新: 目标={config.data_target.value}, "
            f"URL={config.stream_ingest_url}"
        )

    # ============ 统计信息 ============

    @property
    def queue_size(self) -> int:
        """队列大小"""
        return self._write_queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计字典
        """
        with self._lock:
            return {
                'is_running': self._is_running,
                'queue_size': self._write_queue.qsize(),
                'total_enqueued': self._total_enqueued,
                'total_written': self._total_written,
                'total_failed': self._total_failed,
                'last_write_time': self._last_write_time.isoformat() if self._last_write_time else None,
                'data_target': self._data_target.value,
                'batch_size': self._batch_size,
                'flush_interval': self._flush_interval,
            }

    def flush_immediately(self) -> int:
        """
        立即刷新所有数据

        Returns:
            刷新的数据条数
        """
        count = self._write_queue.qsize()
        if count > 0:
            self._flush_all()
        return count
