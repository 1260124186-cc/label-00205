"""
螺栓扭矩-预紧力换算模型

基于 VDI 2230 简化公式的扭矩-预紧力换算库，支持：
1. 公制螺纹规格查表（M6~M64 粗牙/细牙）
2. 摩擦系数查表（螺纹摩擦、支承面摩擦）
3. 润滑状态摩擦系数修正
4. VDI 2230 简化公式计算扭矩→预紧力
5. 反算：实测扭矩→预紧力
6. 预紧力→建议扭矩区间

VDI 2230 简化公式:
    M_A = F_M * (0.159 * P + d_2 * mu_G * 1 / cos(alpha/2) + D_Km * mu_K / 2)
其中:
    M_A = 装配扭矩 (N·m)
    F_M = 预紧力 (N)
    P   = 螺距 (mm)
    d_2 = 螺纹中径 (mm)
    D_Km = 支承面有效摩擦直径 (mm)
    mu_G = 螺纹摩擦系数
    mu_K = 支承面摩擦系数
    alpha = 螺纹牙型角 (公制60°)

使用示例:
    from app.models.bolt_torque_preload import BoltTorquePreloadModel

    model = BoltTorquePreloadModel()
    # 正向计算：目标预紧力 → 扭矩
    result = model.calculate_torque(
        bolt_size="M20",
        target_preload=150000,
        lubrication_type="molybdenum_disulfide"
    )
    # 反向计算：实测扭矩 → 预紧力
    preload = model.calculate_preload_from_torque(
        bolt_size="M20",
        measured_torque=450,
        lubrication_type="molybdenum_disulfide"
    )
"""

import math
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.utils.config import config


class ThreadStandard(Enum):
    METRIC_COARSE = "metric_coarse"
    METRIC_FINE = "metric_fine"


class LubricationType(Enum):
    DRY = "dry"
    MACHINE_OIL = "machine_oil"
    MOLYBDENUM_DISULFIDE = "molybdenum_disulfide"
    GRAPHITE = "graphite"
    TEFLON_COATED = "teflon_coated"
    ANTI_SEIZE = "anti_seize"
    ZINC_FLAKE_COATED = "zinc_flake_coated"
    HOT_DIP_GALVANIZED = "hot_dip_galvanized"


LUBRICATION_LABELS = {
    LubricationType.DRY: "无润滑(干摩擦)",
    LubricationType.MACHINE_OIL: "机械油润滑",
    LubricationType.MOLYBDENUM_DISULFIDE: "二硫化钼润滑",
    LubricationType.GRAPHITE: "石墨润滑",
    LubricationType.TEFLON_COATED: "特氟龙涂层",
    LubricationType.ANTI_SEIZE: "防卡剂",
    LubricationType.ZINC_FLAKE_COATED: "锌片涂层",
    LubricationType.HOT_DIP_GALVANIZED: "热浸镀锌",
}


@dataclass
class ThreadSpec:
    """
    螺纹规格参数
    """
    designation: str
    nominal_diameter: float
    pitch: float
    minor_diameter: float
    pitch_diameter: float
    tensile_stress_area: float
    standard: ThreadStandard

    def to_dict(self) -> Dict[str, Any]:
        return {
            "designation": self.designation,
            "nominal_diameter": self.nominal_diameter,
            "pitch": self.pitch,
            "minor_diameter": self.minor_diameter,
            "pitch_diameter": self.pitch_diameter,
            "tensile_stress_area": self.tensile_stress_area,
            "standard": self.standard.value,
        }


@dataclass
class FrictionCoefficients:
    """
    摩擦系数参数
    """
    mu_G: float
    mu_K: float
    mu_G_min: float
    mu_G_max: float
    mu_K_min: float
    mu_K_max: float
    lubrication_type: LubricationType
    uncertainty_factor: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mu_G": self.mu_G,
            "mu_K": self.mu_K,
            "mu_G_min": self.mu_G_min,
            "mu_G_max": self.mu_G_max,
            "mu_K_min": self.mu_K_min,
            "mu_K_max": self.mu_K_max,
            "lubrication_type": self.lubrication_type.value,
            "lubrication_label": LUBRICATION_LABELS[self.lubrication_type],
            "uncertainty_factor": self.uncertainty_factor,
        }


@dataclass
class TorqueCalculationResult:
    """
    扭矩计算结果
    """
    bolt_spec: ThreadSpec
    friction: FrictionCoefficients
    target_preload: float
    nominal_torque: float
    torque_min: float
    torque_max: float
    torque_tolerance_pct: float
    tightening_factor: float
    dKm: float
    formula_components: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bolt_spec": self.bolt_spec.to_dict(),
            "friction": self.friction.to_dict(),
            "target_preload_N": round(self.target_preload, 2),
            "target_preload_kN": round(self.target_preload / 1000, 2),
            "nominal_torque_Nm": round(self.nominal_torque, 2),
            "torque_min_Nm": round(self.torque_min, 2),
            "torque_max_Nm": round(self.torque_max, 2),
            "torque_tolerance_pct": round(self.torque_tolerance_pct, 2),
            "tightening_factor_alpha_A": round(self.tightening_factor, 3),
            "support_diameter_DKm_mm": round(self.dKm, 3),
            "formula_components": {
                k: round(v, 4) for k, v in self.formula_components.items()
            },
        }


@dataclass
class PreloadCalculationResult:
    """
    预紧力反算结果
    """
    bolt_spec: ThreadSpec
    friction: FrictionCoefficients
    measured_torque: float
    calculated_preload: float
    preload_min: float
    preload_max: float
    preload_uncertainty_pct: float
    dKm: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bolt_spec": self.bolt_spec.to_dict(),
            "friction": self.friction.to_dict(),
            "measured_torque_Nm": round(self.measured_torque, 2),
            "calculated_preload_N": round(self.calculated_preload, 2),
            "calculated_preload_kN": round(self.calculated_preload / 1000, 2),
            "preload_min_N": round(self.preload_min, 2),
            "preload_min_kN": round(self.preload_min / 1000, 2),
            "preload_max_N": round(self.preload_max, 2),
            "preload_max_kN": round(self.preload_max / 1000, 2),
            "preload_uncertainty_pct": round(self.preload_uncertainty_pct, 2),
            "support_diameter_DKm_mm": round(self.dKm, 3),
        }


METRIC_COARSE_THREADS: Dict[str, ThreadSpec] = {}
METRIC_FINE_THREADS: Dict[str, ThreadSpec] = {}


def _init_thread_tables() -> None:
    """
    初始化公制螺纹规格表 (ISO 724 / GB/T 196)

    参数来源: ISO 724-1993 公制螺纹 基本尺寸
    抗拉应力面积 As = (pi/4) * ((d2 + d3)/2)^2 (VDI 2230 简化)
    """
    coarse_specs = [
        ("M6", 6.0, 1.0, 4.917, 5.350, 20.1),
        ("M8", 8.0, 1.25, 6.647, 7.188, 39.7),
        ("M10", 10.0, 1.5, 8.376, 9.026, 64.5),
        ("M12", 12.0, 1.75, 10.106, 10.863, 94.6),
        ("M14", 14.0, 2.0, 11.835, 12.701, 129.3),
        ("M16", 16.0, 2.0, 13.835, 14.701, 167.2),
        ("M18", 18.0, 2.5, 15.294, 16.376, 204.6),
        ("M20", 20.0, 2.5, 17.294, 18.376, 257.8),
        ("M22", 22.0, 2.5, 19.294, 20.376, 317.6),
        ("M24", 24.0, 3.0, 20.752, 22.052, 375.7),
        ("M27", 27.0, 3.0, 23.752, 25.052, 495.7),
        ("M30", 30.0, 3.5, 26.211, 27.727, 616.1),
        ("M33", 33.0, 3.5, 29.211, 30.727, 758.9),
        ("M36", 36.0, 4.0, 31.670, 33.402, 889.8),
        ("M39", 39.0, 4.0, 34.670, 36.402, 1055.6),
        ("M42", 42.0, 4.5, 37.129, 39.077, 1228.6),
        ("M45", 45.0, 4.5, 40.129, 42.077, 1431.6),
        ("M48", 48.0, 5.0, 42.588, 44.752, 1640.7),
        ("M52", 52.0, 5.0, 46.588, 48.752, 1965.7),
        ("M56", 56.0, 5.5, 49.047, 51.428, 2292.3),
        ("M60", 60.0, 5.5, 53.047, 55.428, 2718.8),
        ("M64", 64.0, 6.0, 55.506, 58.103, 3154.9),
    ]

    fine_specs = [
        ("M8x1", 8.0, 1.0, 6.917, 7.350, 42.7),
        ("M10x1", 10.0, 1.0, 8.917, 9.350, 70.0),
        ("M10x1.25", 10.0, 1.25, 8.647, 9.188, 67.4),
        ("M12x1.25", 12.0, 1.25, 10.647, 11.188, 102.1),
        ("M12x1.5", 12.0, 1.5, 10.376, 11.026, 98.7),
        ("M14x1.5", 14.0, 1.5, 12.376, 13.026, 138.4),
        ("M16x1.5", 16.0, 1.5, 14.376, 15.026, 182.5),
        ("M18x1.5", 18.0, 1.5, 16.376, 17.026, 231.6),
        ("M20x1.5", 20.0, 1.5, 18.376, 19.026, 286.5),
        ("M20x2", 20.0, 2.0, 17.835, 18.701, 279.6),
        ("M22x1.5", 22.0, 1.5, 20.376, 21.026, 346.4),
        ("M24x2", 24.0, 2.0, 21.835, 22.701, 405.8),
        ("M27x2", 27.0, 2.0, 24.835, 25.701, 532.5),
        ("M30x2", 30.0, 2.0, 27.835, 28.701, 674.0),
        ("M30x3", 30.0, 3.0, 26.752, 28.052, 646.0),
        ("M33x2", 33.0, 2.0, 30.835, 31.701, 829.7),
        ("M36x3", 36.0, 3.0, 32.752, 34.052, 915.3),
        ("M39x3", 39.0, 3.0, 35.752, 37.052, 1088.4),
        ("M42x3", 42.0, 3.0, 38.752, 40.052, 1275.9),
        ("M45x3", 45.0, 3.0, 41.752, 43.052, 1478.4),
        ("M48x3", 48.0, 3.0, 44.752, 46.052, 1695.9),
        ("M52x3", 52.0, 3.0, 48.752, 50.052, 2005.9),
        ("M56x4", 56.0, 4.0, 51.670, 53.402, 2322.8),
        ("M60x4", 60.0, 4.0, 55.670, 57.402, 2760.3),
        ("M64x4", 64.0, 4.0, 59.670, 61.402, 3227.8),
    ]

    for d, nom, p, d1, d2, As in coarse_specs:
        METRIC_COARSE_THREADS[d] = ThreadSpec(
            designation=d,
            nominal_diameter=nom,
            pitch=p,
            minor_diameter=d1,
            pitch_diameter=d2,
            tensile_stress_area=As,
            standard=ThreadStandard.METRIC_COARSE,
        )

    for d, nom, p, d1, d2, As in fine_specs:
        METRIC_FINE_THREADS[d] = ThreadSpec(
            designation=d,
            nominal_diameter=nom,
            pitch=p,
            minor_diameter=d1,
            pitch_diameter=d2,
            tensile_stress_area=As,
            standard=ThreadStandard.METRIC_FINE,
        )


_init_thread_tables()


FRICTION_TABLE: Dict[LubricationType, FrictionCoefficients] = {}


def _init_friction_table() -> None:
    """
    初始化摩擦系数表 (参考 VDI 2230 Part 1, Table A4 / ISO 16047)

    典型摩擦系数:
    - mu_G: 螺纹摩擦系数
    - mu_K: 支承面摩擦系数
    - 范围: min ~ max (用于不确定度计算)
    """
    friction_data = [
        (LubricationType.DRY, 0.14, 0.16, 0.10, 0.18, 0.12, 0.20, 1.6),
        (LubricationType.MACHINE_OIL, 0.12, 0.14, 0.08, 0.16, 0.10, 0.18, 1.4),
        (LubricationType.MOLYBDENUM_DISULFIDE, 0.10, 0.10, 0.07, 0.13, 0.07, 0.13, 1.25),
        (LubricationType.GRAPHITE, 0.11, 0.13, 0.08, 0.14, 0.10, 0.16, 1.3),
        (LubricationType.TEFLON_COATED, 0.08, 0.08, 0.05, 0.11, 0.05, 0.11, 1.2),
        (LubricationType.ANTI_SEIZE, 0.10, 0.12, 0.07, 0.13, 0.09, 0.15, 1.25),
        (LubricationType.ZINC_FLAKE_COATED, 0.12, 0.15, 0.09, 0.15, 0.12, 0.18, 1.35),
        (LubricationType.HOT_DIP_GALVANIZED, 0.20, 0.22, 0.15, 0.25, 0.17, 0.28, 1.8),
    ]

    for lub, muG, muK, muG_min, muG_max, muK_min, muK_max, unc in friction_data:
        FRICTION_TABLE[lub] = FrictionCoefficients(
            mu_G=muG,
            mu_K=muK,
            mu_G_min=muG_min,
            mu_G_max=muG_max,
            mu_K_min=muK_min,
            mu_K_max=muK_max,
            lubrication_type=lub,
            uncertainty_factor=unc,
        )


_init_friction_table()


DEFAULT_WASHER_OUTER_DIAMETERS = {
    "M6": 11.0, "M8": 15.0, "M10": 18.0, "M12": 22.0,
    "M14": 24.0, "M16": 28.0, "M18": 30.0, "M20": 34.0,
    "M22": 37.0, "M24": 39.0, "M27": 44.0, "M30": 50.0,
    "M33": 54.0, "M36": 60.0, "M39": 63.0, "M42": 66.0,
    "M45": 70.0, "M48": 75.0, "M52": 82.0, "M56": 88.0,
    "M60": 94.0, "M64": 100.0,
}


class BoltTorquePreloadModel:
    """
    螺栓扭矩-预紧力换算模型（VDI 2230 简化版）

    核心功能:
    - 螺纹规格查询
    - 摩擦系数查询与修正
    - 扭矩 → 预紧力 正向计算
    - 实测扭矩 → 预紧力 反向计算
    - 预紧力不确定度分析
    - 建议复紧扭矩区间计算
    """

    def __init__(self):
        self.thread_angle_rad = math.radians(30.0)
        self.cos_half_alpha = math.cos(self.thread_angle_rad)

        tp_cfg = config.get('torque_preload', {})
        self.default_tightening_factor = tp_cfg.get('default_tightening_factor', 1.4)
        self.default_torque_tolerance_pct = tp_cfg.get('default_torque_tolerance_pct', 15.0)
        self.default_retorque_factor_low = tp_cfg.get('default_retorque_factor_low', 0.9)
        self.default_retorque_factor_high = tp_cfg.get('default_retorque_factor_high', 1.1)

        logger.info("螺栓扭矩-预紧力换算模型初始化完成")

    def list_thread_specs(
        self, standard: Optional[ThreadStandard] = None
    ) -> List[ThreadSpec]:
        if standard == ThreadStandard.METRIC_FINE:
            return list(METRIC_FINE_THREADS.values())
        elif standard == ThreadStandard.METRIC_COARSE:
            return list(METRIC_COARSE_THREADS.values())
        else:
            return list(METRIC_COARSE_THREADS.values()) + list(METRIC_FINE_THREADS.values())

    def get_thread_spec(self, designation: str) -> Optional[ThreadSpec]:
        key = designation.upper().replace(" ", "")
        if key in METRIC_COARSE_THREADS:
            return METRIC_COARSE_THREADS[key]
        if key in METRIC_FINE_THREADS:
            return METRIC_FINE_THREADS[key]
        for d in METRIC_COARSE_THREADS:
            if d.lower() == key.lower():
                return METRIC_COARSE_THREADS[d]
        for d in METRIC_FINE_THREADS:
            if d.lower() == key.lower():
                return METRIC_FINE_THREADS[d]
        return None

    def list_lubrication_types(self) -> List[Dict[str, Any]]:
        result = []
        for lub in LubricationType:
            fric = FRICTION_TABLE.get(lub)
            if fric:
                result.append({
                    "type": lub.value,
                    "label": LUBRICATION_LABELS[lub],
                    "mu_G": fric.mu_G,
                    "mu_K": fric.mu_K,
                    "uncertainty_factor": fric.uncertainty_factor,
                })
        return result

    def get_friction_coefficients(
        self,
        lubrication_type: LubricationType,
        custom_mu_G: Optional[float] = None,
        custom_mu_K: Optional[float] = None,
    ) -> FrictionCoefficients:
        base = FRICTION_TABLE.get(lubrication_type)
        if base is None:
            base = FRICTION_TABLE[LubricationType.MACHINE_OIL]

        mu_G = custom_mu_G if custom_mu_G is not None else base.mu_G
        mu_K = custom_mu_K if custom_mu_K is not None else base.mu_K

        spread_G = (base.mu_G_max - base.mu_G_min) / 2
        spread_K = (base.mu_K_max - base.mu_K_min) / 2

        return FrictionCoefficients(
            mu_G=mu_G,
            mu_K=mu_K,
            mu_G_min=max(0.01, mu_G - spread_G),
            mu_G_max=mu_G + spread_G,
            mu_K_min=max(0.01, mu_K - spread_K),
            mu_K_max=mu_K + spread_K,
            lubrication_type=lubrication_type,
            uncertainty_factor=base.uncertainty_factor,
        )

    def calculate_support_diameter(
        self,
        bolt_spec: ThreadSpec,
        washer_outer_diameter: Optional[float] = None,
        nut_type: str = "hex_nut",
    ) -> float:
        d = bolt_spec.nominal_diameter
        if washer_outer_diameter is not None:
            Dw = washer_outer_diameter
        else:
            base_key = f"M{int(d)}"
            Dw = DEFAULT_WASHER_OUTER_DIAMETERS.get(base_key, 1.5 * d)
            if nut_type == "hex_bolt_head":
                Dw = Dw * 0.95
        d_h = d * 1.05
        D_Km = (Dw + d_h) / 2.0
        return D_Km

    def calculate_torque(
        self,
        bolt_size: str,
        target_preload: float,
        lubrication_type: LubricationType = LubricationType.MACHINE_OIL,
        custom_mu_G: Optional[float] = None,
        custom_mu_K: Optional[float] = None,
        washer_outer_diameter: Optional[float] = None,
        nut_type: str = "hex_nut",
        tightening_factor: Optional[float] = None,
        torque_tolerance_pct: Optional[float] = None,
    ) -> TorqueCalculationResult:
        bolt_spec = self.get_thread_spec(bolt_size)
        if bolt_spec is None:
            raise ValueError(f"未知螺纹规格: {bolt_size}")

        friction = self.get_friction_coefficients(
            lubrication_type, custom_mu_G, custom_mu_K
        )

        D_Km = self.calculate_support_diameter(bolt_spec, washer_outer_diameter, nut_type)

        P = bolt_spec.pitch
        d2 = bolt_spec.pitch_diameter
        mu_G = friction.mu_G
        mu_K = friction.mu_K

        thread_component = 0.159 * P + (d2 * mu_G) / self.cos_half_alpha
        bearing_component = (D_Km * mu_K) / 2.0
        total_torque_coeff = thread_component + bearing_component

        M_A = target_preload * total_torque_coeff / 1000.0

        alpha_A = tightening_factor or self.default_tightening_factor
        tol_pct = torque_tolerance_pct or self.default_torque_tolerance_pct
        M_A_min = M_A * (1.0 - tol_pct / 100.0) / alpha_A
        M_A_max = M_A * (1.0 + tol_pct / 100.0)

        return TorqueCalculationResult(
            bolt_spec=bolt_spec,
            friction=friction,
            target_preload=target_preload,
            nominal_torque=M_A,
            torque_min=M_A_min,
            torque_max=M_A_max,
            torque_tolerance_pct=tol_pct,
            tightening_factor=alpha_A,
            dKm=D_Km,
            formula_components={
                "pitch_term_Nmm": 0.159 * P * target_preload,
                "thread_friction_term_Nmm": (d2 * mu_G / self.cos_half_alpha) * target_preload,
                "bearing_friction_term_Nmm": (D_Km * mu_K / 2.0) * target_preload,
                "total_coeff_mm": total_torque_coeff,
                "thread_component_ratio": thread_component / total_torque_coeff if total_torque_coeff > 0 else 0,
                "bearing_component_ratio": bearing_component / total_torque_coeff if total_torque_coeff > 0 else 0,
            },
        )

    def calculate_preload_from_torque(
        self,
        bolt_size: str,
        measured_torque: float,
        lubrication_type: LubricationType = LubricationType.MACHINE_OIL,
        custom_mu_G: Optional[float] = None,
        custom_mu_K: Optional[float] = None,
        washer_outer_diameter: Optional[float] = None,
        nut_type: str = "hex_nut",
    ) -> PreloadCalculationResult:
        bolt_spec = self.get_thread_spec(bolt_size)
        if bolt_spec is None:
            raise ValueError(f"未知螺纹规格: {bolt_size}")

        friction = self.get_friction_coefficients(
            lubrication_type, custom_mu_G, custom_mu_K
        )

        D_Km = self.calculate_support_diameter(bolt_spec, washer_outer_diameter, nut_type)

        P = bolt_spec.pitch
        d2 = bolt_spec.pitch_diameter
        mu_G = friction.mu_G
        mu_K = friction.mu_K

        total_torque_coeff = 0.159 * P + (d2 * mu_G) / self.cos_half_alpha + (D_Km * mu_K) / 2.0

        F_M_nominal = (measured_torque * 1000.0) / total_torque_coeff

        coeff_min = (
            0.159 * P
            + (d2 * friction.mu_G_min) / self.cos_half_alpha
            + (D_Km * friction.mu_K_min) / 2.0
        )
        F_M_max = (measured_torque * 1000.0) / coeff_min

        coeff_max = (
            0.159 * P
            + (d2 * friction.mu_G_max) / self.cos_half_alpha
            + (D_Km * friction.mu_K_max) / 2.0
        )
        F_M_min = (measured_torque * 1000.0) / coeff_max

        uncertainty_pct = ((F_M_max - F_M_min) / 2.0) / F_M_nominal * 100.0 if F_M_nominal > 0 else 0

        return PreloadCalculationResult(
            bolt_spec=bolt_spec,
            friction=friction,
            measured_torque=measured_torque,
            calculated_preload=F_M_nominal,
            preload_min=F_M_min,
            preload_max=F_M_max,
            preload_uncertainty_pct=uncertainty_pct,
            dKm=D_Km,
        )

    def calculate_retorque_range(
        self,
        bolt_size: str,
        target_preload: float,
        current_preload: Optional[float] = None,
        measured_torque: Optional[float] = None,
        lubrication_type: LubricationType = LubricationType.MACHINE_OIL,
        custom_mu_G: Optional[float] = None,
        custom_mu_K: Optional[float] = None,
        washer_outer_diameter: Optional[float] = None,
        nut_type: str = "hex_nut",
        retorque_factor_low: Optional[float] = None,
        retorque_factor_high: Optional[float] = None,
    ) -> Dict[str, Any]:
        if current_preload is None and measured_torque is not None:
            preload_result = self.calculate_preload_from_torque(
                bolt_size=bolt_size,
                measured_torque=measured_torque,
                lubrication_type=lubrication_type,
                custom_mu_G=custom_mu_G,
                custom_mu_K=custom_mu_K,
                washer_outer_diameter=washer_outer_diameter,
                nut_type=nut_type,
            )
            current_preload = preload_result.calculated_preload

        if current_preload is None:
            raise ValueError("必须提供 current_preload 或 measured_torque")

        factor_low = retorque_factor_low or self.default_retorque_factor_low
        factor_high = retorque_factor_high or self.default_retorque_factor_high

        loss_ratio = 1.0 - (current_preload / target_preload) if target_preload > 0 else 0

        needed_preload_low = target_preload * factor_low
        needed_preload_high = target_preload * factor_high

        torque_low_result = self.calculate_torque(
            bolt_size=bolt_size,
            target_preload=needed_preload_low,
            lubrication_type=lubrication_type,
            custom_mu_G=custom_mu_G,
            custom_mu_K=custom_mu_K,
            washer_outer_diameter=washer_outer_diameter,
            nut_type=nut_type,
        )
        torque_high_result = self.calculate_torque(
            bolt_size=bolt_size,
            target_preload=needed_preload_high,
            lubrication_type=lubrication_type,
            custom_mu_G=custom_mu_G,
            custom_mu_K=custom_mu_K,
            washer_outer_diameter=washer_outer_diameter,
            nut_type=nut_type,
        )

        action = "maintain"
        if loss_ratio > 0.15:
            action = "retorque_needed"
        elif loss_ratio > 0.05:
            action = "monitor"

        return {
            "bolt_size": bolt_size,
            "target_preload_N": round(target_preload, 2),
            "target_preload_kN": round(target_preload / 1000, 2),
            "current_preload_N": round(current_preload, 2),
            "current_preload_kN": round(current_preload / 1000, 2),
            "preload_loss_ratio": round(loss_ratio, 4),
            "preload_loss_pct": round(loss_ratio * 100, 2),
            "recommended_action": action,
            "retorque_torque_min_Nm": round(torque_low_result.nominal_torque, 2),
            "retorque_torque_nominal_Nm": round(
                (torque_low_result.nominal_torque + torque_high_result.nominal_torque) / 2.0,
                2,
            ),
            "retorque_torque_max_Nm": round(torque_high_result.nominal_torque, 2),
            "retorque_preload_range_N": [
                round(needed_preload_low, 2),
                round(needed_preload_high, 2),
            ],
            "retorque_preload_range_kN": [
                round(needed_preload_low / 1000, 2),
                round(needed_preload_high / 1000, 2),
            ],
        }

    def batch_calculate_torque(
        self,
        bolt_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results = []
        for item in bolt_list:
            try:
                lub_type = item.get('lubrication_type', LubricationType.MACHINE_OIL)
                if isinstance(lub_type, str):
                    lub_type = LubricationType(lub_type)
                result = self.calculate_torque(
                    bolt_size=item['bolt_size'],
                    target_preload=item['target_preload'],
                    lubrication_type=lub_type,
                    custom_mu_G=item.get('custom_mu_G'),
                    custom_mu_K=item.get('custom_mu_K'),
                    washer_outer_diameter=item.get('washer_outer_diameter'),
                    nut_type=item.get('nut_type', 'hex_nut'),
                    tightening_factor=item.get('tightening_factor'),
                    torque_tolerance_pct=item.get('torque_tolerance_pct'),
                )
                results.append({
                    "bolt_id": item.get('bolt_id', item.get('bolt_size')),
                    "success": True,
                    "data": result.to_dict(),
                })
            except Exception as e:
                results.append({
                    "bolt_id": item.get('bolt_id', item.get('bolt_size', 'unknown')),
                    "success": False,
                    "error": str(e),
                })
        return results

    def batch_calculate_preload(
        self,
        torque_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results = []
        for item in torque_list:
            try:
                lub_type = item.get('lubrication_type', LubricationType.MACHINE_OIL)
                if isinstance(lub_type, str):
                    lub_type = LubricationType(lub_type)
                result = self.calculate_preload_from_torque(
                    bolt_size=item['bolt_size'],
                    measured_torque=item['measured_torque'],
                    lubrication_type=lub_type,
                    custom_mu_G=item.get('custom_mu_G'),
                    custom_mu_K=item.get('custom_mu_K'),
                    washer_outer_diameter=item.get('washer_outer_diameter'),
                    nut_type=item.get('nut_type', 'hex_nut'),
                )
                results.append({
                    "bolt_id": item.get('bolt_id', item.get('bolt_size')),
                    "success": True,
                    "data": result.to_dict(),
                })
            except Exception as e:
                results.append({
                    "bolt_id": item.get('bolt_id', item.get('bolt_size', 'unknown')),
                    "success": False,
                    "error": str(e),
                })
        return results
