"""
Modbus 采集器

实现 Modbus TCP 和 Modbus RTU 协议的数据采集，
支持线圈、离散输入、保持寄存器、输入寄存器的读取。
"""

import struct
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Callable
from loguru import logger

from app.gateway.models import (
    DeviceConfig,
    PointConfig,
    DataPoint,
    DeviceStatus,
    DataType,
    ModbusRegisterType,
    ProtocolType,
)
from app.gateway.base_collector import BaseCollector

try:
    from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    _has_pymodbus = True
except ImportError:
    _has_pymodbus = False
    logger.warning("pymodbus 库未安装，Modbus 采集功能不可用")


class ModbusCollector(BaseCollector):
    """
    Modbus 采集器

    支持 Modbus TCP 和 Modbus RTU 协议，
    支持多种寄存器类型和数据类型的读取。
    """

    def __init__(
        self,
        device_config: DeviceConfig,
        data_callback: Optional[Callable[[List[DataPoint]], None]] = None,
        status_callback: Optional[Callable[[str, DeviceStatus, str], None]] = None,
    ):
        """
        初始化 Modbus 采集器

        Args:
            device_config: 设备配置
            data_callback: 数据回调
            status_callback: 状态回调
        """
        super().__init__(device_config, data_callback, status_callback)

        self._client = None
        self._port_type = device_config.protocol

        # 按寄存器类型分组点位
        self._register_groups: Dict[str, List[PointConfig]] = {}

        if not _has_pymodbus:
            logger.error("pymodbus 库未安装，Modbus 采集器无法使用")

    # ============ 连接管理 ============

    def connect(self) -> bool:
        """
        连接到 Modbus 设备

        Returns:
            bool: 是否连接成功
        """
        if not _has_pymodbus:
            logger.error("pymodbus 库未安装")
            return False

        try:
            if self._config.protocol == ProtocolType.MODBUS_TCP:
                self._client = ModbusTcpClient(
                    host=self._config.host,
                    port=self._config.port,
                    timeout=self._config.timeout,
                )
            elif self._config.protocol == ProtocolType.MODBUS_RTU:
                # RTU 模式（串口）
                serial_port = self._config.connection_config.get('serial_port', '/dev/ttyUSB0')
                baudrate = self._config.connection_config.get('baudrate', 9600)
                parity = self._config.connection_config.get('parity', 'N')
                stopbits = self._config.connection_config.get('stopbits', 1)
                bytesize = self._config.connection_config.get('bytesize', 8)

                self._client = ModbusSerialClient(
                    port=serial_port,
                    baudrate=baudrate,
                    parity=parity,
                    stopbits=stopbits,
                    bytesize=bytesize,
                    timeout=self._config.timeout,
                )
            else:
                logger.error(f"不支持的 Modbus 协议: {self._config.protocol}")
                return False

            # 连接
            if hasattr(self._client, 'connect'):
                if not self._client.connect():
                    logger.error(f"Modbus 连接失败: {self._config.device_id}")
                    return False

            self._is_connected = True
            logger.info(
                f"Modbus 连接成功: {self._config.device_id} "
                f"({self._config.host}:{self._config.port})"
            )
            return True

        except Exception as e:
            logger.error(
                f"Modbus 连接失败 {self._config.device_id}: {e}"
            )
            self._is_connected = False
            return False

    def disconnect(self) -> None:
        """断开 Modbus 连接"""
        try:
            if self._client:
                if hasattr(self._client, 'close'):
                    self._client.close()
                self._client = None

            self._is_connected = False
            logger.info(f"Modbus 已断开: {self._config.device_id}")

        except Exception as e:
            logger.error(f"Modbus 断开连接异常: {e}")

    # ============ 地址解析 ============

    def _parse_address(self, address: str) -> Tuple[ModbusRegisterType, int]:
        """
        解析寄存器地址

        支持格式：
        - holding_register:100  -> (保持寄存器, 100)
        - coil:5  -> (线圈, 5)
        - discrete_input:0 -> (离散输入, 0)
        - input_register:10 -> (输入寄存器, 10)
        - 40101  -> (保持寄存器, 100)  (Modicon 格式)
        - 30101  -> (输入寄存器, 100)  (Modicon 格式)
        - 00001  -> (线圈, 0)           (Modicon 格式)
        - 10001  -> (离散输入, 0)      (Modicon 格式)

        Args:
            address: 地址字符串

        Returns:
            (寄存器类型, 地址)
        """
        try:
            # 格式1: type:address
            if ':' in address:
                parts = address.split(':', 1)
                reg_type_str = parts[0].lower().strip()
                addr = int(parts[1].strip())

                reg_type_map = {
                    'coil': ModbusRegisterType.COIL,
                    'coils': ModbusRegisterType.COIL,
                    'discrete_input': ModbusRegisterType.DISCRETE_INPUT,
                    'discrete_inputs': ModbusRegisterType.DISCRETE_INPUT,
                    'holding_register': ModbusRegisterType.HOLDING_REGISTER,
                    'holding_registers': ModbusRegisterType.HOLDING_REGISTER,
                    'input_register': ModbusRegisterType.INPUT_REGISTER,
                    'input_registers': ModbusRegisterType.INPUT_REGISTER,
                }

                reg_type = reg_type_map.get(
                    reg_type_str,
                    ModbusRegisterType.HOLDING_REGISTER,
                )
                return reg_type, addr

            # 格式2: Modicon 地址格式
            if address.isdigit():
                addr_num = int(address)
                if addr_num >= 40000:
                    return ModbusRegisterType.HOLDING_REGISTER, addr_num - 40001
                elif addr_num >= 30000:
                    return ModbusRegisterType.INPUT_REGISTER, addr_num - 30001
                elif addr_num >= 10000:
                    return ModbusRegisterType.DISCRETE_INPUT, addr_num - 10001
                elif addr_num >= 0:
                    return ModbusRegisterType.COIL, addr_num - 1

        except (ValueError, IndexError):
            pass

        # 默认：保持寄存器
        try:
            return ModbusRegisterType.HOLDING_REGISTER, int(address)
        except (ValueError, TypeError):
            return ModbusRegisterType.HOLDING_REGISTER, 0

    # ============ 数据类型解析 ============

    def _parse_register_value(
        self,
        registers: List[int],
        data_type: DataType,
        byte_order: str = 'big',
    ) -> Any:
        """
        解析寄存器值

        Args:
            registers: 寄存器值列表
            data_type: 数据类型
            byte_order: 字节序 (big/little)

        Returns:
            解析后的值
        """
        if not registers:
            return None

        # 根据数据类型确定寄存器数量和格式
        type_info = {
            DataType.BOOL: (1, '?'),
            DataType.INT16: (1, 'h'),
            DataType.UINT16: (1, 'H'),
            DataType.INT32: (2, 'i'),
            DataType.UINT32: (2, 'I'),
            DataType.INT64: (4, 'q'),
            DataType.UINT64: (4, 'Q'),
            DataType.FLOAT32: (2, 'f'),
            DataType.FLOAT64: (4, 'd'),
        }

        info = type_info.get(data_type)
        if info is None:
            # 默认按 UINT16 处理
            return registers[0]

        reg_count, fmt = info

        if len(registers) < reg_count:
            return None

        # 构建字节流
        byte_list = []
        for reg in registers[:reg_count]:
            if byte_order == 'big':
                byte_list.append((reg >> 8) & 0xFF)
                byte_list.append(reg & 0xFF)
            else:
                byte_list.append(reg & 0xFF)
                byte_list.append((reg >> 8) & 0xFF)

        byte_data = bytes(byte_list)

        try:
            if data_type == DataType.BOOL:
                return bool(registers[0])

            # 确定 struct 格式的字节序
            struct_fmt = ('>' if byte_order == 'big' else '<') + fmt
            value = struct.unpack(struct_fmt, byte_data[:struct.calcsize(struct_fmt)])[0]
            return value

        except Exception as e:
            logger.warning(f"解析寄存器值失败: {e}")
            return None

    # ============ 点位读取 ============

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
            reg_type, address = self._parse_address(point.address)
            slave_id = self._config.slave_id
            byte_order = point.protocol_config.get('byte_order', 'big')

            # 计算需要读取的寄存器数量
            reg_count = self._get_register_count(point.data_type)

            # 根据寄存器类型调用不同的读取方法
            if reg_type == ModbusRegisterType.COIL:
                result = self._client.read_coils(
                    address=address,
                    count=max(1, reg_count),
                    slave=slave_id,
                )
                if result.isError():
                    return None
                if point.data_type == DataType.BOOL:
                    return bool(result.bits[0])
                return result.bits[0]

            elif reg_type == ModbusRegisterType.DISCRETE_INPUT:
                result = self._client.read_discrete_inputs(
                    address=address,
                    count=max(1, reg_count),
                    slave=slave_id,
                )
                if result.isError():
                    return None
                if point.data_type == DataType.BOOL:
                    return bool(result.bits[0])
                return result.bits[0]

            elif reg_type == ModbusRegisterType.HOLDING_REGISTER:
                result = self._client.read_holding_registers(
                    address=address,
                    count=reg_count,
                    slave=slave_id,
                )
                if result.isError():
                    return None
                return self._parse_register_value(
                    result.registers, point.data_type, byte_order
                )

            elif reg_type == ModbusRegisterType.INPUT_REGISTER:
                result = self._client.read_input_registers(
                    address=address,
                    count=reg_count,
                    slave=slave_id,
                )
                if result.isError():
                    return None
                return self._parse_register_value(
                    result.registers, point.data_type, byte_order
                )

            return None

        except Exception as e:
            logger.debug(f"读取点位失败 {point.point_id}: {e}")
            return None

    def read_batch(self, points: List[PointConfig]) -> Dict[str, Any]:
        """
        批量读取点位

        按寄存器类型和地址范围优化读取，减少通信次数。

        Args:
            points: 点位配置列表

        Returns:
            {point_id: value} 字典
        """
        if not self._is_connected or self._client is None:
            return {}

        results: Dict[str, Any] = {}

        try:
            # 按寄存器类型和地址分组
            groups = self._group_points_by_range(points)

            for group_key, group_points in groups.items():
                reg_type, start_addr, count = group_key
                slave_id = self._config.slave_id

                try:
                    # 读取连续的寄存器范围
                    if reg_type == ModbusRegisterType.COIL:
                        result = self._client.read_coils(
                            address=start_addr,
                            count=count,
                            slave=slave_id,
                        )
                        if not result.isError():
                            bits = result.bits
                            for point in group_points:
                                _, addr = self._parse_address(point.address)
                                offset = addr - start_addr
                                if 0 <= offset < len(bits):
                                    if point.data_type == DataType.BOOL:
                                        results[point.point_id] = bool(bits[offset])
                                    else:
                                        results[point.point_id] = bits[offset]

                    elif reg_type == ModbusRegisterType.DISCRETE_INPUT:
                        result = self._client.read_discrete_inputs(
                            address=start_addr,
                            count=count,
                            slave=slave_id,
                        )
                        if not result.isError():
                            bits = result.bits
                            for point in group_points:
                                _, addr = self._parse_address(point.address)
                                offset = addr - start_addr
                                if 0 <= offset < len(bits):
                                    if point.data_type == DataType.BOOL:
                                        results[point.point_id] = bool(bits[offset])
                                    else:
                                        results[point.point_id] = bits[offset]

                    elif reg_type == ModbusRegisterType.HOLDING_REGISTER:
                        result = self._client.read_holding_registers(
                            address=start_addr,
                            count=count,
                            slave=slave_id,
                        )
                        if not result.isError():
                            registers = result.registers
                            for point in group_points:
                                _, addr = self._parse_address(point.address)
                                offset = addr - start_addr
                                reg_count = self._get_register_count(point.data_type)
                                byte_order = point.protocol_config.get('byte_order', 'big')

                                if offset + reg_count <= len(registers):
                                    sub_regs = registers[offset:offset + reg_count]
                                    value = self._parse_register_value(
                                        sub_regs, point.data_type, byte_order
                                    )
                                    if value is not None:
                                        results[point.point_id] = value

                    elif reg_type == ModbusRegisterType.INPUT_REGISTER:
                        result = self._client.read_input_registers(
                            address=start_addr,
                            count=count,
                            slave=slave_id,
                        )
                        if not result.isError():
                            registers = result.registers
                            for point in group_points:
                                _, addr = self._parse_address(point.address)
                                offset = addr - start_addr
                                reg_count = self._get_register_count(point.data_type)
                                byte_order = point.protocol_config.get('byte_order', 'big')

                                if offset + reg_count <= len(registers):
                                    sub_regs = registers[offset:offset + reg_count]
                                    value = self._parse_register_value(
                                        sub_regs, point.data_type, byte_order
                                    )
                                    if value is not None:
                                        results[point.point_id] = value

                except Exception as e:
                    logger.debug(f"批量读取组失败 {group_key}: {e}")
                    # 回退到单点读取
                    for point in group_points:
                        if point.point_id not in results:
                            val = self.read_point(point)
                            if val is not None:
                                results[point.point_id] = val

        except Exception as e:
            logger.warning(f"批量读取失败，改用单点读取: {e}")
            for point in points:
                val = self.read_point(point)
                if val is not None:
                    results[point.point_id] = val

        return results

    def _get_register_count(self, data_type: DataType) -> int:
        """
        获取数据类型占用的寄存器数量

        Args:
            data_type: 数据类型

        Returns:
            寄存器数量
        """
        type_counts = {
            DataType.BOOL: 1,
            DataType.INT16: 1,
            DataType.UINT16: 1,
            DataType.INT32: 2,
            DataType.UINT32: 2,
            DataType.INT64: 4,
            DataType.UINT64: 4,
            DataType.FLOAT32: 2,
            DataType.FLOAT64: 4,
            DataType.STRING: 10,  # 字符串默认10个寄存器
        }
        return type_counts.get(data_type, 1)

    def _group_points_by_range(
        self, points: List[PointConfig]
    ) -> Dict[Tuple[ModbusRegisterType, int, int], List[PointConfig]]:
        """
        按寄存器类型和地址范围分组（优化批量读取）

        Args:
            points: 点位列表

        Returns:
            {(寄存器类型, 起始地址, 数量): [点位]}
        """
        # 按寄存器类型分组
        by_type: Dict[ModbusRegisterType, List[Tuple[int, PointConfig]]] = {}

        for point in points:
            reg_type, addr = self._parse_address(point.address)
            if reg_type not in by_type:
                by_type[reg_type] = []
            by_type[reg_type].append((addr, point))

        # 在每个类型内按地址排序，并分组合并连续地址
        groups = {}
        max_gap = 10  # 最大地址间隔，超过则分两组

        for reg_type, addr_points in by_type.items():
            addr_points.sort(key=lambda x: x[0])

            if not addr_points:
                continue

            # 贪心算法分组
            current_group = [addr_points[0]]
            current_start = addr_points[0][0]
            current_end = addr_points[0][0] + self._get_register_count(addr_points[0][1].data_type)

            for i in range(1, len(addr_points)):
                addr, point = addr_points[i]
                point_end = addr + self._get_register_count(point.data_type)

                if addr - current_end <= max_gap:
                    current_group.append(addr_points[i])
                    current_end = max(current_end, point_end)
                else:
                    # 保存当前组
                    key = (reg_type, current_start, current_end - current_start)
                    groups[key] = [p for _, p in current_group]

                    # 开始新组
                    current_group = [addr_points[i]]
                    current_start = addr
                    current_end = point_end

            # 保存最后一组
            key = (reg_type, current_start, current_end - current_start)
            groups[key] = [p for _, p in current_group]

        return groups

    # ============ 写入支持（可选） ============

    def write_coil(self, address: int, value: bool) -> bool:
        """
        写入单个线圈

        Args:
            address: 地址
            value: 值

        Returns:
            bool
        """
        if not self._is_connected or self._client is None:
            return False

        try:
            result = self._client.write_coil(
                address=address,
                value=value,
                slave=self._config.slave_id,
            )
            return not result.isError()
        except Exception as e:
            logger.warning(f"写入线圈失败 {address}: {e}")
            return False

    def write_register(self, address: int, value: int) -> bool:
        """
        写入单个保持寄存器

        Args:
            address: 地址
            value: 值

        Returns:
            bool
        """
        if not self._is_connected or self._client is None:
            return False

        try:
            result = self._client.write_register(
                address=address,
                value=value,
                slave=self._config.slave_id,
            )
            return not result.isError()
        except Exception as e:
            logger.warning(f"写入寄存器失败 {address}: {e}")
            return False

    # ============ 重写基类方法 ============

    def _init_point_schedules(self) -> None:
        """初始化点位调度表（按采集周期分组优化）"""
        super()._init_point_schedules()
        self._build_register_groups()

    def _build_register_groups(self) -> None:
        """构建寄存器分组（用于批量读取优化）"""
        self._register_groups.clear()
        for point in self._config.get_enabled_points():
            period_key = f"{point.sampling_period}"
            if period_key not in self._register_groups:
                self._register_groups[period_key] = []
            self._register_groups[period_key].append(point)


# 工厂函数
def create_modbus_collector(
    device_config: DeviceConfig,
    data_callback: Optional[Callable[[List[DataPoint]], None]] = None,
    status_callback: Optional[Callable[[str, DeviceStatus, str], None]] = None,
) -> ModbusCollector:
    """
    创建 Modbus 采集器

    Args:
        device_config: 设备配置
        data_callback: 数据回调
        status_callback: 状态回调

    Returns:
        ModbusCollector
    """
    return ModbusCollector(
        device_config=device_config,
        data_callback=data_callback,
        status_callback=status_callback,
    )
