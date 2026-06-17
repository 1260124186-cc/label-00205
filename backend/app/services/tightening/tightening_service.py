"""
螺栓紧固工艺综合服务层

功能:
1. 扭矩-预紧力双向换算（VDI 2230 简化公式）
2. 工艺规程生成（紧固步骤、交叉顺序、允差带）
3. 实测扭矩反算预紧力供模型使用
4. 复紧扭矩区间建议
5. 合规审计（设计极限+润滑剂+工艺完整性）
6. 知识库案例关联（工艺 ID 检索）

使用示例:
    from app.services.tightening import TighteningService

    service = TighteningService()

    # 1. 生成完整紧固工艺方案
    plan = service.generate_tightening_plan(
        bolt_size="M20",
        bolt_grade="8.8",
        target_preload=150000,
        lubrication_type="molybdenum_disulfide",
        procedure_id="ASME_PCC1_4STEP",
        bolt_count=8,
    )

    # 2. 输入实测扭矩反算预紧力
    preload_result = service.calculate_preload_from_measurement(
        bolt_size="M20",
        measured_torque=420,
        lubrication_type="molybdenum_disulfide",
    )

    # 3. 获取复紧扭矩建议区间
    retorque = service.suggest_retorque_range(
        bolt_size="M20",
        target_preload=150000,
        measured_torque=380,
        lubrication_type="molybdenum_disulfide",
    )

    # 4. 执行完整合规审计
    audit = service.full_compliance_audit(
        bolt_size="M20",
        bolt_grade="8.8",
        target_preload=150000,
        measured_preload_list=[145000, 152000, 148000],
        lubrication_type="molybdenum_disulfide",
        lubricant_usage_count=5,
        procedure_id="ASME_PCC1_4STEP",
        completed_steps=["step1", "step2", "step3", "step4"],
    )
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.utils.config import config
from app.models.bolt_torque_preload import (
    BoltTorquePreloadModel,
    LubricationType,
    LUBRICATION_LABELS,
    TorqueCalculationResult,
    PreloadCalculationResult,
)
from app.models.bolt_tightening_process import (
    BoltTighteningProcessModel,
    TighteningMethod,
    TIGHTENING_METHOD_LABELS,
    ToleranceBandType,
    DEFAULT_TOLERANCE_BANDS,
)
from app.services.tightening.compliance_service import (
    TighteningComplianceService,
    ComplianceStatus,
    COMPLIANCE_STATUS_LABELS,
    BoltGrade,
)


class RetorqueAction(Enum):
    NO_ACTION = "no_action"
    SLIGHT_TIGHTEN = "slight_tighten"
    RETORQUE_TO_TARGET = "retorque_to_target"
    REPLACE_AND_REASSEMBLE = "replace_and_reassemble"


RETORQUE_ACTION_LABELS = {
    RetorqueAction.NO_ACTION: "无需处理",
    RetorqueAction.SLIGHT_TIGHTEN: "轻微补紧",
    RetorqueAction.RETORQUE_TO_TARGET: "复紧至目标值",
    RetorqueAction.REPLACE_AND_REASSEMBLE: "更换螺栓并重新装配",
}


@dataclass
class TighteningPlan:
    """
    完整紧固工艺方案
    """
    process_id: str
    bolt_size: str
    bolt_grade: str
    target_preload_N: float
    target_torque_Nm: float
    lubrication_type: str
    tightening_method: str
    tolerance_band: Dict[str, Any]
    tightening_steps: List[Dict[str, Any]]
    cross_sequence: List[Dict[str, Any]]
    turn_angle_deg: Optional[float]
    retorque_range_Nm: Dict[str, float]
    compliance_summary: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "bolt_size": self.bolt_size,
            "bolt_grade": self.bolt_grade,
            "target_preload_N": self.target_preload_N,
            "target_torque_Nm": self.target_torque_Nm,
            "lubrication_type": self.lubrication_type,
            "lubrication_label": LUBRICATION_LABELS.get(
                LubricationType(self.lubrication_type), self.lubrication_type
            ),
            "tightening_method": self.tightening_method,
            "tightening_method_label": TIGHTENING_METHOD_LABELS.get(
                TighteningMethod(self.tightening_method), self.tightening_method
            ),
            "tolerance_band": self.tolerance_band,
            "tightening_steps": self.tightening_steps,
            "cross_sequence": self.cross_sequence,
            "turn_angle_deg": self.turn_angle_deg,
            "retorque_range_Nm": self.retorque_range_Nm,
            "compliance_summary": self.compliance_summary,
            "warnings": self.warnings,
        }


@dataclass
class MeasurementPreloadResult:
    """
    实测扭矩反算预紧力结果（供模型使用）
    """
    bolt_size: str
    measured_torque_Nm: float
    estimated_preload_N: float
    preload_min_N: float
    preload_max_N: float
    preload_uncertainty_pct: float
    friction_coeff_thread: float
    friction_coeff_bearing: float
    lubrication_type: str
    utilization_ratio: Optional[float]
    compliance_status: Optional[str]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bolt_size": self.bolt_size,
            "measured_torque_Nm": self.measured_torque_Nm,
            "estimated_preload_N": self.estimated_preload_N,
            "preload_min_N": self.preload_min_N,
            "preload_max_N": self.preload_max_N,
            "preload_uncertainty_pct": self.preload_uncertainty_pct,
            "friction_coeff_thread": self.friction_coeff_thread,
            "friction_coeff_bearing": self.friction_coeff_bearing,
            "lubrication_type": self.lubrication_type,
            "lubrication_label": LUBRICATION_LABELS.get(
                LubricationType(self.lubrication_type), self.lubrication_type
            ),
            "utilization_ratio": self.utilization_ratio,
            "compliance_status": self.compliance_status,
            "compliance_label": COMPLIANCE_STATUS_LABELS.get(
                ComplianceStatus(self.compliance_status), self.compliance_status
            ) if self.compliance_status else None,
            "warnings": self.warnings,
        }


@dataclass
class RetorqueSuggestion:
    """
    复紧扭矩建议
    """
    bolt_size: str
    target_preload_N: float
    current_estimated_preload_N: Optional[float]
    measured_torque_Nm: Optional[float]
    target_torque_Nm: float
    suggested_min_torque_Nm: float
    suggested_max_torque_Nm: float
    nominal_retorque_Nm: float
    preload_loss_pct: Optional[float]
    action: str
    severity: str
    rationale: List[str]
    related_knowledge_cases: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bolt_size": self.bolt_size,
            "target_preload_N": self.target_preload_N,
            "current_estimated_preload_N": self.current_estimated_preload_N,
            "measured_torque_Nm": self.measured_torque_Nm,
            "target_torque_Nm": self.target_torque_Nm,
            "suggested_min_torque_Nm": self.suggested_min_torque_Nm,
            "suggested_max_torque_Nm": self.suggested_max_torque_Nm,
            "nominal_retorque_Nm": self.nominal_retorque_Nm,
            "preload_loss_pct": self.preload_loss_pct,
            "action": self.action,
            "action_label": RETORQUE_ACTION_LABELS.get(
                RetorqueAction(self.action), self.action
            ),
            "severity": self.severity,
            "rationale": self.rationale,
            "related_knowledge_cases": self.related_knowledge_cases,
        }


class TighteningService:
    """
    螺栓紧固工艺综合服务

    整合扭矩-预紧力换算、工艺规程生成、合规检查、知识库关联
    提供面向上层业务（API / 预测模型 / 工单系统）的统一入口
    """

    def __init__(self):
        self.torque_model = BoltTorquePreloadModel()
        self.process_model = BoltTighteningProcessModel()
        self.compliance_service = TighteningComplianceService()

        tightening_cfg = config.get('tightening', {})
        self.default_tolerance_band = tightening_cfg.get(
            'default_tolerance_band', ToleranceBandType.NORMAL.value
        )
        self.default_preload_ratio_type = tightening_cfg.get(
            'default_preload_ratio_type', 'non_permanent'
        )
        self.retorque_warning_threshold_pct = tightening_cfg.get(
            'retorque_warning_threshold_pct', 10.0
        )
        self.retorque_critical_threshold_pct = tightening_cfg.get(
            'retorque_critical_threshold_pct', 25.0
        )

        logger.info("螺栓紧固工艺综合服务初始化完成")

    # ============== 核心换算 API ==============

    def calculate_torque_from_preload(
        self,
        bolt_size: str,
        target_preload_N: float,
        lubrication_type: str,
        friction_coeff_thread: Optional[float] = None,
        friction_coeff_bearing: Optional[float] = None,
        bearing_diameter_mm: Optional[float] = None,
    ) -> TorqueCalculationResult:
        """
        由目标预紧力计算所需扭矩
        """
        try:
            result = self.torque_model.calculate_torque(
                bolt_size=bolt_size,
                target_preload=target_preload_N,
                lubrication_type=lubrication_type,
                friction_coeff_thread=friction_coeff_thread,
                friction_coeff_bearing=friction_coeff_bearing,
                bearing_diameter_mm=bearing_diameter_mm,
            )
            logger.info(
                f"扭矩计算: {bolt_size} 预紧力={target_preload_N:.0f}N "
                f"→ 扭矩={result.required_torque_Nm:.1f}Nm [{lubrication_type}]"
            )
            return result
        except Exception as e:
            logger.error(f"扭矩计算失败: {e}")
            raise

    def calculate_preload_from_measurement(
        self,
        bolt_size: str,
        measured_torque_Nm: float,
        lubrication_type: str,
        friction_coeff_thread: Optional[float] = None,
        friction_coeff_bearing: Optional[float] = None,
        bearing_diameter_mm: Optional[float] = None,
        bolt_grade: Optional[str] = None,
    ) -> MeasurementPreloadResult:
        """
        由实测扭矩反算预紧力（供模型使用）

        返回包含预紧力标称值、上下限、不确定度以及合规状态
        """
        try:
            preload_result = self.torque_model.calculate_preload_from_torque(
                bolt_size=bolt_size,
                measured_torque=measured_torque_Nm,
                lubrication_type=lubrication_type,
                friction_coeff_thread=friction_coeff_thread,
                friction_coeff_bearing=friction_coeff_bearing,
                bearing_diameter_mm=bearing_diameter_mm,
            )

            utilization_ratio = None
            compliance_status = None
            warnings = []

            if bolt_grade:
                limit_check = self.compliance_service.check_design_limits(
                    bolt_size=bolt_size,
                    bolt_grade=bolt_grade,
                    preload=preload_result.estimated_preload_N,
                )
                utilization_ratio = limit_check.utilization_ratio
                compliance_status = limit_check.status.value
                if limit_check.status != ComplianceStatus.PASS:
                    warnings.extend(limit_check.warnings)

            if preload_result.preload_uncertainty_pct > 20:
                warnings.append(
                    f"摩擦系数不确定度较大（{preload_result.preload_uncertainty_pct:.1f}%），"
                    f"建议采用超声波测力仪或应变片直接测量预紧力"
                )

            result = MeasurementPreloadResult(
                bolt_size=bolt_size,
                measured_torque_Nm=measured_torque_Nm,
                estimated_preload_N=preload_result.estimated_preload_N,
                preload_min_N=preload_result.preload_min_N,
                preload_max_N=preload_result.preload_max_N,
                preload_uncertainty_pct=preload_result.preload_uncertainty_pct,
                friction_coeff_thread=preload_result.friction_coeff_thread,
                friction_coeff_bearing=preload_result.friction_coeff_bearing,
                lubrication_type=preload_result.lubrication_type,
                utilization_ratio=utilization_ratio,
                compliance_status=compliance_status,
                warnings=warnings,
            )

            logger.info(
                f"实测扭矩反算: {bolt_size} 扭矩={measured_torque_Nm:.1f}Nm "
                f"→ 预紧力={result.estimated_preload_N:.0f}±{result.preload_uncertainty_pct:.1f}%N"
            )
            return result

        except Exception as e:
            logger.error(f"实测扭矩反算预紧力失败: {e}")
            raise

    # ============== 复紧建议 API ==============

    def suggest_retorque_range(
        self,
        bolt_size: str,
        target_preload_N: float,
        current_preload_N: Optional[float] = None,
        measured_torque_Nm: Optional[float] = None,
        lubrication_type: str = "molybdenum_disulfide",
        bolt_grade: Optional[str] = None,
        procedure_id: Optional[str] = None,
    ) -> RetorqueSuggestion:
        """
        输出建议复紧扭矩区间

        参数:
            bolt_size: 螺栓规格，如 "M20"
            target_preload_N: 目标预紧力(N)
            current_preload_N: 当前实际预紧力(N)，可选
            measured_torque_Nm: 实测扭矩(Nm)，可选（与 current_preload_N 至少一个）
            lubrication_type: 润滑类型
            bolt_grade: 螺栓性能等级，如 "8.8"，可选用于合规判断
            procedure_id: 工艺 ID，可选用于关联知识库

        返回:
            RetorqueSuggestion: 包含复紧扭矩区间、建议动作、理由
        """
        if current_preload_N is None and measured_torque_Nm is None:
            raise ValueError("current_preload_N 和 measured_torque_Nm 至少提供一个")

        try:
            target_torque_result = self.torque_model.calculate_torque(
                bolt_size=bolt_size,
                target_preload=target_preload_N,
                lubrication_type=lubrication_type,
            )
            target_torque_Nm = target_torque_result.required_torque_Nm

            retorque_range = self.torque_model.calculate_retorque_range(
                bolt_size=bolt_size,
                target_preload=target_preload_N,
                current_preload=current_preload_N,
                measured_torque=measured_torque_Nm,
                lubrication_type=lubrication_type,
            )

            estimated_current_preload = current_preload_N
            if estimated_current_preload is None and measured_torque_Nm is not None:
                preload_res = self.torque_model.calculate_preload_from_torque(
                    bolt_size=bolt_size,
                    measured_torque=measured_torque_Nm,
                    lubrication_type=lubrication_type,
                )
                estimated_current_preload = preload_res.estimated_preload_N

            preload_loss_pct = None
            if estimated_current_preload is not None and target_preload_N > 0:
                preload_loss_pct = max(
                    0.0, (target_preload_N - estimated_current_preload) / target_preload_N * 100
                )

            action, severity, rationale = self._determine_retorque_action(
                preload_loss_pct=preload_loss_pct,
                estimated_current_preload=estimated_current_preload,
                target_preload_N=target_preload_N,
                bolt_size=bolt_size,
                bolt_grade=bolt_grade,
                lubrication_type=lubrication_type,
            )

            related_cases = []
            if procedure_id:
                case_result = self.compliance_service.find_related_knowledge_cases(
                    procedure_id=procedure_id,
                    bolt_size=bolt_size,
                    tags=["retorque", "preload_loss"],
                )
                related_cases = case_result.get("cases", [])

            suggestion = RetorqueSuggestion(
                bolt_size=bolt_size,
                target_preload_N=target_preload_N,
                current_estimated_preload_N=estimated_current_preload,
                measured_torque_Nm=measured_torque_Nm,
                target_torque_Nm=target_torque_Nm,
                suggested_min_torque_Nm=retorque_range["suggested_min_torque_Nm"],
                suggested_max_torque_Nm=retorque_range["suggested_max_torque_Nm"],
                nominal_retorque_Nm=retorque_range["nominal_retorque_Nm"],
                preload_loss_pct=preload_loss_pct,
                action=action.value,
                severity=severity,
                rationale=rationale,
                related_knowledge_cases=related_cases,
            )

            logger.info(
                f"复紧建议: {bolt_size} 预紧力损失={preload_loss_pct:.1f}% "
                f"→ 动作={action.value} 建议扭矩={suggestion.nominal_retorque_Nm:.1f}Nm"
            )
            return suggestion

        except Exception as e:
            logger.error(f"生成复紧建议失败: {e}")
            raise

    def _determine_retorque_action(
        self,
        preload_loss_pct: Optional[float],
        estimated_current_preload: Optional[float],
        target_preload_N: float,
        bolt_size: str,
        bolt_grade: Optional[str],
        lubrication_type: str,
    ) -> Tuple[RetorqueAction, str, List[str]]:
        """
        根据预紧力损失比例、合规状态判定复紧动作
        """
        rationale: List[str] = []

        if preload_loss_pct is None:
            return RetorqueAction.RETORQUE_TO_TARGET, "warning", ["缺少当前预紧力实测数据，按标准工艺复紧至目标值"]

        if bolt_grade:
            limit_check = self.compliance_service.check_design_limits(
                bolt_size=bolt_size,
                bolt_grade=bolt_grade,
                preload=target_preload_N,
            )
            if limit_check.status == ComplianceStatus.FAIL:
                rationale.append(f"目标预紧力超过设计极限: {'; '.join(limit_check.warnings)}")
                return RetorqueAction.REPLACE_AND_REASSEMBLE, "critical", rationale

            if estimated_current_preload:
                cur_check = self.compliance_service.check_design_limits(
                    bolt_size=bolt_size,
                    bolt_grade=bolt_grade,
                    preload=estimated_current_preload,
                )
                if cur_check.status == ComplianceStatus.FAIL and cur_check.over_yield:
                    rationale.append("螺栓可能已发生塑性变形，建议更换")
                    return RetorqueAction.REPLACE_AND_REASSEMBLE, "critical", rationale

        lub_eval = self.compliance_service.evaluate_lubricant(
            lubrication_type=lubrication_type,
        )
        if lub_eval.need_replace:
            rationale.append(f"润滑剂状态异常: {'; '.join(lub_eval.warnings)}")

        if preload_loss_pct <= self.retorque_warning_threshold_pct / 2:
            rationale.append(
                f"预紧力损失仅 {preload_loss_pct:.1f}%，低于 {self.retorque_warning_threshold_pct/2:.1f}% 阈值，无需处理"
            )
            return RetorqueAction.NO_ACTION, "info", rationale

        if preload_loss_pct <= self.retorque_warning_threshold_pct:
            rationale.append(
                f"预紧力损失 {preload_loss_pct:.1f}%，在正常松弛范围内（≤{self.retorque_warning_threshold_pct:.1f}%）"
            )
            return RetorqueAction.SLIGHT_TIGHTEN, "low", rationale

        if preload_loss_pct <= self.retorque_critical_threshold_pct:
            rationale.append(
                f"预紧力损失 {preload_loss_pct:.1f}%，超过警告阈值（{self.retorque_warning_threshold_pct:.1f}%），建议复紧至目标值"
            )
            return RetorqueAction.RETORQUE_TO_TARGET, "warning", rationale

        rationale.append(
            f"预紧力损失 {preload_loss_pct:.1f}%，超过临界阈值（{self.retorque_critical_threshold_pct:.1f}%），存在泄漏/失效风险"
        )
        return RetorqueAction.REPLACE_AND_REASSEMBLE, "high", rationale

    # ============== 工艺方案生成 API ==============

    def generate_tightening_plan(
        self,
        bolt_size: str,
        bolt_grade: str,
        target_preload_N: float,
        lubrication_type: str,
        procedure_id: str = "ASME_PCC1_4STEP",
        bolt_count: int = 8,
        tolerance_band: str = "normal",
        start_index: int = 1,
        passes: Optional[int] = None,
        pattern: Optional[str] = None,
        operating_temperature_c: Optional[float] = None,
        lubricant_usage_count: int = 0,
    ) -> TighteningPlan:
        """
        生成完整紧固工艺方案

        参数:
            bolt_size: 螺栓规格 (如 M20)
            bolt_grade: 性能等级 (如 8.8)
            target_preload_N: 目标预紧力 (N)
            lubrication_type: 润滑类型
            procedure_id: 工艺规程 ID
            bolt_count: 螺栓组数量
            tolerance_band: 允差带类型 (tight/normal/loose)
            start_index: 螺栓编号起始值
            passes: 紧固道次数（可选，默认按规程）
            pattern: 交叉顺序模式（可选，自动判断）
            operating_temperature_c: 工作温度
            lubricant_usage_count: 润滑剂使用次数

        返回:
            TighteningPlan: 完整工艺方案
        """
        try:
            torque_result = self.torque_model.calculate_torque(
                bolt_size=bolt_size,
                target_preload=target_preload_N,
                lubrication_type=lubrication_type,
            )
            target_torque_Nm = torque_result.required_torque_Nm

            full_procedure = self.process_model.generate_full_procedure(
                procedure_id=procedure_id,
                bolt_size=bolt_size,
                target_preload=target_preload_N,
                lubrication_type=lubrication_type,
                bolt_count=bolt_count,
                tolerance_band=tolerance_band,
                start_index=start_index,
                passes=passes,
                pattern=pattern,
            )

            process_id = full_procedure.get("process_id")
            tightening_steps = full_procedure.get("tightening_steps", [])
            cross_sequence_data = full_procedure.get("cross_sequence", {})
            cross_sequence = cross_sequence_data.get("sequence_matrix", [])
            turn_angle = full_procedure.get("turn_angle", {})
            turn_angle_deg = turn_angle.get("total_angle_deg") if turn_angle else None
            tolerance_cfg = full_procedure.get("tolerance_band", {})

            retorque_range = self.torque_model.calculate_retorque_range(
                bolt_size=bolt_size,
                target_preload=target_preload_N,
                lubrication_type=lubrication_type,
            )

            warnings: List[str] = []
            compliance_summary: Dict[str, Any] = {}

            design_check = self.compliance_service.check_design_limits(
                bolt_size=bolt_size,
                bolt_grade=bolt_grade,
                preload=target_preload_N,
            )
            compliance_summary["design_limit"] = design_check.to_dict()
            if design_check.status != ComplianceStatus.PASS:
                warnings.extend(design_check.warnings)

            lub_eval = self.compliance_service.evaluate_lubricant(
                lubrication_type=lubrication_type,
                usage_count=lubricant_usage_count,
                operating_temperature_c=operating_temperature_c,
            )
            compliance_summary["lubricant"] = lub_eval.to_dict()
            if lub_eval.need_replace:
                warnings.extend(lub_eval.warnings)

            uniformity_ref = None
            if bolt_count >= 4:
                uniformity_ref = self.process_model.evaluate_uniformity(
                    measured_preloads=[target_preload_N] * bolt_count,
                    target_preload=target_preload_N,
                )
                compliance_summary["uniformity_reference"] = uniformity_ref

            if torque_result.friction_uncertainty_pct > 15:
                warnings.append(
                    f"当前润滑状态摩擦系数不确定度较高（{torque_result.friction_uncertainty_pct:.1f}%），"
                    f"建议使用角度法或液压张拉法提高预紧力精度"
                )

            plan = TighteningPlan(
                process_id=process_id,
                bolt_size=bolt_size,
                bolt_grade=bolt_grade,
                target_preload_N=target_preload_N,
                target_torque_Nm=target_torque_Nm,
                lubrication_type=lubrication_type,
                tightening_method=full_procedure.get(
                    "tightening_method", TighteningMethod.TORQUE_CONTROL.value
                ),
                tolerance_band=tolerance_cfg,
                tightening_steps=tightening_steps,
                cross_sequence=cross_sequence,
                turn_angle_deg=turn_angle_deg,
                retorque_range_Nm={
                    "min_Nm": retorque_range["suggested_min_torque_Nm"],
                    "nominal_Nm": retorque_range["nominal_retorque_Nm"],
                    "max_Nm": retorque_range["suggested_max_torque_Nm"],
                },
                compliance_summary=compliance_summary,
                warnings=warnings,
            )

            logger.info(
                f"工艺方案生成: process_id={process_id} {bolt_size}-{bolt_grade} "
                f"预紧力={target_preload_N:.0f}N 扭矩={target_torque_Nm:.1f}Nm "
                f"规程={procedure_id} 螺栓数={bolt_count}"
            )
            return plan

        except Exception as e:
            logger.error(f"生成紧固工艺方案失败: {e}")
            raise

    # ============== 综合合规审计 API ==============

    def full_compliance_audit(
        self,
        bolt_size: str,
        bolt_grade: str,
        target_preload_N: float,
        measured_preload_list: Optional[List[float]] = None,
        measured_torque_list: Optional[List[float]] = None,
        lubrication_type: str = "molybdenum_disulfide",
        lubricant_usage_count: int = 0,
        operating_temperature_c: Optional[float] = None,
        procedure_id: Optional[str] = None,
        completed_steps: Optional[List[str]] = None,
        expected_steps: Optional[List[Dict[str, Any]]] = None,
        preload_ratio_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行完整合规审计

        包含:
        - 设计极限检查（目标预紧力 vs 屈服/保证载荷）
        - 均匀性评估（实测预紧力离散度）
        - 润滑剂状态评估
        - 工艺步骤完整性检查
        - 关联知识库案例检索
        """
        try:
            measured_preloads = measured_preload_list or []
            if measured_torque_list and not measured_preloads:
                for t in measured_torque_list:
                    res = self.torque_model.calculate_preload_from_torque(
                        bolt_size=bolt_size,
                        measured_torque=t,
                        lubrication_type=lubrication_type,
                    )
                    measured_preloads.append(res.estimated_preload_N)

            design_check = self.compliance_service.check_design_limits(
                bolt_size=bolt_size,
                bolt_grade=bolt_grade,
                preload=target_preload_N,
                preload_ratio_type=preload_ratio_type,
            )

            uniformity_eval: Optional[Dict[str, Any]] = None
            if measured_preloads:
                uniformity_eval = self.process_model.evaluate_uniformity(
                    measured_preloads=measured_preloads,
                    target_preload=target_preload_N,
                )

            lub_eval = self.compliance_service.evaluate_lubricant(
                lubrication_type=lubrication_type,
                usage_count=lubricant_usage_count,
                operating_temperature_c=operating_temperature_c,
            )

            process_compliance: Optional[Dict[str, Any]] = None
            if procedure_id and completed_steps is not None:
                if expected_steps is None:
                    proc = self.process_model.get_standard_procedure(procedure_id)
                    if proc:
                        expected_steps = [s.to_dict() for s in proc.steps]
                if expected_steps:
                    avg_meas_torque = None
                    if measured_torque_list:
                        avg_meas_torque = sum(measured_torque_list) / len(measured_torque_list)
                    process_check = self.compliance_service.check_process_compliance(
                        expected_steps=expected_steps,
                        completed_steps=completed_steps,
                        target_torque_Nm=target_preload_N,
                        measured_torque_Nm=avg_meas_torque,
                    )
                    process_compliance = process_check.to_dict()

            knowledge_cases = self.compliance_service.find_related_knowledge_cases(
                procedure_id=procedure_id,
                bolt_size=bolt_size,
                bolt_grade=bolt_grade,
                tags=["compliance", "audit"],
            )

            overall_status = ComplianceStatus.PASS
            overall_warnings: List[str] = []
            issues: List[str] = []

            if design_check.status == ComplianceStatus.FAIL:
                overall_status = ComplianceStatus.FAIL
                issues.append("设计极限不满足")
                overall_warnings.extend(design_check.warnings)
            elif design_check.status == ComplianceStatus.WARNING and overall_status == ComplianceStatus.PASS:
                overall_status = ComplianceStatus.WARNING
                overall_warnings.extend(design_check.warnings)

            if lub_eval.need_replace:
                if overall_status != ComplianceStatus.FAIL:
                    overall_status = ComplianceStatus.WARNING
                issues.append("润滑剂需要更换")
                overall_warnings.extend(lub_eval.warnings)

            if uniformity_eval and uniformity_eval.get("status") != "ok":
                if overall_status != ComplianceStatus.FAIL:
                    overall_status = ComplianceStatus.WARNING
                issues.append(f"预紧力均匀性: {uniformity_eval.get('status')}")

            if process_compliance and process_compliance.get("status") != "pass":
                if process_compliance.get("status") == "fail":
                    overall_status = ComplianceStatus.FAIL
                elif overall_status == ComplianceStatus.PASS:
                    overall_status = ComplianceStatus.WARNING
                issues.append(f"工艺合规性: {process_compliance.get('status')}")

            target_torque_Nm = None
            try:
                tq_res = self.torque_model.calculate_torque(
                    bolt_size=bolt_size,
                    target_preload=target_preload_N,
                    lubrication_type=lubrication_type,
                )
                target_torque_Nm = tq_res.required_torque_Nm
            except Exception:
                pass

            audit_result = {
                "audit_id": f"AUD-{procedure_id or 'CUSTOM'}-{bolt_size}-{abs(hash(str(target_preload_N) + bolt_grade)) % 10000:04d}",
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "overview": {
                    "bolt_size": bolt_size,
                    "bolt_grade": bolt_grade,
                    "target_preload_N": target_preload_N,
                    "target_torque_Nm": target_torque_Nm,
                    "lubrication_type": lubrication_type,
                    "procedure_id": procedure_id,
                    "overall_status": overall_status.value,
                    "overall_label": COMPLIANCE_STATUS_LABELS[overall_status],
                    "issues": issues,
                    "warnings": overall_warnings,
                },
                "design_limit_check": design_check.to_dict(),
                "uniformity_evaluation": uniformity_eval,
                "lubricant_evaluation": lub_eval.to_dict(),
                "process_compliance": process_compliance,
                "related_knowledge_cases": knowledge_cases,
            }

            logger.info(
                f"合规审计完成: {audit_result['audit_id']} 状态={overall_status.value} "
                f"问题数={len(issues)}"
            )
            return audit_result

        except Exception as e:
            logger.error(f"合规审计执行失败: {e}")
            raise

    # ============== 批量/工具 API ==============

    def batch_measurements_to_preloads(
        self,
        bolt_size: str,
        measured_torque_list: List[float],
        lubrication_type: str,
        bolt_grade: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量将实测扭矩转换为预紧力（供模型训练/推理使用）
        """
        results = []
        for i, torque in enumerate(measured_torque_list):
            try:
                res = self.calculate_preload_from_measurement(
                    bolt_size=bolt_size,
                    measured_torque_Nm=torque,
                    lubrication_type=lubrication_type,
                    bolt_grade=bolt_grade,
                )
                d = res.to_dict()
                d["index"] = i
                results.append(d)
            except Exception as e:
                logger.warning(f"批量处理第 {i} 条数据失败: {e}")
                results.append({
                    "index": i,
                    "measured_torque_Nm": torque,
                    "error": str(e),
                })
        return results

    def list_available_procedures(self) -> List[Dict[str, Any]]:
        """
        列出可用的标准工艺规程
        """
        return self.process_model.list_standard_procedures()

    def list_lubrication_types(self) -> List[Dict[str, Any]]:
        """
        列出所有支持的润滑类型及摩擦系数参数
        """
        return self.torque_model.list_lubrication_types()

    def list_bolt_grades(self) -> List[Dict[str, Any]]:
        """
        列出所有支持的螺栓性能等级及力学参数
        """
        return self.compliance_service.list_bolt_grades()

    def list_thread_specs(self, coarse_only: bool = False) -> List[Dict[str, Any]]:
        """
        列出所有支持的螺纹规格
        """
        return self.torque_model.list_thread_specs(coarse_only=coarse_only)
