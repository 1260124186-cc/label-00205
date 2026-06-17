"""
PLC 品牌模板管理器

提供主流 PLC 品牌的快速配置模板，包括常见点位映射、
寄存器地址约定、默认参数等。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger

from app.gateway.models import (
    PLCBrand,
    ProtocolType,
    DataType,
    PointConfig,
    DeviceConfig,
)


@dataclass
class PLCTemplate:
    """
    PLC 模板

    Attributes:
        brand: PLC 品牌
        model: 型号
        default_protocol: 默认协议
        default_port: 默认端口
        default_data_type: 默认数据类型
        common_points: 常见点位配置
        register_map: 寄存器映射表
    """
    brand: PLCBrand
    model: str
    default_protocol: ProtocolType
    default_port: int
    default_data_type: DataType = DataType.FLOAT32
    common_points: List[Dict[str, Any]] = field(default_factory=list)
    register_map: Dict[str, str] = field(default_factory=dict)


class PLCTemplateManager:
    """
    PLC 模板管理器

    管理各品牌 PLC 的配置模板，支持快速创建设备配置。
    """

    def __init__(self):
        self._templates: Dict[str, PLCTemplate] = {}
        self._register_maps: Dict[PLCBrand, Dict[str, str]] = {}
        self._load_default_templates()
        logger.info("PLC 模板管理器初始化完成")

    def _load_default_templates(self) -> None:
        """加载默认模板"""
        # 西门子模板
        self._templates["siemens_s7_1200"] = PLCTemplate(
            brand=PLCBrand.SIEMENS,
            model="S7-1200",
            default_protocol=ProtocolType.MODBUS_TCP,
            default_port=502,
            default_data_type=DataType.FLOAT32,
            common_points=[
                {
                    "point_id": "motor_speed",
                    "name": "电机转速",
                    "address": "holding_register:100",
                    "data_type": DataType.FLOAT32,
                    "unit": "rpm",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "motor_current",
                    "name": "电机电流",
                    "address": "holding_register:102",
                    "data_type": DataType.FLOAT32,
                    "unit": "A",
                    "scale_factor": 0.1,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "motor_temperature",
                    "name": "电机温度",
                    "address": "holding_register:104",
                    "data_type": DataType.FLOAT32,
                    "unit": "°C",
                    "scale_factor": 0.1,
                    "offset": 0.0,
                    "sampling_period": 5.0,
                },
                {
                    "point_id": "supply_voltage",
                    "name": "供电电压",
                    "address": "holding_register:106",
                    "data_type": DataType.FLOAT32,
                    "unit": "V",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 2.0,
                },
                {
                    "point_id": "output_power",
                    "name": "输出功率",
                    "address": "holding_register:108",
                    "data_type": DataType.FLOAT32,
                    "unit": "kW",
                    "scale_factor": 0.01,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "operating_hours",
                    "name": "运行小时数",
                    "address": "holding_register:110",
                    "data_type": DataType.UINT32,
                    "unit": "h",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 60.0,
                },
                {
                    "point_id": "fault_code",
                    "name": "故障代码",
                    "address": "holding_register:112",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "run_status",
                    "name": "运行状态",
                    "address": "coil:0",
                    "data_type": DataType.BOOL,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
            ],
        )

        # 施耐德模板
        self._templates["schneider_m340"] = PLCTemplate(
            brand=PLCBrand.SCHNEIDER,
            model="Modicon M340",
            default_protocol=ProtocolType.MODBUS_TCP,
            default_port=502,
            default_data_type=DataType.FLOAT32,
            common_points=[
                {
                    "point_id": "analog_input_1",
                    "name": "模拟量输入1",
                    "address": "input_register:0",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "analog_input_2",
                    "name": "模拟量输入2",
                    "address": "input_register:1",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "pressure_1",
                    "name": "压力1",
                    "address": "holding_register:100",
                    "data_type": DataType.FLOAT32,
                    "unit": "MPa",
                    "scale_factor": 0.001,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "flow_rate",
                    "name": "流量",
                    "address": "holding_register:102",
                    "data_type": DataType.FLOAT32,
                    "unit": "m3/h",
                    "scale_factor": 0.01,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "temperature_1",
                    "name": "温度1",
                    "address": "holding_register:104",
                    "data_type": DataType.FLOAT32,
                    "unit": "°C",
                    "scale_factor": 0.1,
                    "offset": 0.0,
                    "sampling_period": 2.0,
                },
                {
                    "point_id": "level_sensor",
                    "name": "液位传感器",
                    "address": "holding_register:106",
                    "data_type": DataType.FLOAT32,
                    "unit": "m",
                    "scale_factor": 0.001,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "valve_position",
                    "name": "阀门开度",
                    "address": "holding_register:108",
                    "data_type": DataType.INT16,
                    "unit": "%",
                    "scale_factor": 0.1,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "di_status",
                    "name": "数字输入状态",
                    "address": "discrete_input:0",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
                {
                    "point_id": "do_status",
                    "name": "数字输出状态",
                    "address": "coil:0",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
            ],
        )

        # 三菱模板
        self._templates["mitsubishi_fx5u"] = PLCTemplate(
            brand=PLCBrand.MITSUBISHI,
            model="FX5U",
            default_protocol=ProtocolType.MODBUS_TCP,
            default_port=502,
            default_data_type=DataType.INT16,
            common_points=[
                {
                    "point_id": "d_register_0",
                    "name": "D寄存器0",
                    "address": "holding_register:0",
                    "data_type": DataType.INT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "d_register_1",
                    "name": "D寄存器1",
                    "address": "holding_register:1",
                    "data_type": DataType.INT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "x_inputs",
                    "name": "X输入",
                    "address": "discrete_input:0",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
                {
                    "point_id": "y_outputs",
                    "name": "Y输出",
                    "address": "coil:0",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
                {
                    "point_id": "m_relay_0",
                    "name": "M继电器0",
                    "address": "holding_register:100",
                    "data_type": DataType.INT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
            ],
        )

        # 欧姆龙模板
        self._templates["omron_nx1p"] = PLCTemplate(
            brand=PLCBrand.OMRON,
            model="NX1P",
            default_protocol=ProtocolType.OPC_UA,
            default_port=4840,
            default_data_type=DataType.INT16,
            common_points=[
                {
                    "point_id": "ci0_0",
                    "name": "CIO 0.00",
                    "address": "ns=2;s=CIO.0.00",
                    "data_type": DataType.BOOL,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
                {
                    "point_id": "d0",
                    "name": "D0",
                    "address": "ns=2;s=D0",
                    "data_type": DataType.INT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "d100",
                    "name": "D100",
                    "address": "ns=2;s=D100",
                    "data_type": DataType.FLOAT32,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "a0",
                    "name": "A0",
                    "address": "ns=2;s=A0",
                    "data_type": DataType.INT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
            ],
        )

        # AB 罗克韦尔模板
        self._templates["allen_bradley_1756"] = PLCTemplate(
            brand=PLCBrand.ALLEN_BRADLEY,
            model="ControlLogix 1756",
            default_protocol=ProtocolType.OPC_UA,
            default_port=49320,
            default_data_type=DataType.FLOAT32,
            common_points=[
                {
                    "point_id": "tag_ai_1",
                    "name": "模拟输入标签1",
                    "address": "ns=2;s=Channel1:0.Data",
                    "data_type": DataType.FLOAT32,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "tag_ai_2",
                    "name": "模拟输入标签2",
                    "address": "ns=2;s=Channel1:1.Data",
                    "data_type": DataType.FLOAT32,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 1.0,
                },
                {
                    "point_id": "tag_di",
                    "name": "数字输入标签",
                    "address": "ns=2;s=DI.Data",
                    "data_type": DataType.UINT32,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
                {
                    "point_id": "tag_do",
                    "name": "数字输出标签",
                    "address": "ns=2;s=DO.Data",
                    "data_type": DataType.UINT32,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 0.5,
                },
                {
                    "point_id": "controller_status",
                    "name": "控制器状态",
                    "address": "ns=2;s=ControllerStatus",
                    "data_type": DataType.UINT16,
                    "unit": "",
                    "scale_factor": 1.0,
                    "offset": 0.0,
                    "sampling_period": 5.0,
                },
            ],
        )

        # 通用模板
        self._templates["general_modbus"] = PLCTemplate(
            brand=PLCBrand.GENERAL,
            model="通用 Modbus TCP",
            default_protocol=ProtocolType.MODBUS_TCP,
            default_port=502,
            default_data_type=DataType.INT16,
            common_points=[],
        )

        logger.debug(f"加载了 {len(self._templates)} 个 PLC 模板")

    def list_templates(self) -> List[Dict[str, str]]:
        """
        列出所有可用模板

        Returns:
            模板列表 [{brand, model, template_id, protocol, port}]
        """
        result = []
        for tid, tpl in self._templates.items():
            result.append({
                "template_id": tid,
                "brand": tpl.brand.value,
                "model": tpl.model,
                "protocol": tpl.default_protocol.value,
                "port": tpl.default_port,
            })
        return result

    def get_template(self, template_id: str) -> Optional[PLCTemplate]:
        """
        获取指定模板

        Args:
            template_id: 模板ID

        Returns:
            PLCTemplate or None
        """
        return self._templates.get(template_id)

    def create_device_from_template(
        self,
        template_id: str,
        device_id: str,
        name: str,
        host: str,
        port: Optional[int] = None,
        slave_id: int = 1,
        sensor_id_prefix: str = "",
    ) -> Optional[DeviceConfig]:
        """
        从模板创建设备配置

        Args:
            template_id: 模板ID
            device_id: 设备ID
            name: 设备名称
            host: 主机地址
            port: 端口（None则使用模板默认值）
            slave_id: 从站ID
            sensor_id_prefix: 传感器ID前缀

        Returns:
            DeviceConfig or None
        """
        template = self._templates.get(template_id)
        if template is None:
            logger.warning(f"模板不存在: {template_id}")
            return None

        # 创建点位配置
        points = []
        for point_info in template.common_points:
            point_id = point_info["point_id"]
            sensor_id = f"{sensor_id_prefix}{point_id}" if sensor_id_prefix else point_id

            point = PointConfig(
                point_id=point_id,
                sensor_id=sensor_id,
                name=point_info["name"],
                address=point_info["address"],
                data_type=point_info.get("data_type", template.default_data_type),
                unit=point_info.get("unit", ""),
                scale_factor=point_info.get("scale_factor", 1.0),
                offset=point_info.get("offset", 0.0),
                sampling_period=point_info.get("sampling_period", 1.0),
                enabled=True,
            )
            points.append(point)

        # 创建设备配置
        device = DeviceConfig(
            device_id=device_id,
            name=name,
            protocol=template.default_protocol,
            host=host,
            port=port if port is not None else template.default_port,
            slave_id=slave_id,
            points=points,
            enabled=True,
            plc_brand=template.brand,
        )

        logger.info(
            f"从模板 {template_id} 创建设备 {device_id}, "
            f"包含 {len(points)} 个点位"
        )
        return device

    def add_custom_template(self, template: PLCTemplate, template_id: str) -> bool:
        """
        添加自定义模板

        Args:
            template: PLC模板
            template_id: 模板ID

        Returns:
            bool
        """
        if template_id in self._templates:
            logger.warning(f"模板已存在，将覆盖: {template_id}")
        self._templates[template_id] = template
        logger.info(f"添加自定义模板: {template_id}")
        return True

    def get_points_by_brand(self, brand: PLCBrand) -> List[Dict[str, Any]]:
        """
        获取指定品牌的常见点位

        Args:
            brand: PLC品牌

        Returns:
            点位配置列表
        """
        points = []
        for template in self._templates.values():
            if template.brand == brand:
                points.extend(template.common_points)
        return points

    def suggest_template(
        self,
        brand: Optional[PLCBrand] = None,
        protocol: Optional[ProtocolType] = None,
    ) -> List[str]:
        """
        推荐模板

        Args:
            brand: PLC品牌（可选）
            protocol: 协议类型（可选）

        Returns:
            推荐的模板ID列表
        """
        candidates = []
        for tid, tpl in self._templates.items():
            match = True
            if brand is not None and tpl.brand != brand:
                match = False
            if protocol is not None and tpl.default_protocol != protocol:
                match = False
            if match:
                candidates.append(tid)
        return candidates


# 全局单例
_template_manager: Optional[PLCTemplateManager] = None


def get_template_manager() -> PLCTemplateManager:
    """
    获取 PLC 模板管理器单例

    Returns:
        PLCTemplateManager
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = PLCTemplateManager()
    return _template_manager
