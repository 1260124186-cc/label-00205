"""
工业协议采集网关主服务

整合所有采集器、配置管理、数据写入、缓存、健康监控等组件，
提供统一的网关服务入口。
"""

import time
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.gateway.models import (
    GatewayConfig,
    DeviceConfig,
    PointConfig,
    DataPoint,
    GatewayStatus,
    DeviceStatus,
    ProtocolType,
    DataSourceType,
    GatewayRuntimeStats,
)
from app.gateway.config_manager import GatewayConfigManager
from app.gateway.data_writer import GatewayDataWriter
from app.gateway.cache import OfflineCache
from app.gateway.health import GatewayHealthMonitor
from app.gateway.cert_manager import CertificateManager
from app.gateway.templates import PLCTemplateManager
from app.gateway.base_collector import BaseCollector
from app.gateway.opcua_collector import create_opcua_collector
from app.gateway.modbus_collector import create_modbus_collector


class IndustrialGatewayService:
    """
    工业协议采集网关服务

    整合所有网关组件，提供统一的服务入口。
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config_manager: Optional[GatewayConfigManager] = None,
        data_writer: Optional[GatewayDataWriter] = None,
        offline_cache: Optional[OfflineCache] = None,
        health_monitor: Optional[GatewayHealthMonitor] = None,
        cert_manager: Optional[CertificateManager] = None,
        template_manager: Optional[PLCTemplateManager] = None,
    ):
        """
        初始化网关服务

        Args:
            config_path: 配置文件路径
            config_manager: 配置管理器
            data_writer: 数据写入器
            offline_cache: 离线缓存
            health_monitor: 健康监控器
            cert_manager: 证书管理器
            template_manager: PLC模板管理器
        """
        # 初始化组件
        if config_manager:
            self._config_manager = config_manager
        else:
            self._config_manager = GatewayConfigManager(config_path)

        if data_writer:
            self._data_writer = data_writer
        else:
            config = self._config_manager.get_config()
            self._data_writer = GatewayDataWriter(
                data_target=config.data_target,
                stream_ingest_url=config.stream_ingest_url,
            )

        if offline_cache:
            self._offline_cache = offline_cache
        else:
            config = self._config_manager.get_config()
            self._offline_cache = OfflineCache(
                cache_dir=config.cache_dir,
                max_disk_size=config.cache_max_size,
            )

        if health_monitor:
            self._health_monitor = health_monitor
        else:
            config = self._config_manager.get_config()
            self._health_monitor = GatewayHealthMonitor(
                check_interval=config.health_check_interval,
            )

        if cert_manager:
            self._cert_manager = cert_manager
        else:
            self._cert_manager = CertificateManager()

        if template_manager:
            self._template_manager = template_manager
        else:
            self._template_manager = PLCTemplateManager()

        # 采集器管理
        self._collectors: Dict[str, BaseCollector] = {}
        self._collectors_lock = threading.RLock()

        # 运行状态
        self._is_running: bool = False
        self._start_time: Optional[datetime] = None

        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None

        # 设备健康心跳上报
        self._heartbeat_buffer: Dict[str, Dict[str, Any]] = {}
        self._heartbeat_lock = threading.Lock()
        self._last_heartbeat_flush: float = 0.0

        # 注册配置变更回调
        self._config_manager.register_change_callback(self._on_config_change)

        # 注册数据写入结果回调（异步真实写入结果回传）
        self._data_writer.set_batch_result_callback(self._on_write_result)

        logger.info("工业协议采集网关服务初始化完成")

    # ============ 生命周期 ============

    def start(self) -> bool:
        """
        启动网关服务

        Returns:
            bool: 是否启动成功
        """
        if self._is_running:
            logger.warning("网关服务已在运行")
            return True

        try:
            logger.info("正在启动工业协议采集网关...")

            # 启动健康监控
            self._health_monitor.start()
            self._health_monitor.set_gateway_status(GatewayStatus.STARTING)

            # 启动数据写入器
            self._data_writer.start()

            # 启动离线缓存续传
            if self._config_manager.get_config().cache_enabled:
                self._offline_cache.start_auto_replay(
                    callback=self._replay_callback,
                )

            # 启动所有设备采集器
            config = self._config_manager.get_config()
            success_count = 0

            for device in config.get_enabled_devices():
                try:
                    if self._start_device_collector(device):
                        success_count += 1
                except Exception as e:
                    logger.error(f"启动设备采集器失败 {device.device_id}: {e}")

            # 启动配置热加载监控
            self._config_manager.start_reload_watcher()

            # 启动状态监控线程
            self._is_running = True
            self._start_time = datetime.now()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="gateway-monitor",
            )
            self._monitor_thread.start()

            # 更新网关状态
            if success_count > 0:
                self._health_monitor.set_gateway_status(GatewayStatus.RUNNING)
            else:
                self._health_monitor.set_gateway_status(GatewayStatus.ERROR)

            logger.info(
                f"网关服务已启动，成功启动 {success_count}/{len(config.get_enabled_devices())} 个设备"
            )
            return True

        except Exception as e:
            logger.error(f"启动网关服务失败: {e}")
            self._health_monitor.set_gateway_status(GatewayStatus.ERROR)
            return False

    def stop(self) -> None:
        """停止网关服务"""
        if not self._is_running:
            return

        logger.info("正在停止工业协议采集网关...")

        self._is_running = False

        # 停止配置热加载监控
        try:
            self._config_manager.stop_reload_watcher()
        except Exception as e:
            logger.error(f"停止配置热加载失败: {e}")

        # 停止所有采集器
        with self._collectors_lock:
            for device_id, collector in self._collectors.items():
                try:
                    collector.stop()
                    logger.debug(f"已停止采集器: {device_id}")
                except Exception as e:
                    logger.error(f"停止采集器失败 {device_id}: {e}")
            self._collectors.clear()

        # 停止离线缓存续传
        try:
            self._offline_cache.stop_auto_replay()
            self._offline_cache.flush()
        except Exception as e:
            logger.error(f"停止离线缓存失败: {e}")

        # 停止数据写入器
        try:
            self._data_writer.stop()
        except Exception as e:
            logger.error(f"停止数据写入器失败: {e}")

        # 刷新剩余心跳数据
        try:
            with self._heartbeat_lock:
                if self._heartbeat_buffer:
                    self._flush_heartbeats()
        except Exception as e:
            logger.error(f"停止时刷新心跳失败: {e}")

        # 停止健康监控
        try:
            self._health_monitor.stop()
        except Exception as e:
            logger.error(f"停止健康监控失败: {e}")

        # 停止监控线程
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

        logger.info("网关服务已停止")

    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return self._is_running

    # ============ 设备管理 ============

    def _start_device_collector(self, device_config: DeviceConfig) -> bool:
        """
        启动单个设备采集器

        Args:
            device_config: 设备配置

        Returns:
            bool: 是否启动成功
        """
        with self._collectors_lock:
            # 如果已存在，先停止
            if device_config.device_id in self._collectors:
                try:
                    self._collectors[device_config.device_id].stop()
                except Exception:
                    pass
                del self._collectors[device_config.device_id]

            # 注册到健康监控
            self._health_monitor.register_device(
                device_id=device_config.device_id,
                total_points=len(device_config.get_enabled_points()),
            )

            # 注册点位
            for point in device_config.get_enabled_points():
                self._health_monitor.register_point(
                    device_id=device_config.device_id,
                    point_id=point.point_id,
                )

            # 创建采集器
            collector = self._create_collector(device_config)
            if collector is None:
                logger.error(f"无法创建采集器: {device_config.device_id}")
                self._health_monitor.update_device_status(
                    device_id=device_config.device_id,
                    status=DeviceStatus.ERROR,
                    error="不支持的协议类型",
                )
                return False

            # 启动采集器
            success = collector.start()
            if success:
                self._collectors[device_config.device_id] = collector
                logger.info(f"设备采集器已启动: {device_config.device_id}")
            else:
                self._health_monitor.update_device_status(
                    device_id=device_config.device_id,
                    status=DeviceStatus.ERROR,
                    error="启动失败",
                )

            return success

    def _create_collector(self, device_config: DeviceConfig) -> Optional[BaseCollector]:
        """
        根据协议类型创建采集器

        Args:
            device_config: 设备配置

        Returns:
            BaseCollector or None
        """
        data_callback = self._on_data_collected
        status_callback = self._on_device_status_change

        if device_config.protocol == ProtocolType.OPC_UA:
            return create_opcua_collector(
                device_config=device_config,
                data_callback=data_callback,
                status_callback=status_callback,
                cert_manager=self._cert_manager,
            )
        elif device_config.protocol in (
            ProtocolType.MODBUS_TCP,
            ProtocolType.MODBUS_RTU,
        ):
            return create_modbus_collector(
                device_config=device_config,
                data_callback=data_callback,
                status_callback=status_callback,
            )
        else:
            logger.error(f"不支持的协议类型: {device_config.protocol}")
            return None

    def add_device(self, device_config: DeviceConfig) -> bool:
        """
        动态添加设备

        Args:
            device_config: 设备配置

        Returns:
            bool
        """
        # 更新配置
        if not self._config_manager.update_device(device_config):
            return False

        # 如果网关正在运行，启动采集器
        if self._is_running:
            return self._start_device_collector(device_config)

        return True

    def remove_device(self, device_id: str) -> bool:
        """
        动态移除设备

        Args:
            device_id: 设备ID

        Returns:
            bool
        """
        # 停止采集器
        with self._collectors_lock:
            if device_id in self._collectors:
                try:
                    self._collectors[device_id].stop()
                except Exception:
                    pass
                del self._collectors[device_id]

        # 注销健康监控
        self._health_monitor.unregister_device(device_id)

        # 从配置中删除
        return self._config_manager.delete_device(device_id)

    # ============ 数据处理 ============

    def _on_data_collected(self, data_points: List[DataPoint]) -> None:
        """
        数据采集回调

        这里只做入队处理。真实写入结果通过 _on_write_result 异步接收，
        只有失败的数据才会回退到离线缓存。

        Args:
            data_points: 数据点列表
        """
        if not data_points:
            return

        # 更新健康监控（采样成功/失败只跟采集质量挂钩）
        for dp in data_points:
            self._health_monitor.update_point_sample(
                device_id=dp.device_id,
                point_id=dp.point_id,
                value=dp.value,
                success=(dp.quality == "good"),
            )

        # 只要入队成功就先往下走（队列本身是内存缓冲）
        # 真实写入失败由 _on_write_result 统一回退缓存
        enqueued = self._data_writer.write_batch(data_points)
        if enqueued == 0:
            # 连入队都失败了，直接进缓存
            logger.warning("数据入队失败，全部回退到离线缓存")
            self._fallback_to_cache(data_points)

        # 更新缓存大小统计
        self._health_monitor.update_cache_size(self._offline_cache.size)

    def _on_write_result(
        self,
        success_points: List[DataPoint],
        failed_points: List[DataPoint],
        is_replay: bool,
    ) -> None:
        """
        批次真实写入结果回调

        Args:
            success_points: 写入成功的数据点
            failed_points: 写入失败的数据点
            is_replay: 是否为续传批次
        """
        # 统计写入成功
        if success_points:
            self._health_monitor._total_written_batches = getattr(
                self._health_monitor, "_total_written_batches", 0
            ) + 1

        # 更新设备健康心跳（仅实时采集且启用时）
        if success_points and not is_replay:
            self._update_device_heartbeats(success_points)

        # 失败的数据回退缓存（实时采集与续传都需要）
        if failed_points:
            if is_replay:
                # 续传失败：数据放回缓存队首，等待下次续传
                logger.warning(
                    f"续传批次写入失败: {len(failed_points)} 条，将在下次续传时重试"
                )
                self._reinsert_to_cache_head(failed_points)
            else:
                # 实时采集失败：回退到缓存等待自动续传
                logger.warning(
                    f"实时写入失败: {len(failed_points)} 条，回退到离线缓存"
                )
                self._fallback_to_cache(failed_points)

        # 更新缓存大小统计
        self._health_monitor.update_cache_size(self._offline_cache.size)

    def _update_device_heartbeats(self, points: List[DataPoint]) -> None:
        """
        更新设备健康心跳（缓冲批量上报）

        Args:
            points: 成功写入的数据点列表
        """
        config = self._config_manager.get_config()
        if not getattr(config, 'device_health_enabled', True):
            return

        try:
            gateway_id = config.gateway_id

            with self._heartbeat_lock:
                for point in points:
                    sensor_id = str(point.sensor_id)
                    key = f"{gateway_id}:{sensor_id}"

                    buffered = self._heartbeat_buffer.get(key)
                    if buffered is None:
                        self._heartbeat_buffer[key] = {
                            'gateway_id': gateway_id,
                            'device_id': point.device_id,
                            'sensor_id': sensor_id,
                            'value': point.value,
                            'timestamp': point.timestamp,
                            'sampling_period': self._get_sampling_period(point),
                            'point_name': point.point_id if hasattr(point, 'point_id') else '',
                        }
                    else:
                        if point.timestamp > buffered['timestamp']:
                            buffered['value'] = point.value
                            buffered['timestamp'] = point.timestamp

                batch_size = getattr(config, 'device_heartbeat_batch_size', 100)
                now = time.time()
                if len(self._heartbeat_buffer) >= batch_size or (
                    now - self._last_heartbeat_flush >= 5.0
                    and self._heartbeat_buffer
                ):
                    self._flush_heartbeats()
                    self._last_heartbeat_flush = now

        except Exception as e:
            logger.error(f"更新设备心跳失败: {e}")

    def _get_sampling_period(self, point: DataPoint) -> float:
        """获取点位的采样周期（秒）"""
        try:
            from app.gateway.models import PointConfig
            config = self._config_manager.get_config()
            for device in config.devices:
                for p in device.points:
                    if p.point_id == getattr(point, 'point_id', None):
                        return p.sampling_period
        except Exception:
            pass
        return 60.0

    def _flush_heartbeats(self) -> None:
        """
        刷新心跳缓冲区，批量上报到设备健康监控服务
        """
        if not self._heartbeat_buffer:
            return

        try:
            from app.services.device_health_service import get_device_health_service

            dh_service = get_device_health_service()
            buffer_copy = list(self._heartbeat_buffer.values())
            self._heartbeat_buffer.clear()

            success_count = 0
            for hb in buffer_copy:
                try:
                    dh_service.record_heartbeat(
                        collector_id=hb['gateway_id'],
                        sensor_id=hb['sensor_id'],
                        value=hb['value'],
                        timestamp=hb['timestamp'],
                        sampling_interval=hb.get('sampling_period'),
                        device_name=hb.get('point_name', ''),
                    )
                    success_count += 1
                except Exception as e:
                    logger.warning(
                        f"上报心跳失败 {hb['gateway_id']}/{hb['sensor_id']}: {e}"
                    )

            if success_count > 0:
                logger.debug(f"心跳批量上报完成: {success_count}/{len(buffer_copy)}")

        except Exception as e:
            logger.error(f"批量刷新心跳失败: {e}")

    def _fallback_to_cache(self, points: List[DataPoint]) -> None:
        """
        将数据写入离线缓存（队尾，等待后续自动续传）

        Args:
            points: 需要缓存的数据点
        """
        if not points:
            return
        if not self._config_manager.get_config().cache_enabled:
            logger.warning(
                f"缓存未启用，丢弃 {len(points)} 条写入失败数据"
            )
            return
        cached = self._offline_cache.add_points(points)
        if cached > 0:
            logger.debug(f"写入失败，已缓存 {cached} 条数据（等待自动续传）")

    def _reinsert_to_cache_head(self, points: List[DataPoint]) -> None:
        """
        将续传失败的数据放回缓存队首（优先重传）

        Args:
            points: 续传失败的数据点
        """
        if not points:
            return
        if not self._config_manager.get_config().cache_enabled:
            logger.warning(
                f"缓存未启用，丢弃 {len(points)} 条续传失败数据"
            )
            return
        # 利用 pop + 倒序 add 的方式无法直接插队首，
        # 通过 cache 内部把 failed_points 优先添加到队首
        self._offline_cache.add_points_to_head(points)

    def _on_device_status_change(
        self, device_id: str, status: DeviceStatus, error: str = ""
    ) -> None:
        """
        设备状态变化回调

        Args:
            device_id: 设备ID
            status: 设备状态
            error: 错误信息
        """
        self._health_monitor.update_device_status(
            device_id=device_id,
            status=status,
            error=error,
        )

        logger.info(
            f"设备状态变更: {device_id} -> {status.value}"
            + (f" ({error})" if error else "")
        )

    def _replay_callback(self, data_points: List[DataPoint]) -> bool:
        """
        缓存续传回调

        使用同步写入 API，必须返回真实的写入结果，
        才能决定缓存数据是确认弹出还是放回。

        Args:
            data_points: 数据点列表

        Returns:
            bool: 是否续传成功（所有点都写入成功才算成功）
        """
        if not data_points:
            return True

        success_count, failed_count = self._data_writer.write_batch_sync(
            data_points, is_replay=True
        )
        total = len(data_points)

        # 全部成功才返回 True，让缓存把数据弹出
        if failed_count == 0 and success_count == total:
            logger.debug(f"续传成功: {success_count} 条")
            return True
        else:
            logger.warning(
                f"续传未完全成功: {success_count}/{total} 成功, "
                f"{failed_count} 失败，数据将放回缓存重试"
            )
            # 返回 False → cache 会自动把数据放回队首
            return False

    # ============ 配置变更 ============

    def _on_config_change(self, config: GatewayConfig) -> None:
        """
        配置变更回调

        Args:
            config: 新配置
        """
        logger.info("检测到配置变更，正在应用...")

        # 更新数据写入器配置
        self._data_writer.update_config(config)

        # 更新缓存配置
        if config.cache_enabled:
            self._offline_cache.set_max_sizes(
                max_memory=10000,
                max_disk=config.cache_max_size,
            )

        # 同步设备配置
        if self._is_running:
            self._sync_devices(config)

        logger.info("配置变更已应用")

    def _sync_devices(self, config: GatewayConfig) -> None:
        """
        同步设备配置（热加载）

        本方法需要避免在 _collectors_lock 内部再次调用 _start_device_collector，
        以防锁重入/死锁。做法：在锁内计算待启动/移除的设备清单，
        在锁外实际执行启停操作。

        Args:
            config: 网关配置
        """
        enabled_devices = {d.device_id: d for d in config.get_enabled_devices()}

        devices_to_remove: List[str] = []
        devices_to_update: List[DeviceConfig] = []
        devices_to_start: List[DeviceConfig] = []

        # ============ 锁内：只做状态计算，不做 IO ============
        with self._collectors_lock:
            for device_id in list(self._collectors.keys()):
                if device_id not in enabled_devices:
                    devices_to_remove.append(device_id)

            for device_id, device_config in enabled_devices.items():
                if device_id in self._collectors:
                    devices_to_update.append(device_config)
                else:
                    devices_to_start.append(device_config)

            # 移除设备（stop 可能涉及IO，但此处移除的是停用/删除的设备，
            # 并且在锁内只操作字典，调用 stop 之前先 pop 出来在锁外执行）
            collectors_to_stop = {}
            for device_id in devices_to_remove:
                if device_id in self._collectors:
                    collectors_to_stop[device_id] = self._collectors.pop(device_id)

        # ============ 锁外：执行 IO 和启停 ============

        # 停止移除的设备
        for device_id, collector in collectors_to_stop.items():
            try:
                collector.stop()
            except Exception as e:
                logger.error(f"停止设备采集器失败 {device_id}: {e}")
            try:
                self._health_monitor.unregister_device(device_id)
            except Exception:
                pass
            logger.info(f"设备已移除: {device_id}")

        # 更新现有设备配置
        for device_config in devices_to_update:
            collector = self._collectors.get(device_config.device_id)
            if collector is not None:
                try:
                    collector.update_config(device_config)
                except Exception as e:
                    logger.error(
                        f"更新设备配置失败 {device_config.device_id}: {e}"
                    )

        # 启动新设备（在锁外调用 _start_device_collector，
        # 其内部会再次获取锁，此时不会死锁）
        for device_config in devices_to_start:
            try:
                self._start_device_collector(device_config)
            except Exception as e:
                logger.error(f"启动新设备失败 {device_config.device_id}: {e}")

    # ============ 监控循环 ============

    def _monitor_loop(self) -> None:
        """监控循环"""
        while self._is_running:
            try:
                # 更新活跃点数
                active_points = 0
                for collector in self._collectors.values():
                    stats = collector.get_stats()
                    active_points += stats.get('enabled_points', 0)
                self._health_monitor.update_active_points(active_points)

                # 更新缓存大小
                self._health_monitor.update_cache_size(
                    self._offline_cache.size
                )

                # 检查设备连接状态，尝试重连
                self._check_and_reconnect_devices()

                time.sleep(10)

            except Exception as e:
                logger.error(f"网关监控循环异常: {e}")
                time.sleep(10)

    def _check_and_reconnect_devices(self) -> None:
        """检查并重连断开的设备"""
        config = self._config_manager.get_config()

        devices_to_reconnect: List[DeviceConfig] = []

        # 锁内：只做判定
        with self._collectors_lock:
            for device in config.get_enabled_devices():
                device_status = self._health_monitor.get_device_status(
                    device.device_id
                )
                if device_status and device_status.status in (
                    DeviceStatus.DISCONNECTED,
                    DeviceStatus.ERROR,
                ):
                    # 先取出并停止现有采集器
                    if device.device_id in self._collectors:
                        try:
                            collector = self._collectors.pop(device.device_id)
                            collector.stop()
                        except Exception:
                            pass
                    devices_to_reconnect.append(device)

        # 锁外：真正执行重连（_start_device_collector 内部会重新拿锁）
        for device in devices_to_reconnect:
            logger.info(f"尝试重连设备: {device.device_id}")
            try:
                self._start_device_collector(device)
            except Exception as e:
                logger.error(f"重连设备失败 {device.device_id}: {e}")

    # ============ 数据查询 ============

    def get_status(self) -> Dict[str, Any]:
        """
        获取网关状态

        Returns:
            状态字典
        """
        return self._health_monitor.get_health_status()

    def get_stats(self) -> GatewayRuntimeStats:
        """
        获取网关统计信息

        Returns:
            GatewayRuntimeStats
        """
        return self._health_monitor.get_stats()

    def get_device_list(self) -> List[Dict[str, Any]]:
        """
        获取设备列表

        Returns:
            设备列表
        """
        config = self._config_manager.get_config()
        result = []

        for device in config.devices:
            status = self._health_monitor.get_device_status(device.device_id)
            result.append({
                'device_id': device.device_id,
                'name': device.name,
                'protocol': device.protocol.value,
                'host': device.host,
                'port': device.port,
                'enabled': device.enabled,
                'plc_brand': device.plc_brand.value,
                'total_points': len(device.points),
                'status': status.status.value if status else 'unknown',
                'last_connect_time': status.last_connect_time.isoformat()
                    if status and status.last_connect_time else None,
                'points_sampled': status.points_sampled if status else 0,
                'points_failed': status.points_failed if status else 0,
            })

        return result

    def get_device_detail(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        获取设备详情

        Args:
            device_id: 设备ID

        Returns:
            设备详情
        """
        device = self._config_manager.get_device(device_id)
        if device is None:
            return None

        status = self._health_monitor.get_device_status(device_id)
        collector = self._collectors.get(device_id)

        points = []
        for point in device.points:
            point_status = self._health_monitor.get_point_status(
                device_id, point.point_id
            )
            points.append({
                'point_id': point.point_id,
                'sensor_id': point.sensor_id,
                'name': point.name,
                'address': point.address,
                'data_type': point.data_type.value,
                'unit': point.unit,
                'scale_factor': point.scale_factor,
                'offset': point.offset,
                'sampling_period': point.sampling_period,
                'enabled': point.enabled,
                'status': point_status.status.value if point_status else 'idle',
                'last_value': point_status.last_value if point_status else None,
                'last_sample_time': point_status.last_sample_time.isoformat()
                    if point_status and point_status.last_sample_time else None,
            })

        return {
            'device_id': device.device_id,
            'name': device.name,
            'protocol': device.protocol.value,
            'host': device.host,
            'port': device.port,
            'slave_id': device.slave_id,
            'timeout': device.timeout,
            'retry_count': device.retry_count,
            'enabled': device.enabled,
            'plc_brand': device.plc_brand.value,
            'status': status.status.value if status else 'unknown',
            'last_error': status.last_error if status else '',
            'consecutive_errors': status.consecutive_errors if status else 0,
            'points': points,
            'collector_stats': collector.get_stats() if collector else {},
        }

    # ============ 组件访问 ============

    @property
    def config_manager(self) -> GatewayConfigManager:
        """配置管理器"""
        return self._config_manager

    @property
    def data_writer(self) -> GatewayDataWriter:
        """数据写入器"""
        return self._data_writer

    @property
    def offline_cache(self) -> OfflineCache:
        """离线缓存"""
        return self._offline_cache

    @property
    def health_monitor(self) -> GatewayHealthMonitor:
        """健康监控器"""
        return self._health_monitor

    @property
    def cert_manager(self) -> CertificateManager:
        """证书管理器"""
        return self._cert_manager

    @property
    def template_manager(self) -> PLCTemplateManager:
        """PLC模板管理器"""
        return self._template_manager

    def trigger_cache_replay(self) -> bool:
        """
        手动触发缓存续传

        Returns:
            bool
        """
        return self._offline_cache.trigger_replay()

    def flush_cache(self) -> None:
        """刷新缓存到磁盘"""
        self._offline_cache.flush()

    def clear_cache(self) -> None:
        """清空缓存"""
        self._offline_cache.clear()


# 全局单例
_gateway_service: Optional[IndustrialGatewayService] = None


def get_gateway_service(
    config_path: Optional[str] = None,
) -> IndustrialGatewayService:
    """
    获取网关服务单例

    Args:
        config_path: 配置文件路径（首次调用时使用）

    Returns:
        IndustrialGatewayService
    """
    global _gateway_service
    if _gateway_service is None:
        _gateway_service = IndustrialGatewayService(config_path=config_path)
    return _gateway_service
