"""
OPC UA 采集器

实现 OPC UA 协议的数据采集，支持订阅和轮询两种模式。
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from loguru import logger

from app.gateway.models import (
    DeviceConfig,
    PointConfig,
    DataPoint,
    DeviceStatus,
    DataType,
)
from app.gateway.base_collector import BaseCollector

try:
    from opcua import Client, ua
    from opcua.common.subscription import SubHandler
    _has_opcua = True
except ImportError:
    _has_opcua = False
    logger.warning("opcua 库未安装，OPC UA 采集功能不可用")


class OPCUASubscriptionHandler:
    """OPC UA 订阅处理器"""

    def __init__(
        self,
        device_id: str,
        points: Dict[str, PointConfig],
        data_callback: Callable[[List[DataPoint]], None],
    ):
        """
        初始化订阅处理器

        Args:
            device_id: 设备ID
            points: 点位配置字典 {node_id: PointConfig}
            data_callback: 数据回调
        """
        self._device_id = device_id
        self._points = points
        self._data_callback = data_callback

    def datachange_notification(self, node, val, data):
        """
        数据变化通知

        Args:
            node: 节点对象
            val: 新值
            data: 数据对象
        """
        try:
            node_id = str(node.nodeid)

            # 查找对应的点位配置
            point = None
            for p in self._points.values():
                if p.address == node_id:
                    point = p
                    break

            if point is None:
                logger.warning(f"收到未知节点的数据变化: {node_id}")
                return

            # 转换值
            value = point.convert_value(val)
            timestamp = datetime.now()

            data_point = DataPoint(
                device_id=self._device_id,
                point_id=point.point_id,
                sensor_id=point.sensor_id,
                value=value,
                raw_value=val,
                timestamp=timestamp,
                quality="good",
                unit=point.unit,
            )

            self._data_callback([data_point])

        except Exception as e:
            logger.error(f"处理 OPC UA 数据变化通知失败: {e}")

    def event_notification(self, event):
        """事件通知"""
        logger.debug(f"OPC UA 事件: {event}")

    def status_change_notification(self, status):
        """状态变化通知"""
        logger.info(f"OPC UA 订阅状态变化: {status}")


class OPUACollector(BaseCollector):
    """
    OPC UA 采集器

    支持 OPC UA 协议的数据采集，提供两种模式：
    - 订阅模式：通过订阅机制实时获取数据变化
    - 轮询模式：定时轮询读取数据

    证书策略：
    - 如果传入了 cert_manager，则优先使用它：
        1. 若 device_config.connection_config 指定了 cert_name，则按名称查找
        2. 否则尝试获取默认证书（没有则自动生成）
    - 没有 cert_manager 时，回退到配置中的 certificate_path / private_key_path
    """

    def __init__(
        self,
        device_config: DeviceConfig,
        data_callback: Optional[Callable[[List[DataPoint]], None]] = None,
        status_callback: Optional[Callable[[str, DeviceStatus, str], None]] = None,
        use_subscription: bool = True,
        cert_manager: Optional[Any] = None,
    ):
        """
        初始化 OPC UA 采集器

        Args:
            device_config: 设备配置
            data_callback: 数据回调
            status_callback: 状态回调
            use_subscription: 是否使用订阅模式
            cert_manager: 证书管理器（可选，推荐传入）
        """
        super().__init__(device_config, data_callback, status_callback)

        self._use_subscription = use_subscription
        self._client: Optional[Client] = None
        self._subscription = None
        self._subscribed_nodes = []
        self._node_cache: Dict[str, Any] = {}
        self._cert_manager = cert_manager

        if not _has_opcua:
            logger.error("opcua 库未安装，OPC UA 采集器无法使用")

    # ============ 证书解析 ============

    def _resolve_certificate(
        self,
        security_mode: str,
        security_policy: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        解析用于安全连接的证书和私钥路径

        优先级：
        1. 显式 certificate_path/private_key_path
        2. 通过 cert_manager 按 cert_name 加载
        3. 通过 cert_manager 获取/生成默认证书
        4. 返回 None（降级为无安全连接）

        Args:
            security_mode: 安全模式
            security_policy: 安全策略

        Returns:
            (cert_path, key_path, server_cert_path)
        """
        if security_mode == 'None' or security_policy == 'None':
            return None, None, None

        conn_cfg = self._config.connection_config or {}

        # 优先级1：显式文件路径
        explicit_cert = conn_cfg.get('certificate_path')
        explicit_key = conn_cfg.get('private_key_path')
        if explicit_cert and explicit_key:
            logger.debug(
                f"OPC UA 使用显式证书: {explicit_cert}"
            )
            return (
                explicit_cert,
                explicit_key,
                conn_cfg.get('server_certificate_path'),
            )

        # 没有 cert_manager → 无法获取证书
        if self._cert_manager is None:
            logger.warning(
                f"设备 {self._config.device_id} 未提供证书路径，"
                "且未接入证书管理器，将尝试无安全连接"
            )
            return None, None, None

        # 优先级2：按 cert_name 加载
        cert_name = conn_cfg.get('cert_name')
        if cert_name:
            cert_info = self._cert_manager.get_certificate(cert_name)
            if cert_info is None:
                logger.warning(
                    f"未找到证书 {cert_name}，将尝试自动生成"
                )
                cert_info = self._cert_manager.generate_self_signed(
                    cert_name=cert_name,
                    common_name=f"Gateway-{self._config.device_id}",
                )
        else:
            # 优先级3：获取默认证书，不存在则自动生成
            cert_info = self._cert_manager.get_default_certificate()
            if cert_info is None:
                logger.info(
                    f"未找到默认证书，为设备 {self._config.device_id} 自动生成"
                )
                cert_info = self._cert_manager.generate_self_signed(
                    cert_name=self._cert_manager._default_cert_name,
                    common_name=f"Industrial-Gateway-Default",
                )

        if cert_info is None:
            logger.error("证书解析失败，无法建立安全连接")
            return None, None, None

        # 验证有效期，临近过期自动续期
        resolved_cert_name = conn_cfg.get('cert_name') or self._cert_manager._default_cert_name
        ok, msg = self._cert_manager.validate_certificate(resolved_cert_name)
        if not ok:
            logger.warning(f"证书校验异常: {msg}，尝试续期")
            try:
                cert_info = self._cert_manager.renew_certificate(
                    cert_name=resolved_cert_name,
                )
            except Exception as e:
                logger.error(f"证书续期失败: {e}")

        # 临近过期告警
        if cert_info.days_remaining <= 30:
            logger.warning(
                f"证书即将过期（剩余 {cert_info.days_remaining} 天），"
                f"请及时续期"
            )

        server_cert_path = conn_cfg.get('server_certificate_path')
        logger.debug(
            f"OPC UA 使用证书管理器提供的证书: {cert_info.cert_path}"
        )
        return cert_info.cert_path, cert_info.key_path, server_cert_path

    # ============ 连接管理 ============

    def connect(self) -> bool:
        """
        连接到 OPC UA 服务器

        Returns:
            bool: 是否连接成功
        """
        if not _has_opcua:
            logger.error("opcua 库未安装")
            return False

        try:
            # 构建连接 URL
            url = f"opc.tcp://{self._config.host}:{self._config.port}"

            # 检查安全配置
            security_mode = self._config.connection_config.get('security_mode', 'None')
            security_policy = self._config.connection_config.get('security_policy', 'None')

            # 创建客户端
            self._client = Client(url=url, timeout=self._config.timeout)

            # 设置安全策略（通过证书管理器优先解析）
            if security_mode != 'None':
                cert_path, key_path, server_cert = self._resolve_certificate(
                    security_mode=security_mode,
                    security_policy=security_policy,
                )

                if cert_path and key_path:
                    try:
                        self._client.set_security(
                            getattr(ua, f'SecurityPolicy{security_policy}'),
                            cert_path,
                            key_path,
                            server_certificate=server_cert,
                            mode=getattr(ua, f'MessageSecurityMode_{security_mode}'),
                        )
                        logger.debug(
                            f"OPC UA 安全模式已设置: {security_mode}/{security_policy}"
                        )
                    except Exception as sec_e:
                        logger.warning(
                            f"设置 OPC UA 安全策略失败，将尝试无安全连接: {sec_e}"
                        )
                else:
                    logger.warning(
                        "未获取到可用证书，将降级为无安全连接"
                    )

            # 身份验证
            username = self._config.connection_config.get('username')
            password = self._config.connection_config.get('password')
            if username and password:
                self._client.set_user(username, password)

            # 连接
            self._client.connect()

            # 获取基础信息
            server_node = self._client.get_server_node()
            logger.debug(f"OPC UA 服务器节点: {server_node}")

            self._is_connected = True
            logger.info(
                f"OPC UA 连接成功: {self._config.device_id} ({url})"
            )
            return True

        except Exception as e:
            logger.error(
                f"OPC UA 连接失败 {self._config.device_id}: {e}"
            )
            self._is_connected = False
            return False

    def disconnect(self) -> None:
        """断开 OPC UA 连接"""
        try:
            # 取消订阅
            if self._subscription:
                try:
                    self._subscription.delete()
                except Exception:
                    pass
                self._subscription = None
                self._subscribed_nodes = []

            # 断开连接
            if self._client:
                try:
                    self._client.disconnect()
                except Exception:
                    pass
                self._client = None

            self._node_cache.clear()
            self._is_connected = False
            logger.info(f"OPC UA 已断开: {self._config.device_id}")

        except Exception as e:
            logger.error(f"OPC UA 断开连接异常: {e}")

    # ============ 点位读取 ============

    def _get_node(self, node_id: str):
        """
        获取节点对象（带缓存）

        Args:
            node_id: 节点ID

        Returns:
            节点对象
        """
        if self._client is None:
            return None

        if node_id in self._node_cache:
            return self._node_cache[node_id]

        try:
            node = self._client.get_node(node_id)
            self._node_cache[node_id] = node
            return node
        except Exception as e:
            logger.warning(f"获取节点失败 {node_id}: {e}")
            return None

    def read_point(self, point: PointConfig) -> Optional[Any]:
        """
        读取单个点位

        Args:
            point: 点位配置

        Returns:
            原始值，失败返回 None
        """
        if not self._is_connected or self._client is None:
            return None

        try:
            node = self._get_node(point.address)
            if node is None:
                return None

            value = node.get_value()
            return value

        except Exception as e:
            logger.debug(f"读取点位失败 {point.point_id}: {e}")
            return None

    def read_batch(self, points: List[PointConfig]) -> Dict[str, Any]:
        """
        批量读取点位

        Args:
            points: 点位配置列表

        Returns:
            {point_id: value} 字典
        """
        if not self._is_connected or self._client is None:
            return {}

        results: Dict[str, Any] = {}

        try:
            # 构建节点列表
            nodes = []
            point_map = {}  # node_id -> point_id

            for point in points:
                node = self._get_node(point.address)
                if node is not None:
                    nodes.append(node)
                    point_map[point.address] = point.point_id

            if not nodes:
                return {}

            # 批量读取
            values = self._client.get_values(nodes, [ua.AttributeIds.Value] * len(nodes))

            for i, node in enumerate(nodes):
                if i < len(values) and values[i] is not None:
                    node_id = str(node.nodeid)
                    point_id = point_map.get(node_id)
                    if point_id:
                        results[point_id] = values[i]

            return results

        except Exception as e:
            logger.warning(f"批量读取失败: {e}")
            # 回退到单点读取
            for point in points:
                val = self.read_point(point)
                if val is not None:
                    results[point.point_id] = val
            return results

    # ============ 订阅管理 ============

    def _setup_subscription(self) -> bool:
        """
        设置数据订阅

        Returns:
            bool: 是否成功
        """
        if not self._is_connected or self._client is None:
            return False

        if not self._use_subscription:
            return False

        try:
            # 清除旧订阅
            if self._subscription:
                try:
                    self._subscription.delete()
                except Exception:
                    pass
                self._subscription = None

            # 创建订阅处理器
            points_dict = {p.point_id: p for p in self._config.get_enabled_points()}
            handler = OPCUASubscriptionHandler(
                device_id=self._config.device_id,
                points=points_dict,
                data_callback=self._data_callback,
            )

            # 创建订阅
            self._subscription = self._client.create_subscription(
                period=1000,  # 发布间隔（毫秒）
                handler=handler,
            )

            # 订阅节点
            nodes = []
            for point in self._config.get_enabled_points():
                node = self._get_node(point.address)
                if node is not None:
                    nodes.append(node)

            if nodes:
                self._subscription.subscribe_data_change(nodes)
                self._subscribed_nodes = nodes
                logger.info(
                    f"OPC UA 订阅设置成功: {self._config.device_id}, "
                    f"订阅节点数: {len(nodes)}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"设置 OPC UA 订阅失败: {e}")
            return False

    # ============ 重写基类方法 ============

    def start(self) -> bool:
        """
        启动采集器

        Returns:
            bool: 是否启动成功
        """
        if not _has_opcua:
            logger.error("opcua 库未安装，无法启动 OPC UA 采集器")
            return False

        if not super().start():
            return False

        # 设置订阅（如果启用）
        if self._use_subscription:
            self._setup_subscription()

        return True

    def stop(self) -> None:
        """停止采集器"""
        # 取消订阅
        if self._subscription:
            try:
                self._subscription.delete()
            except Exception:
                pass
            self._subscription = None
            self._subscribed_nodes = []

        super().stop()

    # ============ 节点浏览 ============

    def browse_nodes(self, node_id: str = "i=85", max_level: int = 2) -> List[Dict[str, Any]]:
        """
        浏览节点

        Args:
            node_id: 起始节点ID（默认是 Objects 文件夹）
            max_level: 最大浏览深度

        Returns:
            节点列表
        """
        if not self._is_connected or self._client is None:
            return []

        try:
            node = self._get_node(node_id)
            if node is None:
                return []

            return self._browse_node_recursive(node, 0, max_level)

        except Exception as e:
            logger.error(f"浏览节点失败: {e}")
            return []

    def _browse_node_recursive(self, node, current_level: int, max_level: int) -> List[Dict[str, Any]]:
        """递归浏览节点"""
        result = []

        try:
            children = node.get_children()

            for child in children:
                try:
                    node_info = {
                        'node_id': str(child.nodeid),
                        'display_name': child.get_display_name().Text,
                        'node_class': str(child.get_node_class()),
                        'browse_name': str(child.get_browse_name()),
                    }

                    result.append(node_info)

                    if current_level < max_level - 1:
                        child_nodes = self._browse_node_recursive(
                            child, current_level + 1, max_level
                        )
                        result.extend(child_nodes)

                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"浏览子节点失败: {e}")

        return result

    # ============ 配置更新 ============

    def update_config(self, config: DeviceConfig) -> None:
        """
        更新设备配置

        Args:
            config: 新的设备配置
        """
        super().update_config(config)

        # 如果使用订阅模式，重新设置订阅
        if self._is_running and self._use_subscription:
            try:
                self._setup_subscription()
            except Exception as e:
                logger.warning(f"重新设置订阅失败: {e}")


# 工厂函数
def create_opcua_collector(
    device_config: DeviceConfig,
    data_callback: Optional[Callable[[List[DataPoint]], None]] = None,
    status_callback: Optional[Callable[[str, DeviceStatus, str], None]] = None,
    use_subscription: bool = True,
    cert_manager: Optional[Any] = None,
) -> OPUACollector:
    """
    创建 OPC UA 采集器

    Args:
        device_config: 设备配置
        data_callback: 数据回调
        status_callback: 状态回调
        use_subscription: 是否使用订阅模式
        cert_manager: 证书管理器（推荐传入）

    Returns:
        OPUACollector
    """
    return OPUACollector(
        device_config=device_config,
        data_callback=data_callback,
        status_callback=status_callback,
        use_subscription=use_subscription,
        cert_manager=cert_manager,
    )
