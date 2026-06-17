"""
采集器基类

定义所有协议采集器的公共接口和基础功能。
"""

import time
import threading
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any
from abc import ABC, abstractmethod
from loguru import logger

from app.gateway.models import (
    DeviceConfig,
    PointConfig,
    DataPoint,
    DeviceStatus,
    PointStatus,
)


class BaseCollector(ABC):
    """
    采集器基类

    定义协议采集器的公共接口和基础功能，
    包括连接管理、点位采集调度、数据回调等。
    """

    def __init__(
        self,
        device_config: DeviceConfig,
        data_callback: Optional[Callable[[List[DataPoint]], None]] = None,
        status_callback: Optional[Callable[[str, DeviceStatus, str], None]] = None,
    ):
        """
        初始化采集器

        Args:
            device_config: 设备配置
            data_callback: 数据回调函数
            status_callback: 状态回调函数 (device_id, status, error_msg)
        """
        self._config = device_config
        self._data_callback = data_callback
        self._status_callback = status_callback

        self._is_running: bool = False
        self._is_connected: bool = False
        self._lock = threading.Lock()

        # 采集线程
        self._collect_thread: Optional[threading.Thread] = None

        # 点位调度
        self._point_schedules: Dict[str, Dict[str, Any]] = {}
        self._last_sample_times: Dict[str, float] = {}

        # 统计
        self._total_samples: int = 0
        self._failed_samples: int = 0
        self._consecutive_errors: int = 0

        logger.info(
            f"采集器初始化: {device_config.device_id}, "
            f"协议: {device_config.protocol.value}"
        )

    # ============ 抽象方法 ============

    @abstractmethod
    def connect(self) -> bool:
        """
        连接设备

        Returns:
            bool: 是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开设备连接"""
        pass

    @abstractmethod
    def read_point(self, point: PointConfig) -> Optional[Any]:
        """
        读取单个点位

        Args:
            point: 点位配置

        Returns:
            原始值，失败返回 None
        """
        pass

    @abstractmethod
    def read_batch(self, points: List[PointConfig]) -> Dict[str, Any]:
        """
        批量读取点位

        Args:
            points: 点位配置列表

        Returns:
            {point_id: value} 字典，失败的点位不包含在结果中
        """
        pass

    # ============ 生命周期 ============

    def start(self) -> bool:
        """
        启动采集器

        Returns:
            bool: 是否启动成功
        """
        if self._is_running:
            logger.warning(f"采集器已在运行: {self._config.device_id}")
            return True

        try:
            # 连接设备
            if not self.connect():
                logger.error(f"采集器连接失败: {self._config.device_id}")
                self._update_status(DeviceStatus.ERROR, "连接失败")
                return False

            # 初始化点位调度
            self._init_point_schedules()

            # 启动采集线程
            self._is_running = True
            self._collect_thread = threading.Thread(
                target=self._collect_loop,
                daemon=True,
                name=f"collector-{self._config.device_id}",
            )
            self._collect_thread.start()

            self._update_status(DeviceStatus.CONNECTED)
            logger.info(f"采集器已启动: {self._config.device_id}")
            return True

        except Exception as e:
            logger.error(f"启动采集器失败 {self._config.device_id}: {e}")
            self._update_status(DeviceStatus.ERROR, str(e))
            return False

    def stop(self) -> None:
        """停止采集器"""
        if not self._is_running:
            return

        self._is_running = False

        if self._collect_thread:
            self._collect_thread.join(timeout=5.0)
            self._collect_thread = None

        self.disconnect()
        self._update_status(DeviceStatus.DISCONNECTED)
        logger.info(f"采集器已停止: {self._config.device_id}")

    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._is_running

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected

    # ============ 采集调度 ============

    def _init_point_schedules(self) -> None:
        """初始化点位调度表"""
        enabled_points = self._config.get_enabled_points()
        now = time.time()

        for point in enabled_points:
            self._point_schedules[point.point_id] = {
                'point': point,
                'next_sample_time': now,
                'period': point.sampling_period,
            }
            self._last_sample_times[point.point_id] = 0.0

        logger.debug(
            f"点位调度初始化完成: {self._config.device_id}, "
            f"点位数量: {len(self._point_schedules)}"
        )

    def _collect_loop(self) -> None:
        """采集循环"""
        while self._is_running:
            try:
                now = time.time()
                points_to_sample: List[PointConfig] = []

                # 找出需要采样的点位
                for point_id, schedule in self._point_schedules.items():
                    if now >= schedule['next_sample_time']:
                        points_to_sample.append(schedule['point'])

                if points_to_sample:
                    # 批量采集
                    data_points = self._sample_points(points_to_sample)

                    if data_points and self._data_callback:
                        try:
                            self._data_callback(data_points)
                        except Exception as e:
                            logger.error(f"数据回调执行失败: {e}")

                    # 更新下次采样时间
                    for point in points_to_sample:
                        schedule = self._point_schedules.get(point.point_id)
                        if schedule:
                            schedule['next_sample_time'] = (
                                now + point.sampling_period
                            )

                # 短暂休眠，避免CPU占用过高
                sleep_time = self._get_min_sleep_time()
                if sleep_time > 0:
                    time.sleep(min(sleep_time, 0.1))
                else:
                    time.sleep(0.01)

            except Exception as e:
                logger.error(f"采集循环异常 {self._config.device_id}: {e}")
                self._consecutive_errors += 1
                if self._consecutive_errors >= 10:
                    self._update_status(
                        DeviceStatus.ERROR,
                        f"连续错误 {self._consecutive_errors} 次: {e}"
                    )
                time.sleep(1.0)

    def _get_min_sleep_time(self) -> float:
        """
        获取最小休眠时间

        Returns:
            到下一次采样的最小时间（秒）
        """
        now = time.time()
        min_time = float('inf')

        for schedule in self._point_schedules.values():
            time_until_next = schedule['next_sample_time'] - now
            if time_until_next < min_time:
                min_time = time_until_next

        return max(0, min_time)

    def _sample_points(self, points: List[PointConfig]) -> List[DataPoint]:
        """
        采样点位

        Args:
            points: 点位列表

        Returns:
            数据点列表
        """
        data_points: List[DataPoint] = []
        timestamp = datetime.now()

        try:
            # 尝试批量读取
            results = self.read_batch(points)

            for point in points:
                raw_value = results.get(point.point_id)
                if raw_value is not None:
                    value = point.convert_value(raw_value)
                    data_point = DataPoint(
                        device_id=self._config.device_id,
                        point_id=point.point_id,
                        sensor_id=point.sensor_id,
                        value=value,
                        raw_value=raw_value,
                        timestamp=timestamp,
                        quality="good",
                        unit=point.unit,
                    )
                    data_points.append(data_point)

                    self._total_samples += 1
                    self._consecutive_errors = max(0, self._consecutive_errors - 1)
                else:
                    self._failed_samples += 1

        except Exception as e:
            logger.warning(f"批量采集失败，改用单点采集: {e}")
            # 回退到单点采集
            for point in points:
                try:
                    raw_value = self.read_point(point)
                    if raw_value is not None:
                        value = point.convert_value(raw_value)
                        data_point = DataPoint(
                            device_id=self._config.device_id,
                            point_id=point.point_id,
                            sensor_id=point.sensor_id,
                            value=value,
                            raw_value=raw_value,
                            timestamp=timestamp,
                            quality="good",
                            unit=point.unit,
                        )
                        data_points.append(data_point)
                        self._total_samples += 1
                    else:
                        self._failed_samples += 1
                except Exception as e2:
                    logger.warning(f"单点采集失败 {point.point_id}: {e2}")
                    self._failed_samples += 1

        return data_points

    # ============ 状态管理 ============

    def _update_status(self, status: DeviceStatus, error: str = "") -> None:
        """
        更新设备状态

        Args:
            status: 设备状态
            error: 错误信息
        """
        if status == DeviceStatus.CONNECTED:
            self._is_connected = True
        elif status in (DeviceStatus.DISCONNECTED, DeviceStatus.ERROR):
            self._is_connected = False

        if self._status_callback:
            try:
                self._status_callback(
                    self._config.device_id,
                    status,
                    error,
                )
            except Exception as e:
                logger.error(f"状态回调执行失败: {e}")

    # ============ 配置更新 ============

    def update_config(self, config: DeviceConfig) -> None:
        """
        更新设备配置

        Args:
            config: 新的设备配置
        """
        with self._lock:
            self._config = config
            self._init_point_schedules()
            logger.info(f"设备配置已更新: {config.device_id}")

    # ============ 统计信息 ============

    def get_stats(self) -> Dict[str, Any]:
        """
        获取采集器统计信息

        Returns:
            统计字典
        """
        return {
            'device_id': self._config.device_id,
            'is_running': self._is_running,
            'is_connected': self._is_connected,
            'total_points': len(self._config.points),
            'enabled_points': len(self._config.get_enabled_points()),
            'total_samples': self._total_samples,
            'failed_samples': self._failed_samples,
            'consecutive_errors': self._consecutive_errors,
        }

    def add_point(self, point: PointConfig) -> bool:
        """
        动态添加点位

        Args:
            point: 点位配置

        Returns:
            bool
        """
        with self._lock:
            if point.point_id in self._point_schedules:
                logger.warning(f"点位已存在: {point.point_id}")
                return False

            self._config.points.append(point)
            now = time.time()
            self._point_schedules[point.point_id] = {
                'point': point,
                'next_sample_time': now,
                'period': point.sampling_period,
            }
            logger.info(f"点位已添加: {point.point_id}")
            return True

    def remove_point(self, point_id: str) -> bool:
        """
        动态移除点位

        Args:
            point_id: 点位ID

        Returns:
            bool
        """
        with self._lock:
            if point_id not in self._point_schedules:
                return False

            del self._point_schedules[point_id]
            self._config.points = [
                p for p in self._config.points
                if p.point_id != point_id
            ]
            logger.info(f"点位已移除: {point_id}")
            return True
