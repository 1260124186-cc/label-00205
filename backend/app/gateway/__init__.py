"""
工业协议采集网关模块

支持 OPC UA 和 Modbus 协议的数据采集，
提供点位映射、断线缓存、健康监控、配置热加载等功能。
"""

from app.gateway.models import (
    GatewayConfig,
    DeviceConfig,
    PointConfig,
    DataPoint,
    GatewayStatus,
    DeviceStatus,
    PointStatus,
)
from app.gateway.service import IndustrialGatewayService
from app.gateway.config_manager import GatewayConfigManager
from app.gateway.data_writer import GatewayDataWriter
from app.gateway.cache import OfflineCache
from app.gateway.health import GatewayHealthMonitor
from app.gateway.cert_manager import CertificateManager
from app.gateway.templates import PLCTemplateManager

__all__ = [
    "GatewayConfig",
    "DeviceConfig",
    "PointConfig",
    "DataPoint",
    "GatewayStatus",
    "DeviceStatus",
    "PointStatus",
    "IndustrialGatewayService",
    "GatewayConfigManager",
    "GatewayDataWriter",
    "OfflineCache",
    "GatewayHealthMonitor",
    "CertificateManager",
    "PLCTemplateManager",
]
