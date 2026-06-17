"""
螺栓紧固工艺规程模型

功能:
1. 紧固步骤定义（百分比扭矩法、角度法）
2. 允差带配置（扭矩允差、角度允差、预紧力允差）
3. 交叉紧固顺序生成（4/8/12/16/20/24/32/36 螺栓组）
4. 工艺规程模板库（API 650、ASME PCC-1、GB 150 等标准）
5. 紧固过程模拟与预紧力均匀性评估
6. 工艺 ID 生成与知识库关联

使用示例:
    from app.models.bolt_tightening_process import BoltTighteningProcessModel

    model = BoltTighteningProcessModel()
    # 生成交叉紧固顺序
    sequence = model.generate_cross_tightening_sequence(bolt_count=8)
    # 获取标准工艺规程
    procedure = model.get_standard_procedure("ASME_PCC1_4STEP")
    # 计算角度法旋转角度
    angle = model.calculate_turn_angle(bolt_size="M20", target_preload=150000, lubrication_type="molybdenum_disulfide")
"""

import math
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.utils.config import config
from app.models.bolt_torque_preload import (
    BoltTorquePreloadModel,
    LubricationType,
    LUBRICATION_LABELS,
)


class TighteningMethod(Enum):
    TORQUE_CONTROL = "torque_control"
    ANGLE_CONTROL = "angle_control"
    YIELD_POINT = "yield_point"
    HYDRAULIC_TENSIONING = "hydraulic_tensioning"
    HEATING = "heating"


TIGHTENING_METHOD_LABELS = {
    TighteningMethod.TORQUE_CONTROL: "扭矩控制法",
    TighteningMethod.ANGLE_CONTROL: "角度控制法",
    TighteningMethod.YIELD_POINT: "屈服点法",
    TighteningMethod.HYDRAULIC_TENSIONING: "液压张拉法",
    TighteningMethod.HEATING: "加热法",
}


class ToleranceBandType(Enum):
    TIGHT = "tight"
    NORMAL = "normal"
    LOOSE = "loose"
    CUSTOM = "custom"


@dataclass
class ToleranceBand:
    """
    允差带配置
    """
    torque_tolerance_pct: float
    angle_tolerance_deg: float
    preload_tolerance_pct: float
    band_type: ToleranceBandType

    def to_dict(self) -> Dict[str, Any]:
        return {
            "torque_tolerance_pct": self.torque_tolerance_pct,
            "angle_tolerance_deg": self.angle_tolerance_deg,
            "preload_tolerance_pct": self.preload_tolerance_pct,
            "band_type": self.band_type.value,
        }


DEFAULT_TOLERANCE_BANDS: Dict[ToleranceBandType, ToleranceBand] = {
    ToleranceBandType.TIGHT: ToleranceBand(
        torque_tolerance_pct=5.0,
        angle_tolerance_deg=3.0,
        preload_tolerance_pct=8.0,
        band_type=ToleranceBandType.TIGHT,
    ),
    ToleranceBandType.NORMAL: ToleranceBand(
        torque_tolerance_pct=10.0,
        angle_tolerance_deg=5.0,
        preload_tolerance_pct=15.0,
        band_type=ToleranceBandType.NORMAL,
    ),
    ToleranceBandType.LOOSE: ToleranceBand(
        torque_tolerance_pct=15.0,
        angle_tolerance_deg=10.0,
        preload_tolerance_pct=20.0,
        band_type=ToleranceBandType.LOOSE,
    ),
}


@dataclass
class TighteningStep:
    """
    紧固步骤定义
    """
    step_number: int
    step_name: str
    method: TighteningMethod
    torque_target_pct: Optional[float] = None
    torque_absolute_Nm: Optional[float] = None
    angle_target_deg: Optional[float] = None
    angle_from_snug: bool = False
    hold_time_seconds: float = 0.0
    pass_number: int = 1
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "method": self.method.value,
            "method_label": TIGHTENING_METHOD_LABELS[self.method],
            "torque_target_pct": self.torque_target_pct,
            "torque_absolute_Nm": self.torque_absolute_Nm,
            "angle_target_deg": self.angle_target_deg,
            "angle_from_snug": self.angle_from_snug,
            "hold_time_seconds": self.hold_time_seconds,
            "pass_number": self.pass_number,
            "description": self.description,
        }


@dataclass
class TighteningProcedure:
    """
    紧固工艺规程
    """
    procedure_id: str
    procedure_name: str
    standard_code: str
    standard_version: str
    description: str
    steps: List[TighteningStep]
    tolerance_band: ToleranceBand
    requires_cross_sequence: bool
    min_bolt_count: int
    max_bolt_count: int
    applicable_bolt_sizes: List[str]
    lubrication_requirements: List[str]
    tool_requirements: List[str]
    safety_notes: List[str]
    associated_knowledge_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "procedure_name": self.procedure_name,
            "standard_code": self.standard_code,
            "standard_version": self.standard_version,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "tolerance_band": self.tolerance_band.to_dict(),
            "requires_cross_sequence": self.requires_cross_sequence,
            "min_bolt_count": self.min_bolt_count,
            "max_bolt_count": self.max_bolt_count,
            "applicable_bolt_sizes": self.applicable_bolt_sizes,
            "lubrication_requirements": self.lubrication_requirements,
            "tool_requirements": self.tool_requirements,
            "safety_notes": self.safety_notes,
            "associated_knowledge_tags": self.associated_knowledge_tags,
        }


@dataclass
class TighteningSequenceResult:
    """
    紧固顺序生成结果
    """
    bolt_count: int
    sequence: List[int]
    sequence_by_pass: List[List[int]]
    pass_count: int
    pattern_type: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bolt_count": self.bolt_count,
            "sequence": self.sequence,
            "sequence_labeled": [f"B#{b}" for b in self.sequence],
            "sequence_by_pass": self.sequence_by_pass,
            "sequence_by_pass_labeled": [
                [f"B#{b}" for b in p] for p in self.sequence_by_pass
            ],
            "pass_count": self.pass_count,
            "pattern_type": self.pattern_type,
            "description": self.description,
        }


@dataclass
class TurnAngleResult:
    """
    角度法旋转角度计算结果
    """
    bolt_size: str
    target_preload_N: float
    pitch_mm: float
    snug_torque_Nm: float
    turn_angle_deg: float
    turn_angle_min_deg: float
    turn_angle_max_deg: float
    elastic_deformation_um: float
    calculation_method: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bolt_size": self.bolt_size,
            "target_preload_N": round(self.target_preload_N, 2),
            "target_preload_kN": round(self.target_preload_N / 1000, 2),
            "pitch_mm": self.pitch_mm,
            "snug_torque_Nm": round(self.snug_torque_Nm, 2),
            "turn_angle_deg": round(self.turn_angle_deg, 1),
            "turn_angle_min_deg": round(self.turn_angle_min_deg, 1),
            "turn_angle_max_deg": round(self.turn_angle_max_deg, 1),
            "elastic_deformation_um": round(self.elastic_deformation_um, 1),
            "calculation_method": self.calculation_method,
        }


def _build_standard_procedures() -> Dict[str, TighteningProcedure]:
    """
    构建标准工艺规程库
    """
    procedures: Dict[str, TighteningProcedure] = {}

    # ASME PCC-1 4步扭矩法
    procedures["ASME_PCC1_4STEP"] = TighteningProcedure(
        procedure_id="ASME_PCC1_4STEP",
        procedure_name="ASME PCC-1 四步扭矩法",
        standard_code="ASME PCC-1",
        standard_version="2019",
        description="ASME PCC-1 推荐的四步十字交叉紧固法，适用于大多数压力边界法兰连接",
        steps=[
            TighteningStep(1, "初步就位", TighteningMethod.TORQUE_CONTROL, torque_target_pct=20, pass_number=1, description="手动预紧至贴合"),
            TighteningStep(2, "第一遍预紧", TighteningMethod.TORQUE_CONTROL, torque_target_pct=50, pass_number=1, description="按十字交叉顺序紧固至50%目标扭矩"),
            TighteningStep(3, "第二遍预紧", TighteningMethod.TORQUE_CONTROL, torque_target_pct=80, pass_number=2, description="按十字交叉顺序紧固至80%目标扭矩"),
            TighteningStep(4, "最终紧固", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=3, description="按十字交叉顺序紧固至100%目标扭矩"),
            TighteningStep(5, "顺圆验证", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=4, description="顺时针逐颗复紧验证，无顺序要求"),
        ],
        tolerance_band=DEFAULT_TOLERANCE_BANDS[ToleranceBandType.NORMAL],
        requires_cross_sequence=True,
        min_bolt_count=4,
        max_bolt_count=64,
        applicable_bolt_sizes=["M12", "M16", "M20", "M24", "M27", "M30", "M33", "M36", "M39", "M42", "M45", "M48", "M52", "M56", "M60", "M64"],
        lubrication_requirements=[
            "使用符合 ASME PCC-1 附录要求的润滑剂",
            "螺纹和支承面均需均匀涂抹",
            "摩擦系数偏差 ≤ ±10%",
        ],
        tool_requirements=[
            "经校准的扭矩扳手（精度 ±3%）",
            "套筒、转接头等配套工具",
        ],
        safety_notes=[
            "佩戴安全防护装备",
            "禁止超过扳手额定扭矩",
            "高压法兰需双人操作确认",
        ],
        associated_knowledge_tags=["ASME_PCC1", "扭矩法", "法兰紧固", "四步法"],
    )

    # ASME PCC-1 扭矩+角度法
    procedures["ASME_PCC1_TORQUE_ANGLE"] = TighteningProcedure(
        procedure_id="ASME_PCC1_TORQUE_ANGLE",
        procedure_name="ASME PCC-1 扭矩+角度控制法",
        standard_code="ASME PCC-1",
        standard_version="2019",
        description="先达到贴合扭矩后旋转指定角度，适用于高精度预紧力要求场合",
        steps=[
            TighteningStep(1, "贴合扭矩", TighteningMethod.TORQUE_CONTROL, torque_target_pct=30, pass_number=1, description="按顺序紧固至贴合扭矩（约30%目标扭矩对应值）"),
            TighteningStep(2, "角度旋转", TighteningMethod.ANGLE_CONTROL, angle_target_deg=180, angle_from_snug=True, pass_number=1, description="从贴合扭矩位置旋转指定角度"),
            TighteningStep(3, "最终验证", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=2, description="顺圆验证最终扭矩值"),
        ],
        tolerance_band=DEFAULT_TOLERANCE_BANDS[ToleranceBandType.TIGHT],
        requires_cross_sequence=True,
        min_bolt_count=4,
        max_bolt_count=64,
        applicable_bolt_sizes=["M16", "M20", "M24", "M27", "M30", "M33", "M36", "M39", "M42", "M45", "M48"],
        lubrication_requirements=[
            "必须使用经过验证的润滑剂",
            "每批次螺栓需做摩擦系数测试",
            "摩擦系数范围: 0.08 ~ 0.14",
        ],
        tool_requirements=[
            "扭矩-角度一体机（精度 ±2%扭矩, ±1°角度）",
            "角度指示器或电子转角仪",
        ],
        safety_notes=[
            "确认贴合扭矩后方可开始角度计量",
            "防止超过弹性极限",
        ],
        associated_knowledge_tags=["ASME_PCC1", "角度法", "高精度", "扭矩角度"],
    )

    # API 650 储罐法兰紧固
    procedures["API_650_5STEP"] = TighteningProcedure(
        procedure_id="API_650_5STEP",
        procedure_name="API 650 储罐法兰五步法",
        standard_code="API 650",
        standard_version="12th",
        description="API 650 焊接储罐法兰紧固工艺，包含热水试运转后复紧要求",
        steps=[
            TighteningStep(1, "手工就位", TighteningMethod.TORQUE_CONTROL, torque_target_pct=10, pass_number=1, description="手工拧紧螺母使垫片就位"),
            TighteningStep(2, "第一遍(30%)", TighteningMethod.TORQUE_CONTROL, torque_target_pct=30, pass_number=1, description="十字交叉顺序至30%目标扭矩"),
            TighteningStep(3, "第二遍(60%)", TighteningMethod.TORQUE_CONTROL, torque_target_pct=60, pass_number=2, description="十字交叉顺序至60%目标扭矩"),
            TighteningStep(4, "第三遍(100%)", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=3, description="十字交叉顺序至100%目标扭矩"),
            TighteningStep(5, "顺圆复紧", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=4, description="顺时针逐颗复紧至目标扭矩"),
            TighteningStep(6, "热态复紧", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=5, description="充水试验或运行温度稳定后复紧"),
        ],
        tolerance_band=DEFAULT_TOLERANCE_BANDS[ToleranceBandType.NORMAL],
        requires_cross_sequence=True,
        min_bolt_count=8,
        max_bolt_count=128,
        applicable_bolt_sizes=["M16", "M20", "M24", "M27", "M30", "M33", "M36", "M39", "M42", "M45", "M48", "M52", "M56", "M60", "M64"],
        lubrication_requirements=[
            "螺栓螺纹与螺母支承面涂石墨基润滑剂",
            "运行温度 > 200°C 使用高温润滑剂",
        ],
        tool_requirements=[
            "经校准的扭矩扳手（精度 ±4%）",
            "液压扳手或冲击扳手（大规格螺栓）",
        ],
        safety_notes=[
            "大直径法兰分区域对称紧固",
            "热态复紧需在温度稳定后进行",
            "充水试验期间监测泄漏",
        ],
        associated_knowledge_tags=["API_650", "储罐", "热态复紧", "法兰"],
    )

    # GB 150 压力容器紧固
    procedures["GB150_TORQUE_METHOD"] = TighteningProcedure(
        procedure_id="GB150_TORQUE_METHOD",
        procedure_name="GB 150 压力容器扭矩法",
        standard_code="GB 150",
        standard_version="2011",
        description="GB 150 钢制压力容器法兰紧固规程，分多步递增",
        steps=[
            TighteningStep(1, "对称预紧", TighteningMethod.TORQUE_CONTROL, torque_target_pct=25, pass_number=1, description="对称预紧至25%"),
            TighteningStep(2, "第一遍(50%)", TighteningMethod.TORQUE_CONTROL, torque_target_pct=50, pass_number=1, description="十字交叉至50%"),
            TighteningStep(3, "第二遍(75%)", TighteningMethod.TORQUE_CONTROL, torque_target_pct=75, pass_number=2, description="十字交叉至75%"),
            TighteningStep(4, "最终(100%)", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=3, description="十字交叉至100%"),
            TighteningStep(5, "顺序检查", TighteningMethod.TORQUE_CONTROL, torque_target_pct=100, pass_number=4, description="按编号顺序逐颗检查"),
        ],
        tolerance_band=DEFAULT_TOLERANCE_BANDS[ToleranceBandType.NORMAL],
        requires_cross_sequence=True,
        min_bolt_count=4,
        max_bolt_count=48,
        applicable_bolt_sizes=["M12", "M16", "M20", "M24", "M27", "M30", "M33", "M36", "M39", "M42", "M45", "M48"],
        lubrication_requirements=[
            "使用二硫化钼或等效润滑剂",
            "重复使用的螺栓需重新涂润滑剂",
        ],
        tool_requirements=[
            "计量合格的扭矩工具",
            "液压张拉器（可选，大直径螺栓）",
        ],
        safety_notes=[
            "超高压容器使用液压张拉器",
            "紧固过程监测法兰间隙均匀性",
        ],
        associated_knowledge_tags=["GB150", "压力容器", "扭矩法"],
    )

    # VDI 2230 液压张拉法
    procedures["VDI2230_HYDRAULIC"] = TighteningProcedure(
        procedure_id="VDI2230_HYDRAULIC",
        procedure_name="VDI 2230 液压张拉法",
        standard_code="VDI 2230",
        standard_version="2015",
        description="VDI 2230 推荐的高精度液压张拉工艺，适用于关键连接",
        steps=[
            TighteningStep(1, "准备就位", TighteningMethod.HYDRAULIC_TENSIONING, torque_target_pct=10, pass_number=1, description="安装张拉器，手动预紧"),
            TighteningStep(2, "张拉至50%", TighteningMethod.HYDRAULIC_TENSIONING, torque_target_pct=50, pass_number=1, description="对称张拉至50%预紧力"),
            TighteningStep(3, "张拉至100%", TighteningMethod.HYDRAULIC_TENSIONING, torque_target_pct=100, pass_number=2, description="对称张拉至100%预紧力", hold_time_seconds=5),
            TighteningStep(4, "旋紧螺母", TighteningMethod.HYDRAULIC_TENSIONING, pass_number=2, description="保压状态下旋紧螺母至贴合"),
            TighteningStep(5, "压力释放验证", TighteningMethod.HYDRAULIC_TENSIONING, pass_number=3, description="缓慢泄压，检查螺母贴合"),
            TighteningStep(6, "复测预紧力", TighteningMethod.TORQUE_CONTROL, torque_target_pct=95, pass_number=4, description="扭矩法复测或超声波验证"),
        ],
        tolerance_band=DEFAULT_TOLERANCE_BANDS[ToleranceBandType.TIGHT],
        requires_cross_sequence=True,
        min_bolt_count=4,
        max_bolt_count=64,
        applicable_bolt_sizes=["M24", "M27", "M30", "M33", "M36", "M39", "M42", "M45", "M48", "M52", "M56", "M60", "M64"],
        lubrication_requirements=[
            "张拉杆涂耐高温抗咬合剂",
            "螺母支承面使用减摩涂层",
        ],
        tool_requirements=[
            "液压张拉器（匹配螺栓规格）",
            "超高压液压泵（带压力表）",
            "超声波测长仪（可选）",
        ],
        safety_notes=[
            "超高压操作使用防护挡板",
            "分级加压，禁止骤加",
            "确认设备额定压力匹配",
        ],
        associated_knowledge_tags=["VDI2230", "液压张拉", "高精度", "关键连接"],
    )

    return procedures


STANDARD_PROCEDURES: Dict[str, TighteningProcedure] = _build_standard_procedures()


class BoltTighteningProcessModel:
    """
    螺栓紧固工艺规程模型

    核心功能:
    - 工艺规程模板库管理
    - 紧固步骤定义与计算
    - 允差带配置
    - 交叉紧固顺序生成（星型/十字/对称）
    - 角度法旋转角度计算
    - 预紧力均匀性评估
    - 工艺 ID 生成与知识库关联
    """

    def __init__(self):
        self.torque_preload_model = BoltTorquePreloadModel()
        self.custom_procedures: Dict[str, TighteningProcedure] = {}

        tp_cfg = config.get('tightening_process', {})
        self.default_pass_count = tp_cfg.get('default_pass_count', 3)
        self.default_snug_torque_pct = tp_cfg.get('default_snug_torque_pct', 30.0)
        self.default_elastic_modulus_GPa = tp_cfg.get('default_elastic_modulus_GPa', 206.0)

        logger.info("螺栓紧固工艺规程模型初始化完成")

    def list_standard_procedures(self) -> List[Dict[str, Any]]:
        return [
            {
                "procedure_id": p.procedure_id,
                "procedure_name": p.procedure_name,
                "standard_code": p.standard_code,
                "standard_version": p.standard_version,
                "description": p.description,
                "requires_cross_sequence": p.requires_cross_sequence,
                "min_bolt_count": p.min_bolt_count,
                "max_bolt_count": p.max_bolt_count,
                "step_count": len(p.steps),
                "associated_knowledge_tags": p.associated_knowledge_tags,
            }
            for p in STANDARD_PROCEDURES.values()
        ]

    def get_standard_procedure(self, procedure_id: str) -> Optional[TighteningProcedure]:
        return STANDARD_PROCEDURES.get(procedure_id)

    def get_custom_procedure(self, procedure_id: str) -> Optional[TighteningProcedure]:
        return self.custom_procedures.get(procedure_id)

    def get_procedure(self, procedure_id: str) -> Optional[TighteningProcedure]:
        return self.get_standard_procedure(procedure_id) or self.get_custom_procedure(procedure_id)

    def register_custom_procedure(self, procedure: TighteningProcedure) -> None:
        self.custom_procedures[procedure.procedure_id] = procedure
        logger.info(f"已注册自定义工艺规程: {procedure.procedure_id}")

    def list_tolerance_bands(self) -> List[Dict[str, Any]]:
        return [tb.to_dict() for tb in DEFAULT_TOLERANCE_BANDS.values()]

    def get_tolerance_band(self, band_type: ToleranceBandType) -> ToleranceBand:
        return DEFAULT_TOLERANCE_BANDS.get(band_type, DEFAULT_TOLERANCE_BANDS[ToleranceBandType.NORMAL])

    def list_tightening_methods(self) -> List[Dict[str, Any]]:
        return [
            {"method": m.value, "label": TIGHTENING_METHOD_LABELS[m]}
            for m in TighteningMethod
        ]

    def generate_cross_tightening_sequence(
        self,
        bolt_count: int,
        start_index: int = 1,
        passes: Optional[int] = None,
        pattern: Optional[str] = None,
    ) -> TighteningSequenceResult:
        if bolt_count < 4:
            raise ValueError("螺栓数量必须 >= 4 才能使用交叉紧固法")
        if bolt_count > 128:
            raise ValueError("螺栓数量过大，请确认配置是否正确")

        passes = passes or self.default_pass_count

        if pattern is None:
            if bolt_count <= 6:
                pattern = "star"
            elif bolt_count % 4 == 0:
                pattern = "cross_quadrant"
            elif bolt_count % 2 == 0:
                pattern = "diametral_opposite"
            else:
                pattern = "nearest_neighbor_cross"

        bolts = list(range(start_index, start_index + bolt_count))
        full_sequence: List[int] = []
        sequence_by_pass: List[List[int]] = []

        if pattern == "star" and bolt_count <= 8:
            step = bolt_count // 2 if bolt_count % 2 == 0 else bolt_count // 2 + 1
            pass_seq = []
            visited = set()
            idx = 0
            while len(visited) < bolt_count:
                if idx not in visited:
                    pass_seq.append(bolts[idx])
                    visited.add(idx)
                idx = (idx + step) % bolt_count
            sequence_by_pass.append(pass_seq)
            full_sequence.extend(pass_seq)

            for _ in range(1, passes):
                next_pass = [b for b in bolts if b not in pass_seq]
                if not next_pass:
                    next_pass = bolts[:]
                sequence_by_pass.append(next_pass)
                full_sequence.extend(next_pass)

        elif pattern == "cross_quadrant" and bolt_count % 4 == 0:
            per_quad = bolt_count // 4
            quadrants = [
                bolts[i * per_quad:(i + 1) * per_quad]
                for i in range(4)
            ]
            for p in range(passes):
                pass_seq = []
                for qi in range(per_quad):
                    pass_seq.append(quadrants[0][qi])
                    pass_seq.append(quadrants[2][qi])
                    pass_seq.append(quadrants[1][qi])
                    pass_seq.append(quadrants[3][qi])
                sequence_by_pass.append(pass_seq)
                full_sequence.extend(pass_seq)

        elif pattern == "diametral_opposite" and bolt_count % 2 == 0:
            half = bolt_count // 2
            ordered_pairs = []
            for i in range(half):
                ordered_pairs.append((bolts[i], bolts[i + half]))

            reorder_indices = []
            step = half // 2 if half % 2 == 0 else half // 2 + 1
            visited = set()
            i = 0
            while len(reorder_indices) < half:
                if i not in visited:
                    reorder_indices.append(i)
                    visited.add(i)
                i = (i + step) % half

            for p in range(passes):
                pass_seq = []
                for idx in reorder_indices:
                    a, b = ordered_pairs[idx]
                    pass_seq.append(a)
                    pass_seq.append(b)
                sequence_by_pass.append(pass_seq)
                full_sequence.extend(pass_seq)

        else:
            for p in range(passes):
                pass_seq = []
                step = bolt_count // 2 if bolt_count % 2 == 0 else bolt_count // 2 + 1
                visited = set()
                idx = 0
                while len(visited) < bolt_count:
                    if idx not in visited:
                        pass_seq.append(bolts[idx])
                        visited.add(idx)
                    idx = (idx + step) % bolt_count
                    if len(visited) == bolt_count:
                        break
                sequence_by_pass.append(pass_seq)
                full_sequence.extend(pass_seq)

        pattern_labels = {
            "star": "星型对称法",
            "cross_quadrant": "四象限十字交叉法",
            "diametral_opposite": "径向对顶法",
            "nearest_neighbor_cross": "近似对称交叉法",
        }

        return TighteningSequenceResult(
            bolt_count=bolt_count,
            sequence=full_sequence,
            sequence_by_pass=sequence_by_pass,
            pass_count=len(sequence_by_pass),
            pattern_type=pattern,
            description=pattern_labels.get(pattern, "通用交叉紧固法"),
        )

    def calculate_turn_angle(
        self,
        bolt_size: str,
        target_preload: float,
        lubrication_type: LubricationType = LubricationType.MACHINE_OIL,
        custom_mu_G: Optional[float] = None,
        custom_mu_K: Optional[float] = None,
        effective_length_mm: Optional[float] = None,
        elastic_modulus_GPa: Optional[float] = None,
        washer_outer_diameter: Optional[float] = None,
        nut_type: str = "hex_nut",
        snug_torque_pct: Optional[float] = None,
    ) -> TurnAngleResult:
        bolt_spec = self.torque_preload_model.get_thread_spec(bolt_size)
        if bolt_spec is None:
            raise ValueError(f"未知螺纹规格: {bolt_size}")

        E_GPa = elastic_modulus_GPa or self.default_elastic_modulus_GPa
        E_Pa = E_GPa * 1e9
        pitch = bolt_spec.pitch
        stress_area_m2 = bolt_spec.tensile_stress_area * 1e-6

        target_stress = target_preload / stress_area_m2 if stress_area_m2 > 0 else 0
        strain = target_stress / E_Pa if E_Pa > 0 else 0

        if effective_length_mm is None:
            effective_length_mm = bolt_spec.nominal_diameter * 3.0

        elongation_m = strain * (effective_length_mm * 1e-3)
        elongation_um = elongation_m * 1e6

        turn_angle_deg = (elongation_m / (pitch * 1e-3)) * 360.0 if pitch > 0 else 0

        snug_pct = snug_torque_pct or self.default_snug_torque_pct
        snug_preload = target_preload * (snug_pct / 100.0)

        torque_result = self.torque_preload_model.calculate_torque(
            bolt_size=bolt_size,
            target_preload=target_preload,
            lubrication_type=lubrication_type,
            custom_mu_G=custom_mu_G,
            custom_mu_K=custom_mu_K,
            washer_outer_diameter=washer_outer_diameter,
            nut_type=nut_type,
        )
        snug_torque_Nm = torque_result.nominal_torque * (snug_pct / 100.0)

        tol_band = self.get_tolerance_band(ToleranceBandType.TIGHT)
        turn_angle_min = turn_angle_deg * (1.0 - tol_band.angle_tolerance_deg / 100.0)
        turn_angle_max = turn_angle_deg * (1.0 + tol_band.angle_tolerance_deg / 100.0)

        return TurnAngleResult(
            bolt_size=bolt_size,
            target_preload_N=target_preload,
            pitch_mm=pitch,
            snug_torque_Nm=snug_torque_Nm,
            turn_angle_deg=turn_angle_deg,
            turn_angle_min_deg=turn_angle_min,
            turn_angle_max_deg=turn_angle_max,
            elastic_deformation_um=elongation_um,
            calculation_method="VDI 2230 elastic elongation method",
        )

    def generate_full_procedure(
        self,
        procedure_id: str,
        bolt_size: str,
        target_preload: float,
        bolt_count: int = 8,
        lubrication_type: LubricationType = LubricationType.MACHINE_OIL,
        custom_mu_G: Optional[float] = None,
        custom_mu_K: Optional[float] = None,
        tolerance_band_type: ToleranceBandType = ToleranceBandType.NORMAL,
    ) -> Dict[str, Any]:
        procedure = self.get_procedure(procedure_id)
        if procedure is None:
            raise ValueError(f"未知工艺规程ID: {procedure_id}")

        torque_result = self.torque_preload_model.calculate_torque(
            bolt_size=bolt_size,
            target_preload=target_preload,
            lubrication_type=lubrication_type,
            custom_mu_G=custom_mu_G,
            custom_mu_K=custom_mu_K,
        )
        target_torque_Nm = torque_result.nominal_torque

        resolved_steps: List[Dict[str, Any]] = []
        for step in procedure.steps:
            step_dict = step.to_dict()
            if step.torque_target_pct is not None and target_torque_Nm > 0:
                step_dict["resolved_torque_Nm"] = round(
                    target_torque_Nm * step.torque_target_pct / 100.0, 2
                )
            if step.method == TighteningMethod.ANGLE_CONTROL and step.angle_target_deg is None:
                angle_result = self.calculate_turn_angle(
                    bolt_size=bolt_size,
                    target_preload=target_preload,
                    lubrication_type=lubrication_type,
                    custom_mu_G=custom_mu_G,
                    custom_mu_K=custom_mu_K,
                )
                step_dict["resolved_angle_deg"] = round(angle_result.turn_angle_deg, 1)
                step_dict["snug_torque_Nm"] = round(angle_result.snug_torque_Nm, 2)
            resolved_steps.append(step_dict)

        seq_result = None
        if procedure.requires_cross_sequence and bolt_count >= 4:
            seq_result = self.generate_cross_tightening_sequence(bolt_count)

        tolerance_band = self.get_tolerance_band(tolerance_band_type)

        return {
            "procedure_id": procedure_id,
            "procedure_name": procedure.procedure_name,
            "standard_code": procedure.standard_code,
            "standard_version": procedure.standard_version,
            "bolt_size": bolt_size,
            "bolt_count": bolt_count,
            "target_preload_N": round(target_preload, 2),
            "target_preload_kN": round(target_preload / 1000, 2),
            "target_torque_Nm": round(target_torque_Nm, 2),
            "torque_tolerance_min_Nm": round(
                target_torque_Nm * (1 - tolerance_band.torque_tolerance_pct / 100), 2
            ),
            "torque_tolerance_max_Nm": round(
                target_torque_Nm * (1 + tolerance_band.torque_tolerance_pct / 100), 2
            ),
            "lubrication_type": lubrication_type.value,
            "lubrication_label": LUBRICATION_LABELS[lubrication_type],
            "tolerance_band": tolerance_band.to_dict(),
            "steps": resolved_steps,
            "tightening_sequence": seq_result.to_dict() if seq_result else None,
            "lubrication_requirements": procedure.lubrication_requirements,
            "tool_requirements": procedure.tool_requirements,
            "safety_notes": procedure.safety_notes,
            "associated_knowledge_tags": procedure.associated_knowledge_tags,
        }

    def evaluate_uniformity(
        self,
        measured_preloads: List[float],
        target_preload: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not measured_preloads:
            raise ValueError("预紧力数据不能为空")

        arr = np.array(measured_preloads, dtype=np.float64)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        cv = std_val / mean_val if mean_val > 0 else 0.0
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        range_pct = (max_val - min_val) / mean_val * 100.0 if mean_val > 0 else 0.0

        if target_preload and target_preload > 0:
            deviations = (arr - target_preload) / target_preload * 100.0
            max_deviation = float(np.max(np.abs(deviations)))
            below_target_pct = float(np.sum(arr < target_preload * 0.9) / len(arr) * 100)
        else:
            max_deviation = None
            below_target_pct = None

        quality = "excellent"
        if cv > 0.10:
            quality = "poor"
        elif cv > 0.05:
            quality = "fair"
        elif cv > 0.02:
            quality = "good"

        return {
            "bolt_count": len(arr),
            "mean_preload_N": round(mean_val, 2),
            "mean_preload_kN": round(mean_val / 1000, 2),
            "std_preload_N": round(std_val, 2),
            "coefficient_of_variation": round(cv, 4),
            "min_preload_N": round(min_val, 2),
            "max_preload_N": round(max_val, 2),
            "range_pct": round(range_pct, 2),
            "target_preload_N": round(target_preload, 2) if target_preload else None,
            "max_absolute_deviation_pct": round(max_deviation, 2) if max_deviation is not None else None,
            "below_90pct_target_ratio_pct": round(below_target_pct, 2) if below_target_pct is not None else None,
            "uniformity_quality": quality,
        }

    def generate_process_id(
        self,
        procedure_code: str,
        bolt_size: str,
        timestamp: Optional[str] = None,
    ) -> str:
        from datetime import datetime
        ts = timestamp or datetime.now().strftime("%Y%m%d%H%M%S")
        clean_size = bolt_size.upper().replace(" ", "").replace("X", "x")
        return f"TP-{procedure_code}-{clean_size}-{ts}"
