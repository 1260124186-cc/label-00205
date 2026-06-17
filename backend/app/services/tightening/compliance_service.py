"""
螺栓紧固合规检查服务

功能:
1. 设计极限检查（预紧力是否超过屈服强度、扭矩是否超限）
2. 润滑剂更换建议（基于使用次数、摩擦系数漂移、温度老化）
3. 工艺合规性检查（步骤完整性、允差带符合性）
4. 知识库关联查询（根据工艺ID/标签检索历史案例）

使用示例:
    from app.services.tightening import TighteningComplianceService

    service = TighteningComplianceService()
    # 检查设计极限
    check = service.check_design_limits(
        bolt_size="M20",
        bolt_grade="8.8",
        preload=150000
    )
    # 润滑剂评估
    eval = service.evaluate_lubricant(
        lubrication_type="molybdenum_disulfide",
        usage_count=15,
        operating_temperature_c=180
    )
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.utils.config import config
from app.models.bolt_torque_preload import (
    BoltTorquePreloadModel,
    LubricationType,
    LUBRICATION_LABELS,
)


class ComplianceStatus(Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


COMPLIANCE_STATUS_LABELS = {
    ComplianceStatus.PASS: "合格",
    ComplianceStatus.WARNING: "警告",
    ComplianceStatus.FAIL: "不合格",
}


class BoltGrade(Enum):
    GRADE_4_6 = "4.6"
    GRADE_4_8 = "4.8"
    GRADE_5_6 = "5.6"
    GRADE_5_8 = "5.8"
    GRADE_6_8 = "6.8"
    GRADE_8_8 = "8.8"
    GRADE_9_8 = "9.8"
    GRADE_10_9 = "10.9"
    GRADE_12_9 = "12.9"


BOLT_GRADE_PROPERTIES: Dict[BoltGrade, Dict[str, float]] = {
    BoltGrade.GRADE_4_6:  {"proof_load_MPa": 225,  "yield_MPa": 240,  "tensile_MPa": 400},
    BoltGrade.GRADE_4_8:  {"proof_load_MPa": 310,  "yield_MPa": 320,  "tensile_MPa": 420},
    BoltGrade.GRADE_5_6:  {"proof_load_MPa": 300,  "yield_MPa": 320,  "tensile_MPa": 500},
    BoltGrade.GRADE_5_8:  {"proof_load_MPa": 380,  "yield_MPa": 400,  "tensile_MPa": 520},
    BoltGrade.GRADE_6_8:  {"proof_load_MPa": 480,  "yield_MPa": 480,  "tensile_MPa": 600},
    BoltGrade.GRADE_8_8:  {"proof_load_MPa": 600,  "yield_MPa": 640,  "tensile_MPa": 800},
    BoltGrade.GRADE_9_8:  {"proof_load_MPa": 650,  "yield_MPa": 720,  "tensile_MPa": 900},
    BoltGrade.GRADE_10_9: {"proof_load_MPa": 830,  "yield_MPa": 900,  "tensile_MPa": 1000},
    BoltGrade.GRADE_12_9: {"proof_load_MPa": 970,  "yield_MPa": 1080, "tensile_MPa": 1200},
}


DEFAULT_PRELOAD_RATIOS = {
    "non_permanent": 0.70,
    "permanent_reusable": 0.75,
    "permanent": 0.85,
    "yield_point": 0.90,
    "hydraulic_tension": 0.80,
}


LUBRICANT_TEMPERATURE_LIMITS: Dict[LubricationType, Dict[str, Any]] = {
    LubricationType.DRY: {
        "min_temp_c": -40, "max_temp_c": 150,
        "max_reuses": 1, "aging_factor_per_cycle": 0.05,
        "recommended_replacement": "首次使用后更换",
    },
    LubricationType.MACHINE_OIL: {
        "min_temp_c": -20, "max_temp_c": 120,
        "max_reuses": 3, "aging_factor_per_cycle": 0.08,
        "recommended_replacement": "使用3次或超过6个月更换",
    },
    LubricationType.MOLYBDENUM_DISULFIDE: {
        "min_temp_c": -50, "max_temp_c": 350,
        "max_reuses": 10, "aging_factor_per_cycle": 0.03,
        "recommended_replacement": "使用10次或超过12个月更换",
    },
    LubricationType.GRAPHITE: {
        "min_temp_c": -40, "max_temp_c": 450,
        "max_reuses": 8, "aging_factor_per_cycle": 0.04,
        "recommended_replacement": "使用8次或超过12个月更换",
    },
    LubricationType.TEFLON_COATED: {
        "min_temp_c": -60, "max_temp_c": 260,
        "max_reuses": 15, "aging_factor_per_cycle": 0.02,
        "recommended_replacement": "涂层磨损后更换",
    },
    LubricationType.ANTI_SEIZE: {
        "min_temp_c": -30, "max_temp_c": 650,
        "max_reuses": 5, "aging_factor_per_cycle": 0.06,
        "recommended_replacement": "使用5次或超过6个月更换",
    },
    LubricationType.ZINC_FLAKE_COATED: {
        "min_temp_c": -50, "max_temp_c": 300,
        "max_reuses": 20, "aging_factor_per_cycle": 0.015,
        "recommended_replacement": "涂层破损后更换",
    },
    LubricationType.HOT_DIP_GALVANIZED: {
        "min_temp_c": -40, "max_temp_c": 200,
        "max_reuses": 2, "aging_factor_per_cycle": 0.10,
        "recommended_replacement": "热镀锌螺栓建议不重复使用",
    },
}


@dataclass
class DesignLimitCheck:
    """
    设计极限检查结果
    """
    status: ComplianceStatus
    bolt_size: str
    bolt_grade: BoltGrade
    preload_N: float
    proof_load_N: float
    yield_load_N: float
    stress_MPa: float
    proof_load_ratio: float
    yield_ratio: float
    allowed_max_preload_N: float
    utilization_ratio: float
    issues: List[str]
    recommendations: List[str]

    @property
    def warnings(self) -> List[str]:
        return self.issues

    @property
    def over_yield(self) -> bool:
        return self.yield_ratio >= 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "status_label": COMPLIANCE_STATUS_LABELS[self.status],
            "bolt_size": self.bolt_size,
            "bolt_grade": self.bolt_grade.value,
            "preload_N": round(self.preload_N, 2),
            "preload_kN": round(self.preload_N / 1000, 2),
            "proof_load_N": round(self.proof_load_N, 2),
            "proof_load_kN": round(self.proof_load_N / 1000, 2),
            "yield_load_N": round(self.yield_load_N, 2),
            "yield_load_kN": round(self.yield_load_N / 1000, 2),
            "stress_MPa": round(self.stress_MPa, 2),
            "proof_load_ratio": round(self.proof_load_ratio, 4),
            "yield_ratio": round(self.yield_ratio, 4),
            "allowed_max_preload_N": round(self.allowed_max_preload_N, 2),
            "allowed_max_preload_kN": round(self.allowed_max_preload_N / 1000, 2),
            "utilization_ratio_pct": round(self.utilization_ratio * 100, 2),
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


@dataclass
class LubricantEvaluation:
    """
    润滑剂评估结果
    """
    status: ComplianceStatus
    lubrication_type: LubricationType
    friction_deviation_pct: float
    usage_count: int
    max_allowed_reuses: int
    operating_temperature_c: Optional[float]
    temperature_within_range: Optional[bool]
    remaining_useful_life_pct: float
    estimated_mu_current: float
    estimated_mu_range: Tuple[float, float]
    issues: List[str]
    recommendations: List[str]

    @property
    def warnings(self) -> List[str]:
        return self.issues

    @property
    def need_replace(self) -> bool:
        return self.status == ComplianceStatus.FAIL or self.remaining_useful_life_pct < 20.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "status_label": COMPLIANCE_STATUS_LABELS[self.status],
            "lubrication_type": self.lubrication_type.value,
            "lubrication_label": LUBRICATION_LABELS[self.lubrication_type],
            "friction_deviation_pct": round(self.friction_deviation_pct, 2),
            "usage_count": self.usage_count,
            "max_allowed_reuses": self.max_allowed_reuses,
            "operating_temperature_c": self.operating_temperature_c,
            "temperature_within_range": self.temperature_within_range,
            "remaining_useful_life_pct": round(self.remaining_useful_life_pct, 2),
            "estimated_mu_current": round(self.estimated_mu_current, 4),
            "estimated_mu_range": [round(x, 4) for x in self.estimated_mu_range],
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


@dataclass
class ProcessComplianceCheck:
    """
    工艺合规性检查结果
    """
    status: ComplianceStatus
    step_count: int
    completed_steps: int
    steps_in_tolerance: int
    cross_sequence_followed: Optional[bool]
    torque_deviations_pct: List[float]
    overall_completion_pct: float
    tolerance_violations: List[Dict[str, Any]]
    issues: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "status_label": COMPLIANCE_STATUS_LABELS[self.status],
            "step_count": self.step_count,
            "completed_steps": self.completed_steps,
            "steps_in_tolerance": self.steps_in_tolerance,
            "cross_sequence_followed": self.cross_sequence_followed,
            "torque_deviations_pct": [round(x, 2) for x in self.torque_deviations_pct],
            "overall_completion_pct": round(self.overall_completion_pct, 2),
            "tolerance_violations": self.tolerance_violations,
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


class TighteningComplianceService:
    """
    螺栓紧固合规检查服务

    核心职责:
    - 预紧力设计极限校核
    - 润滑剂寿命与温度评估
    - 紧固工艺合规性检查
    - 知识库关联检索
    """

    def __init__(self):
        self.torque_preload = BoltTorquePreloadModel()

        comp_cfg = config.get('tightening_compliance', {})
        self.default_preload_ratio_type = comp_cfg.get('default_preload_ratio', 'permanent_reusable')
        self.warning_utilization_threshold = comp_cfg.get('warning_utilization_threshold', 0.80)
        self.critical_utilization_threshold = comp_cfg.get('critical_utilization_threshold', 0.92)
        self.default_torque_tolerance_pct = comp_cfg.get('default_torque_tolerance_pct', 15.0)

        logger.info("螺栓紧固合规检查服务初始化完成")

    def list_bolt_grades(self) -> List[Dict[str, Any]]:
        result = []
        for grade, props in BOLT_GRADE_PROPERTIES.items():
            result.append({
                "grade": grade.value,
                "proof_load_MPa": props["proof_load_MPa"],
                "yield_MPa": props["yield_MPa"],
                "tensile_MPa": props["tensile_MPa"],
            })
        return result

    def check_design_limits(
        self,
        bolt_size: str,
        bolt_grade: str,
        preload: float,
        preload_ratio_type: Optional[str] = None,
    ) -> DesignLimitCheck:
        try:
            grade = BoltGrade(bolt_grade)
        except ValueError:
            raise ValueError(f"未知螺栓等级: {bolt_grade}")

        bolt_spec = self.torque_preload.get_thread_spec(bolt_size)
        if bolt_spec is None:
            raise ValueError(f"未知螺纹规格: {bolt_size}")

        props = BOLT_GRADE_PROPERTIES[grade]
        As_m2 = bolt_spec.tensile_stress_area * 1e-6

        proof_load_N = props["proof_load_MPa"] * 1e6 * As_m2
        yield_load_N = props["yield_MPa"] * 1e6 * As_m2
        stress_MPa = preload / (bolt_spec.tensile_stress_area) if bolt_spec.tensile_stress_area > 0 else 0

        ratio_type = preload_ratio_type or self.default_preload_ratio_type
        allowed_ratio = DEFAULT_PRELOAD_RATIOS.get(ratio_type, 0.75)
        allowed_max_preload_N = proof_load_N * allowed_ratio

        proof_load_ratio = preload / proof_load_N if proof_load_N > 0 else 0
        yield_ratio = preload / yield_load_N if yield_load_N > 0 else 0
        utilization_ratio = preload / allowed_max_preload_N if allowed_max_preload_N > 0 else 0

        issues: List[str] = []
        recommendations: List[str] = []

        if utilization_ratio > self.critical_utilization_threshold:
            issues.append(f"预紧力利用率超过 {self.critical_utilization_threshold*100:.0f}%")
            recommendations.append("降低预紧力或更换更高强度等级螺栓")
        elif utilization_ratio > self.warning_utilization_threshold:
            issues.append(f"预紧力利用率超过 {self.warning_utilization_threshold*100:.0f}%")
            recommendations.append("关注预紧力波动，考虑适当降低目标值")

        if yield_ratio >= 1.0:
            issues.append("预紧力达到或超过屈服强度，存在永久变形风险")
            recommendations.append("必须降低预紧力，防止螺栓屈服断裂")

        if proof_load_ratio >= 1.0:
            issues.append("预紧力达到保证载荷极限")
            recommendations.append("预紧力已达保证载荷，校核是否符合设计要求")

        if stress_MPa > props["proof_load_MPa"]:
            issues.append(f"应力 {stress_MPa:.1f}MPa 超过保证载荷应力 {props['proof_load_MPa']}MPa")

        status = ComplianceStatus.PASS
        if issues:
            if utilization_ratio > self.critical_utilization_threshold or yield_ratio >= 1.0:
                status = ComplianceStatus.FAIL
            else:
                status = ComplianceStatus.WARNING

        if not recommendations:
            recommendations.append("预紧力在设计范围内，可正常使用")

        return DesignLimitCheck(
            status=status,
            bolt_size=bolt_size,
            bolt_grade=grade,
            preload_N=preload,
            proof_load_N=proof_load_N,
            yield_load_N=yield_load_N,
            stress_MPa=stress_MPa,
            proof_load_ratio=proof_load_ratio,
            yield_ratio=yield_ratio,
            allowed_max_preload_N=allowed_max_preload_N,
            utilization_ratio=utilization_ratio,
            issues=issues,
            recommendations=recommendations,
        )

    def evaluate_lubricant(
        self,
        lubrication_type: str,
        usage_count: int = 0,
        operating_temperature_c: Optional[float] = None,
        measured_friction_deviation_pct: Optional[float] = None,
        months_since_application: Optional[float] = None,
    ) -> LubricantEvaluation:
        try:
            lub = LubricationType(lubrication_type)
        except ValueError:
            raise ValueError(f"未知润滑类型: {lubrication_type}")

        limits = LUBRICANT_TEMPERATURE_LIMITS.get(lub)
        if limits is None:
            limits = LUBRICANT_TEMPERATURE_LIMITS[LubricationType.MACHINE_OIL]

        base_friction = self.torque_preload.get_friction_coefficients(lub)
        base_mu = (base_friction.mu_G + base_friction.mu_K) / 2.0

        aging_from_reuse = min(1.0, usage_count / max(1, limits["max_reuses"])) * limits["aging_factor_per_cycle"]
        aging_from_time = 0.0
        if months_since_application is not None:
            aging_from_time = min(1.0, months_since_application / 12.0) * limits["aging_factor_per_cycle"] * 1.5

        total_aging = aging_from_reuse + aging_from_time
        estimated_mu_current = base_mu * (1.0 + total_aging)
        estimated_mu_range = (
            max(0.01, estimated_mu_current - 0.02),
            estimated_mu_current + 0.03,
        )

        remaining_reuse_life = max(0.0, 1.0 - usage_count / max(1, limits["max_reuses"]))
        remaining_life_pct = remaining_reuse_life * 100.0

        temp_ok = None
        if operating_temperature_c is not None:
            temp_ok = limits["min_temp_c"] <= operating_temperature_c <= limits["max_temp_c"]

        friction_dev = measured_friction_deviation_pct or 0.0
        if measured_friction_deviation_pct is None:
            friction_dev = total_aging * 100.0

        issues: List[str] = []
        recommendations: List[str] = []

        if usage_count >= limits["max_reuses"]:
            issues.append(f"已达最大使用次数 {limits['max_reuses']} 次")
            recommendations.append("建议更换润滑剂")
        elif usage_count >= limits["max_reuses"] * 0.8:
            issues.append(f"使用次数接近极限 ({usage_count}/{limits['max_reuses']})")
            recommendations.append("准备更换润滑剂")

        if operating_temperature_c is not None and temp_ok is False:
            if operating_temperature_c > limits["max_temp_c"]:
                issues.append(f"运行温度 {operating_temperature_c}°C 超过上限 {limits['max_temp_c']}°C")
                recommendations.append(f"更换耐高温润滑剂，当前上限 {limits['max_temp_c']}°C")
            else:
                issues.append(f"运行温度 {operating_temperature_c}°C 低于下限 {limits['min_temp_c']}°C")
                recommendations.append(f"更换耐低温润滑剂，当前下限 {limits['min_temp_c']}°C")

        if friction_dev > 20.0:
            issues.append(f"摩擦系数偏差较大: {friction_dev:.1f}%")
            recommendations.append("检查润滑剂状态，考虑重新涂覆")
        elif friction_dev > 10.0:
            issues.append(f"摩擦系数出现漂移: {friction_dev:.1f}%")

        if remaining_life_pct < 20.0:
            issues.append(f"剩余使用寿命不足: {remaining_life_pct:.1f}%")
            recommendations.append(limits.get("recommended_replacement", "尽快更换润滑剂"))

        status = ComplianceStatus.PASS
        if issues:
            critical_issues = [
                i for i in issues
                if "超过上限" in i or "超过下限" in i or "已达最大使用次数" in i or "不足" in i and "20%" in i
            ]
            if critical_issues:
                status = ComplianceStatus.FAIL
            else:
                status = ComplianceStatus.WARNING

        if not recommendations:
            recommendations.append("润滑剂状态良好，可继续使用")

        return LubricantEvaluation(
            status=status,
            lubrication_type=lub,
            friction_deviation_pct=friction_dev,
            usage_count=usage_count,
            max_allowed_reuses=limits["max_reuses"],
            operating_temperature_c=operating_temperature_c,
            temperature_within_range=temp_ok,
            remaining_useful_life_pct=remaining_life_pct,
            estimated_mu_current=estimated_mu_current,
            estimated_mu_range=estimated_mu_range,
            issues=issues,
            recommendations=recommendations,
        )

    def check_process_compliance(
        self,
        expected_steps: int,
        completed_steps: List[Dict[str, Any]],
        target_torque_Nm: float,
        cross_sequence_followed: Optional[bool] = None,
        torque_tolerance_pct: Optional[float] = None,
    ) -> ProcessComplianceCheck:
        tol_pct = torque_tolerance_pct or self.default_torque_tolerance_pct

        completed_count = len(completed_steps)
        deviations_pct: List[float] = []
        tolerance_violations: List[Dict[str, Any]] = []
        steps_in_tol = 0

        for step in completed_steps:
            measured = step.get("measured_torque_Nm")
            if measured is None:
                continue
            dev_pct = abs(measured - target_torque_Nm) / target_torque_Nm * 100.0 if target_torque_Nm > 0 else 0.0
            deviations_pct.append(dev_pct)
            if dev_pct <= tol_pct:
                steps_in_tol += 1
            else:
                tolerance_violations.append({
                    "step_number": step.get("step_number"),
                    "target_torque_Nm": round(target_torque_Nm, 2),
                    "measured_torque_Nm": round(measured, 2),
                    "deviation_pct": round(dev_pct, 2),
                    "tolerance_pct": tol_pct,
                })

        completion_pct = (completed_count / expected_steps * 100.0) if expected_steps > 0 else 0.0

        issues: List[str] = []
        recommendations: List[str] = []

        if completion_pct < 100.0:
            issues.append(f"工艺步骤未完成: {completed_count}/{expected_steps}")
            recommendations.append("完成剩余紧固步骤")

        if tolerance_violations:
            issues.append(f"{len(tolerance_violations)} 项扭矩超出允差带")
            recommendations.append("对超出允差的螺栓重新紧固")

        if cross_sequence_followed is False:
            issues.append("未按交叉紧固顺序执行")
            recommendations.append("后续复紧严格按交叉顺序执行")

        avg_dev = sum(deviations_pct) / len(deviations_pct) if deviations_pct else 0.0
        if avg_dev > tol_pct * 0.7:
            issues.append(f"扭矩平均偏差较大: {avg_dev:.1f}%")
            recommendations.append("检查工具校准和润滑剂状态")

        status = ComplianceStatus.PASS
        if issues:
            if completion_pct < 80.0 or len(tolerance_violations) > max(1, expected_steps // 3):
                status = ComplianceStatus.FAIL
            else:
                status = ComplianceStatus.WARNING

        if not recommendations:
            recommendations.append("紧固工艺执行符合要求")

        return ProcessComplianceCheck(
            status=status,
            step_count=expected_steps,
            completed_steps=completed_count,
            steps_in_tolerance=steps_in_tol,
            cross_sequence_followed=cross_sequence_followed,
            torque_deviations_pct=deviations_pct,
            overall_completion_pct=completion_pct,
            tolerance_violations=tolerance_violations,
            issues=issues,
            recommendations=recommendations,
        )

    def find_related_knowledge_cases(
        self,
        procedure_id: Optional[str] = None,
        bolt_size: Optional[str] = None,
        lubrication_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        search_tags = []
        if procedure_id:
            search_tags.append(procedure_id)
        if bolt_size:
            search_tags.append(bolt_size)
        if lubrication_type:
            search_tags.append(lubrication_type)
        if tags:
            search_tags.extend(tags)

        try:
            from app.services.knowledge import KnowledgeService
            ks = KnowledgeService()
            total, cases = ks.list_cases(
                tags=search_tags if search_tags else None,
                limit=limit,
            )
            case_list = []
            for c in cases:
                try:
                    case_tags = json.loads(c.tags) if c.tags else []
                except Exception:
                    case_tags = []
                case_list.append({
                    "case_id": c.id,
                    "case_no": c.case_no,
                    "title": c.case_title,
                    "fault_type": c.fault_type,
                    "fault_level": c.fault_level,
                    "status": c.status,
                    "tags": case_tags,
                    "create_time": c.create_time.isoformat() if c.create_time else None,
                    "effectiveness_score": c.effectiveness_score,
                })
            return {
                "search_tags": search_tags,
                "total": total,
                "count": len(case_list),
                "cases": case_list,
            }
        except Exception as e:
            logger.warning(f"知识库关联查询失败: {e}")
            return {
                "search_tags": search_tags,
                "total": 0,
                "count": 0,
                "cases": [],
                "error": str(e),
            }

    def full_compliance_audit(
        self,
        bolt_size: str,
        bolt_grade: str,
        target_preload: float,
        lubrication_type: str,
        procedure_id: str,
        expected_steps: int,
        completed_steps: List[Dict[str, Any]],
        target_torque_Nm: float,
        usage_count: int = 0,
        operating_temperature_c: Optional[float] = None,
        preload_ratio_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        design_check = self.check_design_limits(
            bolt_size=bolt_size,
            bolt_grade=bolt_grade,
            preload=target_preload,
            preload_ratio_type=preload_ratio_type,
        )
        lubricant_eval = self.evaluate_lubricant(
            lubrication_type=lubrication_type,
            usage_count=usage_count,
            operating_temperature_c=operating_temperature_c,
        )
        process_check = self.check_process_compliance(
            expected_steps=expected_steps,
            completed_steps=completed_steps,
            target_torque_Nm=target_torque_Nm,
        )
        related_cases = self.find_related_knowledge_cases(
            procedure_id=procedure_id,
            bolt_size=bolt_size,
            lubrication_type=lubrication_type,
        )

        statuses = [design_check.status, lubricant_eval.status, process_check.status]
        if ComplianceStatus.FAIL in statuses:
            overall_status = ComplianceStatus.FAIL
        elif ComplianceStatus.WARNING in statuses:
            overall_status = ComplianceStatus.WARNING
        else:
            overall_status = ComplianceStatus.PASS

        all_issues = design_check.issues + lubricant_eval.issues + process_check.issues
        all_recommendations = design_check.recommendations + lubricant_eval.recommendations + process_check.recommendations

        return {
            "overall_status": overall_status.value,
            "overall_status_label": COMPLIANCE_STATUS_LABELS[overall_status],
            "audit_timestamp": datetime.now().isoformat(),
            "design_limits": design_check.to_dict(),
            "lubricant_evaluation": lubricant_eval.to_dict(),
            "process_compliance": process_check.to_dict(),
            "related_knowledge": related_cases,
            "all_issues": all_issues,
            "all_recommendations": list(set(all_recommendations)),
        }
