"""
网关数据模型

定义网关配置、设备配置、点位配置、数据点等核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class ProtocolType(str, Enum):
    """协议类型"""
    OPC_UA = "opcua"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"


class DataSourceType(str, Enum):
    """数据写入目标类型"""
    SC_BOLT_DATA = "sc_bolt_data"
    STREAM_INGEST = "stream_ingest"
    BOTH = "both"


class ModbusRegisterType(str, Enum):
    """Modbus 寄存器类型"""
    COIL = "coil"
    DISCRETE_INPUT = "discrete_input"
    HOLDING_REGISTER = "holding_register"
    INPUT_REGISTER = "input_register"


class DataType(str, Enum):
    """数据类型"""
    BOOL = "bool"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"


class GatewayStatus(str, Enum):
    """网关运行状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class DeviceStatus(str, Enum):
    """设备连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class PointStatus(str, Enum):
    """点位采集状态"""
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"
    TIMEOUT = "timeout"


class PLCBrand(str, Enum):
    """PLC 品牌"""
    SIEMENS = "siemens"
    SCHNEIDER = "schneider"
    MITSUBISHI = "mitsubishi"
    OMRON = "omron"
    ALLEN_BRADLEY = "allen_bradley"
    GENERAL = "general"


@dataclass
class PointConfig:
    """
    点位配置

    Attributes:
        point_id: 点位ID（唯一标识）
        sensor_id: 传感器ID（映射到sc_bolt_data的sensor_id）
        name: 点位名称
        description: 描述
        address: 寄存器地址 / OPC UA NodeId
        data_type: 数据类型
        unit: 单位
        scale_factor: 量程缩放因子（原始值 * scale_factor + offset = 实际值）
        offset: 偏移量
        sampling_period: 采样周期（秒）
        enabled: 是否启用
        protocol_config: 协议特定配置
        tags: 标签
    """
    point_id: str
    sensor_id: str
    name: str
    address: str
    data_type: DataType = DataType.FLOAT32
    unit: str = ""
    scale_factor: float = 1.0
    offset: float = 0.0
    sampling_period: float = 1.0
    enabled: bool = True
    description: str = ""
    protocol_config: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def convert_value(self, raw_value: Any) -> float:
        """将原始值转换为实际工程值"""
        try:
            value = float(raw_value)
            return value * self.scale_factor + self.offset
        except (ValueError, TypeError):
            return 0.0


@dataclass
class DeviceConfig:
    """
    设备配置

    Attributes:
        device_id: 设备ID
        name: 设备名称
        protocol: 协议类型
        host: 主机地址
        port: 端口
        slave_id: 从站ID（Modbus）
        timeout: 超时时间（秒）
        retry_count: 重试次数
        points: 点位配置列表
        enabled: 是否启用
        plc_brand: PLC品牌
        connection_config: 连接配置（证书等）
    """
    device_id: str
    name: str
    protocol: ProtocolType
    host: str
    port: int
    slave_id: int = 1
    timeout: float = 5.0
    retry_count: int = 3
    points: List[PointConfig] = field(default_factory=list)
    enabled: bool = True
    plc_brand: PLCBrand = PLCBrand.GENERAL
    connection_config: Dict[str, Any] = field(default_factory=dict)

    def get_enabled_points(self) -> List[PointConfig]:
        """获取启用的点位列表"""
        return [p for p in self.points if p.enabled]


@dataclass
class GatewayConfig:
    """
    网关全局配置

    Attributes:
        gateway_id: 网关ID
        name: 网关名称
        data_target: 数据写入目标
        stream_ingest_url: stream/ingest 接口地址
        cache_enabled: 是否启用断线缓存
        cache_max_size: 缓存最大条数
        cache_dir: 缓存目录
        health_check_interval: 健康检查间隔（秒）
        config_reload_interval: 配置热加载间隔（秒）
        devices: 设备配置列表
    """
    gateway_id: str = "gateway-001"
    name: str = "工业协议采集网关"
    data_target: DataSourceType = DataSourceType.SC_BOLT_DATA
    stream_ingest_url: str = "http://localhost:8000/stream/ingest"
    cache_enabled: bool = True
    cache_max_size: int = 100000
    cache_dir: str = "./data/gateway_cache"
    health_check_interval: int = 30
    config_reload_interval: int = 60
    devices: List[DeviceConfig] = field(default_factory=list)

    def get_enabled_devices(self) -> List[DeviceConfig]:
        """获取启用的设备列表"""
        return [d for d in self.devices if d.enabled]


@dataclass
class DataPoint:
    """
    采集数据点

    Attributes:
        device_id: 设备ID
        point_id: 点位ID
        sensor_id: 传感器ID
        value: 工程值
        raw_value: 原始值
        timestamp: 采集时间戳
        quality: 数据质量（good/bad/uncertain）
        unit: 单位
    """
    device_id: str
    point_id: str
    sensor_id: str
    value: float
    raw_value: Any
    timestamp: datetime
    quality: str = "good"
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "point_id": self.point_id,
            "sensor_id": self.sensor_id,
            "value": self.value,
            "raw_value": self.raw_value,
            "timestamp": self.timestamp.isoformat(),
            "quality": self.quality,
            "unit": self.unit,
        }


@dataclass
class DeviceRuntimeStatus:
    """设备运行时状态"""
    device_id: str
    status: DeviceStatus
    last_connect_time: Optional[datetime] = None
    last_disconnect_time: Optional[datetime] = None
    consecutive_errors: int = 0
    last_error: str = ""
    total_points: int = 0
    active_points: int = 0
    points_sampled: int = 0
    points_failed: int = 0


@dataclass
class PointRuntimeStatus:
    """点位运行时状态"""
    point_id: str
    status: PointStatus
    last_sample_time: Optional[datetime] = None
    last_value: Optional[float] = None
    consecutive_errors: int = 0
    total_samples: int = 0
    failed_samples: int = 0


@dataclass
class GatewayRuntimeStats:
    """网关运行时统计"""
    status: GatewayStatus
    start_time: Optional[datetime] = None
    total_devices: int = 0
    connected_devices: int = 0
    total_points: int = 0
    active_points: int = 0
    total_samples: int = 0
    samples_per_second: float = 0.0
    cache_size: int = 0
    last_health_check: Optional[datetime] = None
    last_config_reload: Optional[datetime] = None
    uptime_seconds: float = 0.0
