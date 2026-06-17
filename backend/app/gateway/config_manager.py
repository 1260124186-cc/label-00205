"""
网关配置管理器

负责加载、验证和管理网关配置，支持配置热加载。
"""

import os
import json
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from loguru import logger
import yaml

from app.gateway.models import (
    GatewayConfig,
    DeviceConfig,
    PointConfig,
    ProtocolType,
    DataType,
    PLCBrand,
    DataSourceType,
)


class GatewayConfigManager:
    """
    网关配置管理器

    支持从 YAML/JSON 文件加载配置，支持配置热加载，
    并在配置变更时通知订阅者。
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self._config_path: Optional[Path] = None
        self._config: GatewayConfig = GatewayConfig()
        self._lock = threading.RLock()
        self._last_modified: float = 0.0
        self._reload_enabled: bool = True
        self._reload_interval: float = 60.0
        self._reload_thread: Optional[threading.Thread] = None
        self._is_running: bool = False
        self._change_callbacks: List[Callable[[GatewayConfig], None]] = []

        if config_path:
            self.load_config(config_path)

        logger.info("网关配置管理器初始化完成")

    # ============ 配置加载 ============

    def load_config(self, config_path: str) -> bool:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            bool: 是否加载成功
        """
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
            self._config = GatewayConfig()
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix in ('.yaml', '.yml'):
                    raw_config = yaml.safe_load(f) or {}
                elif path.suffix == '.json':
                    raw_config = json.load(f) or {}
                else:
                    logger.error(f"不支持的配置文件格式: {path.suffix}")
                    return False

            config = self._parse_config(raw_config)

            with self._lock:
                self._config = config
                self._config_path = path
                self._last_modified = path.stat().st_mtime

            logger.info(f"网关配置加载成功: {config_path}")
            self._notify_change()
            return True

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return False

    def _parse_config(self, raw: Dict[str, Any]) -> GatewayConfig:
        """
        解析原始配置为 GatewayConfig 对象

        Args:
            raw: 原始配置字典

        Returns:
            GatewayConfig
        """
        # 解析网关基本配置
        gateway_raw = raw.get('gateway', raw)

        config = GatewayConfig(
            gateway_id=gateway_raw.get('gateway_id', 'gateway-001'),
            name=gateway_raw.get('name', '工业协议采集网关'),
            data_target=DataSourceType(gateway_raw.get('data_target', 'sc_bolt_data')),
            stream_ingest_url=gateway_raw.get(
                'stream_ingest_url',
                'http://localhost:8000/stream/ingest'
            ),
            cache_enabled=gateway_raw.get('cache_enabled', True),
            cache_max_size=int(gateway_raw.get('cache_max_size', 100000)),
            cache_dir=gateway_raw.get('cache_dir', './data/gateway_cache'),
            health_check_interval=int(gateway_raw.get('health_check_interval', 30)),
            config_reload_interval=int(gateway_raw.get('config_reload_interval', 60)),
        )

        # 解析设备配置
        devices_raw = gateway_raw.get('devices', [])
        for device_raw in devices_raw:
            device = self._parse_device(device_raw)
            if device:
                config.devices.append(device)

        return config

    def _parse_device(self, raw: Dict[str, Any]) -> Optional[DeviceConfig]:
        """
        解析设备配置

        Args:
            raw: 原始设备配置

        Returns:
            DeviceConfig or None
        """
        try:
            device = DeviceConfig(
                device_id=raw['device_id'],
                name=raw.get('name', raw['device_id']),
                protocol=ProtocolType(raw.get('protocol', 'modbus_tcp')),
                host=raw.get('host', '127.0.0.1'),
                port=int(raw.get('port', 502)),
                slave_id=int(raw.get('slave_id', 1)),
                timeout=float(raw.get('timeout', 5.0)),
                retry_count=int(raw.get('retry_count', 3)),
                enabled=raw.get('enabled', True),
                plc_brand=PLCBrand(raw.get('plc_brand', 'general')),
                connection_config=raw.get('connection_config', {}),
            )

            # 解析点位配置
            points_raw = raw.get('points', [])
            for point_raw in points_raw:
                point = self._parse_point(point_raw)
                if point:
                    device.points.append(point)

            return device

        except Exception as e:
            logger.error(f"解析设备配置失败: {e}")
            return None

    def _parse_point(self, raw: Dict[str, Any]) -> Optional[PointConfig]:
        """
        解析点位配置

        Args:
            raw: 原始点位配置

        Returns:
            PointConfig or None
        """
        try:
            point = PointConfig(
                point_id=raw['point_id'],
                sensor_id=str(raw.get('sensor_id', raw['point_id'])),
                name=raw.get('name', raw['point_id']),
                address=raw['address'],
                data_type=DataType(raw.get('data_type', 'float32')),
                unit=raw.get('unit', ''),
                scale_factor=float(raw.get('scale_factor', 1.0)),
                offset=float(raw.get('offset', 0.0)),
                sampling_period=float(raw.get('sampling_period', 1.0)),
                enabled=raw.get('enabled', True),
                description=raw.get('description', ''),
                protocol_config=raw.get('protocol_config', {}),
                tags=raw.get('tags', {}),
            )
            return point
        except Exception as e:
            logger.error(f"解析点位配置失败: {e}")
            return None

    # ============ 配置访问 ============

    @property
    def config(self) -> GatewayConfig:
        """获取当前配置"""
        with self._lock:
            return self._config

    def get_config(self) -> GatewayConfig:
        """获取当前配置"""
        with self._lock:
            return self._config

    def get_device(self, device_id: str) -> Optional[DeviceConfig]:
        """
        获取指定设备配置

        Args:
            device_id: 设备ID

        Returns:
            DeviceConfig or None
        """
        with self._lock:
            for device in self._config.devices:
                if device.device_id == device_id:
                    return device
        return None

    def get_point(self, device_id: str, point_id: str) -> Optional[PointConfig]:
        """
        获取指定点位配置

        Args:
            device_id: 设备ID
            point_id: 点位ID

        Returns:
            PointConfig or None
        """
        device = self.get_device(device_id)
        if device is None:
            return None
        for point in device.points:
            if point.point_id == point_id:
                return point
        return None

    # ============ 配置热加载 ============

    def start_reload_watcher(self) -> None:
        """启动配置热加载监控"""
        if self._is_running:
            logger.warning("配置热加载监控已在运行")
            return

        if not self._config_path:
            logger.warning("未设置配置文件路径，无法启动热加载")
            return

        self._is_running = True
        self._reload_thread = threading.Thread(
            target=self._reload_loop,
            daemon=True,
            name="gateway-config-reload",
        )
        self._reload_thread.start()

        interval = self._config.config_reload_interval
        logger.info(f"配置热加载监控已启动，检查间隔: {interval}秒")

    def stop_reload_watcher(self) -> None:
        """停止配置热加载监控"""
        self._is_running = False
        if self._reload_thread:
            self._reload_thread.join(timeout=5.0)
            self._reload_thread = None
        logger.info("配置热加载监控已停止")

    def _reload_loop(self) -> None:
        """配置热加载循环"""
        while self._is_running:
            try:
                time.sleep(self._reload_interval)
                if self._check_config_changed():
                    logger.info("检测到配置文件变更，正在重新加载...")
                    if self.load_config(str(self._config_path)):
                        logger.info("配置热加载成功")
            except Exception as e:
                logger.error(f"配置热加载异常: {e}")

    def _check_config_changed(self) -> bool:
        """
        检查配置文件是否变更

        Returns:
            bool
        """
        if not self._config_path:
            return False

        try:
            current_mtime = self._config_path.stat().st_mtime
            if current_mtime > self._last_modified:
                return True
        except OSError:
            pass
        return False

    def reload_config(self) -> bool:
        """
        手动触发配置重新加载

        Returns:
            bool: 是否重新加载成功
        """
        if not self._config_path:
            logger.warning("未设置配置文件路径")
            return False

        logger.info("手动触发配置重新加载")
        return self.load_config(str(self._config_path))

    # ============ 配置修改 ============

    def update_device(self, device: DeviceConfig) -> bool:
        """
        更新设备配置

        Args:
            device: 设备配置

        Returns:
            bool
        """
        with self._lock:
            for i, d in enumerate(self._config.devices):
                if d.device_id == device.device_id:
                    self._config.devices[i] = device
                    logger.info(f"设备配置已更新: {device.device_id}")
                    self._notify_change()
                    return True

            self._config.devices.append(device)
            logger.info(f"新建设备配置: {device.device_id}")
            self._notify_change()
            return True

    def delete_device(self, device_id: str) -> bool:
        """
        删除设备配置

        Args:
            device_id: 设备ID

        Returns:
            bool
        """
        with self._lock:
            for i, d in enumerate(self._config.devices):
                if d.device_id == device_id:
                    del self._config.devices[i]
                    logger.info(f"设备配置已删除: {device_id}")
                    self._notify_change()
                    return True
        return False

    def update_point(self, device_id: str, point: PointConfig) -> bool:
        """
        更新点位配置

        Args:
            device_id: 设备ID
            point: 点位配置

        Returns:
            bool
        """
        with self._lock:
            device = None
            for d in self._config.devices:
                if d.device_id == device_id:
                    device = d
                    break

            if device is None:
                logger.warning(f"设备不存在: {device_id}")
                return False

            for i, p in enumerate(device.points):
                if p.point_id == point.point_id:
                    device.points[i] = point
                    logger.info(f"点位配置已更新: {device_id}/{point.point_id}")
                    self._notify_change()
                    return True

            device.points.append(point)
            logger.info(f"新建点位配置: {device_id}/{point.point_id}")
            self._notify_change()
            return True

    def delete_point(self, device_id: str, point_id: str) -> bool:
        """
        删除点位配置

        Args:
            device_id: 设备ID
            point_id: 点位ID

        Returns:
            bool
        """
        with self._lock:
            device = None
            for d in self._config.devices:
                if d.device_id == device_id:
                    device = d
                    break

            if device is None:
                return False

            for i, p in enumerate(device.points):
                if p.point_id == point_id:
                    del device.points[i]
                    logger.info(f"点位配置已删除: {device_id}/{point_id}")
                    self._notify_change()
                    return True
        return False

    # ============ 变更通知 ============

    def register_change_callback(self, callback: Callable[[GatewayConfig], None]) -> None:
        """
        注册配置变更回调

        Args:
            callback: 回调函数
        """
        self._change_callbacks.append(callback)

    def unregister_change_callback(self, callback: Callable[[GatewayConfig], None]) -> None:
        """
        注销配置变更回调

        Args:
            callback: 回调函数
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def _notify_change(self) -> None:
        """通知所有订阅者配置已变更"""
        config = self._config
        for callback in self._change_callbacks:
            try:
                callback(config)
            except Exception as e:
                logger.error(f"配置变更回调执行失败: {e}")

    # ============ 配置导出 ============

    def export_config(self, output_path: str) -> bool:
        """
        导出当前配置到文件

        Args:
            output_path: 输出文件路径

        Returns:
            bool
        """
        try:
            config_dict = self._config_to_dict()

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                if path.suffix in ('.yaml', '.yml'):
                    yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
                elif path.suffix == '.json':
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)
                else:
                    yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)

            logger.info(f"配置已导出到: {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False

    def _config_to_dict(self) -> Dict[str, Any]:
        """
        将配置转换为字典

        Returns:
            配置字典
        """
        with self._lock:
            config = self._config
            devices = []
            for device in config.devices:
                points = []
                for point in device.points:
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
                        'description': point.description,
                        'protocol_config': point.protocol_config,
                        'tags': point.tags,
                    })

                devices.append({
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
                    'connection_config': device.connection_config,
                    'points': points,
                })

            return {
                'gateway': {
                    'gateway_id': config.gateway_id,
                    'name': config.name,
                    'data_target': config.data_target.value,
                    'stream_ingest_url': config.stream_ingest_url,
                    'cache_enabled': config.cache_enabled,
                    'cache_max_size': config.cache_max_size,
                    'cache_dir': config.cache_dir,
                    'health_check_interval': config.health_check_interval,
                    'config_reload_interval': config.config_reload_interval,
                    'devices': devices,
                }
            }

    def validate_config(self) -> List[str]:
        """
        验证配置

        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        config = self._config

        # 验证设备ID唯一性
        device_ids = set()
        for device in config.devices:
            if device.device_id in device_ids:
                errors.append(f"设备ID重复: {device.device_id}")
            device_ids.add(device.device_id)

            # 验证点位ID唯一性
            point_ids = set()
            for point in device.points:
                if point.point_id in point_ids:
                    errors.append(
                        f"点位ID重复: {device.device_id}/{point.point_id}"
                    )
                point_ids.add(point.point_id)

        return errors


# 全局单例
_config_manager: Optional[GatewayConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> GatewayConfigManager:
    """
    获取网关配置管理器单例

    Args:
        config_path: 配置文件路径（首次调用时使用）

    Returns:
        GatewayConfigManager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = GatewayConfigManager(config_path)
    return _config_manager
