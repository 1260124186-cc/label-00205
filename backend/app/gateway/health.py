"""
网关健康监控模块

监控网关自身的运行状态、设备连接状态、
点位采集状态，并提供健康检查接口。
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from loguru import logger

from app.gateway.models import (
    GatewayStatus,
    DeviceStatus,
    PointStatus,
    DeviceRuntimeStatus,
    PointRuntimeStatus,
    GatewayRuntimeStats,
)


@dataclass
class HealthAlert:
    """健康告警"""
    level: str  # info / warning / error / critical
    source: str
    message: str
    timestamp: datetime
    resolved: bool = False


class GatewayHealthMonitor:
    """
    网关健康监控器

    监控网关、设备、点位的运行状态，
    记录健康指标，支持健康告警。
    """

    def __init__(self, check_interval: int = 30):
        """
        初始化健康监控器

        Args:
            check_interval: 健康检查间隔（秒）
        """
        self._check_interval = check_interval
        self._is_running = False
        self._check_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # 网关状态
        self._gateway_status: GatewayStatus = GatewayStatus.STOPPED
        self._gateway_start_time: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None

        # 设备状态
        self._device_statuses: Dict[str, DeviceRuntimeStatus] = {}

        # 点位状态
        self._point_statuses: Dict[str, PointRuntimeStatus] = {}

        # 统计信息
        self._total_samples: int = 0
        self._total_points: int = 0
        self._active_points: int = 0
        self._samples_per_second: float = 0.0
        self._sample_timestamps: List[float] = []  # 最近1分钟的采样时间戳

        # 健康告警
        self._alerts: List[HealthAlert] = []
        self._max_alerts: int = 100
        self._alert_callbacks: List[Callable[[HealthAlert], None]] = []

        # 缓存大小（外部设置）
        self._cache_size: int = 0

        logger.info("网关健康监控器初始化完成")

    # ============ 启动/停止 ============

    def start(self) -> None:
        """启动健康监控"""
        if self._is_running:
            logger.warning("健康监控已在运行")
            return

        self._is_running = True
        self._gateway_status = GatewayStatus.STARTING
        self._gateway_start_time = datetime.now()

        self._check_thread = threading.Thread(
            target=self._check_loop,
            daemon=True,
            name="gateway-health-monitor",
        )
        self._check_thread.start()

        logger.info("健康监控已启动")

    def stop(self) -> None:
        """停止健康监控"""
        self._is_running = False
        self._gateway_status = GatewayStatus.STOPPED

        if self._check_thread:
            self._check_thread.join(timeout=5.0)
            self._check_thread = None

        logger.info("健康监控已停止")

    # ============ 网关状态 ============

    def set_gateway_status(self, status: GatewayStatus) -> None:
        """
        设置网关状态

        Args:
            status: 网关状态
        """
        with self._lock:
            old_status = self._gateway_status
            self._gateway_status = status

            if old_status != status:
                logger.info(f"网关状态变更: {old_status.value} -> {status.value}")
                if status == GatewayStatus.ERROR:
                    self._add_alert(
                        level="error",
                        source="gateway",
                        message="网关进入错误状态",
                    )
                elif old_status == GatewayStatus.ERROR:
                    self._add_alert(
                        level="info",
                        source="gateway",
                        message="网关从错误状态恢复",
                    )

    def get_gateway_status(self) -> GatewayStatus:
        """获取网关状态"""
        return self._gateway_status

    # ============ 设备状态 ============

    def register_device(self, device_id: str, total_points: int = 0) -> None:
        """
        注册设备

        Args:
            device_id: 设备ID
            total_points: 总点数
        """
        with self._lock:
            if device_id not in self._device_statuses:
                self._device_statuses[device_id] = DeviceRuntimeStatus(
                    device_id=device_id,
                    status=DeviceStatus.DISCONNECTED,
                    total_points=total_points,
                )
            else:
                self._device_statuses[device_id].total_points = total_points

    def unregister_device(self, device_id: str) -> None:
        """
        注销设备

        Args:
            device_id: 设备ID
        """
        with self._lock:
            if device_id in self._device_statuses:
                del self._device_statuses[device_id]
                logger.debug(f"设备已从健康监控中注销: {device_id}")

    def update_device_status(
        self,
        device_id: str,
        status: DeviceStatus,
        error: str = "",
    ) -> None:
        """
        更新设备状态

        Args:
            device_id: 设备ID
            status: 设备状态
            error: 错误信息
        """
        with self._lock:
            if device_id not in self._device_statuses:
                self.register_device(device_id)

            device_status = self._device_statuses[device_id]
            old_status = device_status.status
            device_status.status = status

            if status == DeviceStatus.CONNECTED:
                device_status.last_connect_time = datetime.now()
                device_status.consecutive_errors = 0
                device_status.last_error = ""
                if old_status != DeviceStatus.CONNECTED:
                    self._add_alert(
                        level="info",
                        source=f"device:{device_id}",
                        message=f"设备 {device_id} 已连接",
                    )
            elif status == DeviceStatus.DISCONNECTED:
                device_status.last_disconnect_time = datetime.now()
                if old_status == DeviceStatus.CONNECTED:
                    self._add_alert(
                        level="warning",
                        source=f"device:{device_id}",
                        message=f"设备 {device_id} 断开连接",
                    )
            elif status == DeviceStatus.ERROR:
                device_status.consecutive_errors += 1
                device_status.last_error = error
                if device_status.consecutive_errors >= 3:
                    self._add_alert(
                        level="error",
                        source=f"device:{device_id}",
                        message=f"设备 {device_id} 连续错误 {device_status.consecutive_errors} 次: {error}",
                    )

    def get_device_status(self, device_id: str) -> Optional[DeviceRuntimeStatus]:
        """
        获取设备状态

        Args:
            device_id: 设备ID

        Returns:
            DeviceRuntimeStatus or None
        """
        with self._lock:
            return self._device_statuses.get(device_id)

    def get_all_device_statuses(self) -> Dict[str, DeviceRuntimeStatus]:
        """获取所有设备状态"""
        with self._lock:
            return self._device_statuses.copy()

    # ============ 点位状态 ============

    def register_point(self, device_id: str, point_id: str) -> None:
        """
        注册点位

        Args:
            device_id: 设备ID
            point_id: 点位ID
        """
        key = f"{device_id}:{point_id}"
        with self._lock:
            if key not in self._point_statuses:
                self._point_statuses[key] = PointRuntimeStatus(
                    point_id=point_id,
                    status=PointStatus.IDLE,
                )
                self._total_points += 1

    def update_point_sample(
        self,
        device_id: str,
        point_id: str,
        value: float,
        success: bool = True,
    ) -> None:
        """
        更新点位采样结果

        Args:
            device_id: 设备ID
            point_id: 点位ID
            value: 采样值
            success: 是否成功
        """
        key = f"{device_id}:{point_id}"
        with self._lock:
            if key not in self._point_statuses:
                self.register_point(device_id, point_id)

            point_status = self._point_statuses[key]

            if success:
                point_status.status = PointStatus.ACTIVE
                point_status.last_sample_time = datetime.now()
                point_status.last_value = value
                point_status.consecutive_errors = 0
                point_status.total_samples += 1

                # 更新设备统计
                if device_id in self._device_statuses:
                    self._device_statuses[device_id].points_sampled += 1

                # 更新全局统计
                self._total_samples += 1
                self._sample_timestamps.append(time.time())
                self._cleanup_old_timestamps()

            else:
                point_status.status = PointStatus.ERROR
                point_status.consecutive_errors += 1
                point_status.failed_samples += 1

                if point_status.consecutive_errors >= 5:
                    self._add_alert(
                        level="warning",
                        source=f"point:{key}",
                        message=f"点位 {point_id} 连续采样失败 {point_status.consecutive_errors} 次",
                    )

                # 更新设备统计
                if device_id in self._device_statuses:
                    self._device_statuses[device_id].points_failed += 1

    def get_point_status(
        self, device_id: str, point_id: str
    ) -> Optional[PointRuntimeStatus]:
        """
        获取点位状态

        Args:
            device_id: 设备ID
            point_id: 点位ID

        Returns:
            PointRuntimeStatus or None
        """
        key = f"{device_id}:{point_id}"
        with self._lock:
            return self._point_statuses.get(key)

    # ============ 统计信息 ============

    def record_sample(self, count: int = 1) -> None:
        """
        记录采样（用于QPS统计）

        Args:
            count: 采样数量
        """
        with self._lock:
            now = time.time()
            for _ in range(count):
                self._sample_timestamps.append(now)
            self._total_samples += count
            self._cleanup_old_timestamps()

    def _cleanup_old_timestamps(self) -> None:
        """清理旧的时间戳（保留最近1分钟）"""
        cutoff = time.time() - 60.0
        while self._sample_timestamps and self._sample_timestamps[0] < cutoff:
            self._sample_timestamps.pop(0)

    def update_cache_size(self, size: int) -> None:
        """
        更新缓存大小

        Args:
            size: 缓存大小
        """
        self._cache_size = size

    def update_active_points(self, count: int) -> None:
        """
        更新活跃点数

        Args:
            count: 活跃点数
        """
        self._active_points = count

    # ============ 健康检查 ============

    def _check_loop(self) -> None:
        """健康检查循环"""
        while self._is_running:
            try:
                self._perform_health_check()
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
                time.sleep(self._check_interval)

    def _perform_health_check(self) -> None:
        """执行健康检查"""
        self._last_health_check = datetime.now()

        # 计算 QPS
        with self._lock:
            self._cleanup_old_timestamps()
            self._samples_per_second = len(self._sample_timestamps) / 60.0

        # 检查设备连接状态
        connected_count = 0
        for device_id, status in self._device_statuses.items():
            if status.status == DeviceStatus.CONNECTED:
                connected_count += 1

        # 更新网关状态
        if self._gateway_status == GatewayStatus.STARTING:
            if connected_count > 0:
                self.set_gateway_status(GatewayStatus.RUNNING)

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取健康状态

        Returns:
            健康状态字典
        """
        with self._lock:
            devices = self.get_all_device_statuses()
            connected_devices = sum(
                1 for d in devices.values()
                if d.status == DeviceStatus.CONNECTED
            )

            uptime = 0.0
            if self._gateway_start_time:
                uptime = (datetime.now() - self._gateway_start_time).total_seconds()

            # 计算健康级别
            status_value = self._gateway_status.value
            if status_value == 'error':
                health_level = 'unhealthy'
            elif connected_devices == 0 and len(devices) > 0:
                health_level = 'degraded'
            elif self._active_points < self._total_points * 0.5 and self._total_points > 0:
                health_level = 'degraded'
            elif status_value in ('running', 'starting'):
                health_level = 'healthy'
            else:
                health_level = 'unknown'

            return {
                'status': status_value,
                'health_level': health_level,
                'uptime_seconds': uptime,
                'start_time': self._gateway_start_time.isoformat()
                    if self._gateway_start_time else None,
                'last_health_check': self._last_health_check.isoformat()
                    if self._last_health_check else None,
                'total_devices': len(devices),
                'connected_devices': connected_devices,
                'total_points': self._total_points,
                'active_points': self._active_points,
                'total_samples': self._total_samples,
                'samples_per_second': round(self._samples_per_second, 2),
                'cache_size': self._cache_size,
                'alerts_count': len(self._alerts),
            }

    def get_stats(self) -> GatewayRuntimeStats:
        """
        获取运行时统计

        Returns:
            GatewayRuntimeStats
        """
        with self._lock:
            devices = self._device_statuses
            connected_devices = sum(
                1 for d in devices.values()
                if d.status == DeviceStatus.CONNECTED
            )

            uptime = 0.0
            if self._gateway_start_time:
                uptime = (datetime.now() - self._gateway_start_time).total_seconds()

            return GatewayRuntimeStats(
                status=self._gateway_status,
                start_time=self._gateway_start_time,
                total_devices=len(devices),
                connected_devices=connected_devices,
                total_points=self._total_points,
                active_points=self._active_points,
                total_samples=self._total_samples,
                samples_per_second=round(self._samples_per_second, 2),
                cache_size=self._cache_size,
                last_health_check=self._last_health_check,
                uptime_seconds=uptime,
            )

    # ============ 健康告警 ============

    def _add_alert(self, level: str, source: str, message: str) -> None:
        """
        添加健康告警

        Args:
            level: 告警级别
            source: 告警来源
            message: 告警消息
        """
        alert = HealthAlert(
            level=level,
            source=source,
            message=message,
            timestamp=datetime.now(),
        )

        with self._lock:
            self._alerts.append(alert)
            if len(self._alerts) > self._max_alerts:
                self._alerts.pop(0)

        logger.log(
            "WARNING" if level in ("warning", "error") else "INFO",
            f"健康告警 [{level}] {source}: {message}"
        )

        # 通知回调
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"健康告警回调执行失败: {e}")

    def get_alerts(
        self,
        level: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取告警列表

        Args:
            level: 告警级别过滤
            limit: 返回数量限制

        Returns:
            告警列表
        """
        with self._lock:
            alerts = self._alerts
            if level:
                alerts = [a for a in alerts if a.level == level]

            result = []
            for alert in alerts[-limit:]:
                result.append({
                    'level': alert.level,
                    'source': alert.source,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'resolved': alert.resolved,
                })
            return result

    def register_alert_callback(
        self, callback: Callable[[HealthAlert], None]
    ) -> None:
        """
        注册告警回调

        Args:
            callback: 回调函数
        """
        self._alert_callbacks.append(callback)

    # ============ 健康检查接口 ============

    def is_healthy(self) -> bool:
        """
        网关是否健康

        Returns:
            bool
        """
        return self._gateway_status in (
            GatewayStatus.RUNNING,
            GatewayStatus.STARTING,
        )

    def check_overall_health(self) -> Dict[str, Any]:
        """
        综合健康检查

        Returns:
            健康检查结果
        """
        status = self.get_health_status()

        # 判定健康级别
        if status['status'] == 'error':
            health_level = 'unhealthy'
        elif status['connected_devices'] == 0 and status['total_devices'] > 0:
            health_level = 'degraded'
        elif status['active_points'] < status['total_points'] * 0.5:
            health_level = 'degraded'
        else:
            health_level = 'healthy'

        return {
            'healthy': health_level == 'healthy',
            'level': health_level,
            'details': status,
        }


# 全局单例
_health_monitor: Optional[GatewayHealthMonitor] = None


def get_health_monitor(check_interval: int = 30) -> GatewayHealthMonitor:
    """
    获取健康监控器单例

    Args:
        check_interval: 检查间隔（首次调用时使用）

    Returns:
        GatewayHealthMonitor
    """
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = GatewayHealthMonitor(check_interval)
    return _health_monitor
