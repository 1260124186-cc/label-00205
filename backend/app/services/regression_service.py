"""
回归测试服务（Regression Service）

在金样本集上跑指定模型，计算 accuracy / macro-F1 / weighted-F1 /
混淆矩阵 / per-class 指标，并与基线版本对比。

核心功能:
1. evaluate_model():           对指定版本的模型跑金样本集，计算指标
2. compare_with_baseline():    将指标与基线对比，给出 gate_result
3. model_activate_gate():      model/activate 的门禁逻辑（准确率/F1 下降 >2% 阻断）
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
from loguru import logger

from app.services.golden_samples import (
    get_golden_samples_service,
    GoldenSamplesService,
    GoldenSampleMetrics,
    GoldenSampleVersion,
)
from app.services.prediction import PredictionOrchestrator
from app.utils.config import config


STATUS_LABELS = ["正常", "关注级预警", "检查级预警", "紧急级预警", "故障"]
STATUS_CODES = [0, 1, 2, 3, 4]
NUM_CLASSES = len(STATUS_CODES)

DEFAULT_GATE_THRESHOLD = 0.02


@dataclass
class RegressionPerClassMetrics:
    """单类指标"""
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    support: int = 0


@dataclass
class RegressionResult:
    """回归评估结果"""
    version: str
    golden_sample_version: str
    model_version_used: str
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class_metrics: Dict[str, RegressionPerClassMetrics]
    confusion_matrix: List[List[int]]
    total_samples: int
    evaluation_time_seconds: float
    evaluated_at: str

    def to_metrics_obj(self) -> GoldenSampleMetrics:
        """转为 GoldenSampleMetrics 用于持久化"""
        per_class_f1 = {k: v.f1 for k, v in self.per_class_metrics.items()}
        per_class_p = {k: v.precision for k, v in self.per_class_metrics.items()}
        per_class_r = {k: v.recall for k, v in self.per_class_metrics.items()}
        return GoldenSampleMetrics(
            accuracy=self.accuracy,
            macro_f1=self.macro_f1,
            weighted_f1=self.weighted_f1,
            per_class_f1=per_class_f1,
            per_class_precision=per_class_p,
            per_class_recall=per_class_r,
            confusion_matrix=self.confusion_matrix,
            total_samples=self.total_samples,
            evaluation_model_version=self.model_version_used,
            evaluation_timestamp=self.evaluated_at,
        )


@dataclass
class RegressionGateResult:
    """
    门禁结果

    gate_passed:   是否通过（相对基线下降均 <= threshold）
    delta_accuracy: accuracy 变化量（正值表示比基线好，负值表示更差）
    delta_macro_f1: macro_f1 变化量
    delta_weighted_f1: weighted_f1 变化量
    blocked_reason: 若未通过，说明原因
    details: 详细对比信息
    """
    gate_passed: bool
    threshold: float
    baseline_version: Optional[str]
    target_version: str
    baseline_accuracy: float
    target_accuracy: float
    delta_accuracy: float
    baseline_macro_f1: float
    target_macro_f1: float
    delta_macro_f1: float
    baseline_weighted_f1: float
    target_weighted_f1: float
    delta_weighted_f1: float
    blocked_reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class RegressionService:
    """回归测试服务"""

    def __init__(
        self,
        golden_service: Optional[GoldenSamplesService] = None,
        orchestrator: Optional[PredictionOrchestrator] = None,
        gate_threshold: float = DEFAULT_GATE_THRESHOLD,
    ):
        self.golden = golden_service or get_golden_samples_service()
        self.orchestrator = orchestrator or PredictionOrchestrator()
        self.gate_threshold = float(
            config.get("regression.gate_threshold", gate_threshold)
        )
        logger.info(
            f"回归测试服务初始化完成: "
            f"gate_threshold={self.gate_threshold * 100:.1f}%"
        )

    # =============================================================
    # 核心评估
    # =============================================================

    def evaluate_model(
        self,
        golden_sample_version: Optional[str] = None,
        model_version: Optional[str] = None,
        model_type: str = "bolt",
        node_id_override: Optional[str] = None,
        max_samples: Optional[int] = None,
        fallback_to_rule_based: bool = True,
    ) -> RegressionResult:
        """
        在指定金样本集上评估指定版本的模型

        Args:
            golden_sample_version: 金样本版本（默认用当前基线）
            model_version:         模型版本号（默认用活动版本）
            model_type:            模型类型 bolt/flange
            node_id_override:      可选，node_id 前缀
            max_samples:           可选，限制最多评估窗口数（调试用）
            fallback_to_rule_based: 模型未训练或不可用时是否回退到规则分类器

        Returns:
            RegressionResult
        """
        if golden_sample_version is None:
            baseline = self.golden.get_baseline_version()
            if baseline is None:
                raise RuntimeError("尚未设置基线金样本版本，请先注册或设置 baseline")
            golden_sample_version = baseline.version

        labels = self.golden.load_golden_labels(golden_sample_version)
        if not labels:
            raise RuntimeError(
                f"金样本版本 {golden_sample_version} 无 golden labels 数据"
            )

        if max_samples:
            labels = labels[:max_samples]

        t0 = time.time()
        y_true: List[int] = []
        y_pred: List[int] = []

        for lbl in labels:
            try:
                bolt_id = (
                    node_id_override
                    if node_id_override is not None
                    else str(lbl["bolt_id"])
                )
                values = np.array(lbl["preload_values"], dtype=np.float32)
                if values.ndim == 1:
                    values = values.reshape(-1, 1)

                golden_label = int(lbl["golden_label"])
                y_true.append(golden_label)

                status_code = self._run_single_prediction(
                    bolt_id=bolt_id,
                    values=values,
                    model_type=model_type,
                    model_version=model_version,
                    fallback_to_rule_based=fallback_to_rule_based,
                )
                y_pred.append(status_code)
            except Exception as e:
                logger.debug(f"评估窗口失败 bolt={lbl.get('bolt_id')}: {e}")
                y_pred.append(-1)

        total = len(y_true)
        metrics_data = self._compute_metrics(y_true, y_pred)
        elapsed = time.time() - t0

        result = RegressionResult(
            version=f"reg_{golden_sample_version}_{int(time.time())}",
            golden_sample_version=golden_sample_version,
            model_version_used=model_version or "(active)",
            accuracy=metrics_data["accuracy"],
            macro_f1=metrics_data["macro_f1"],
            weighted_f1=metrics_data["weighted_f1"],
            per_class_metrics=metrics_data["per_class"],
            confusion_matrix=metrics_data["confusion_matrix"],
            total_samples=total,
            evaluation_time_seconds=round(elapsed, 3),
            evaluated_at=datetime.now().isoformat(),
        )

        logger.info(
            f"回归评估完成: 版本={golden_sample_version}, "
            f"样本数={total}, "
            f"accuracy={result.accuracy:.4f}, "
            f"macro_f1={result.macro_f1:.4f}, "
            f"weighted_f1={result.weighted_f1:.4f}, "
            f"耗时={elapsed:.2f}s"
        )
        return result

    def _run_single_prediction(
        self,
        bolt_id: str,
        values: np.ndarray,
        model_type: str,
        model_version: Optional[str],
        fallback_to_rule_based: bool,
    ) -> int:
        """执行单个窗口的预测，返回 status_code"""
        try:
            result = self.orchestrator.predict_bolt(
                bolt_id=bolt_id,
                data=values,
                timestamps=None,
                version=model_version,
                save_to_db=False,
            )
            status_code = int(result.get("status_code", 0))
            if 0 <= status_code < NUM_CLASSES:
                return status_code
        except Exception:
            pass
        if fallback_to_rule_based:
            return self._rule_based_predict(values)
        return 0

    @staticmethod
    def _rule_based_predict(values: np.ndarray) -> int:
        """兜底：基于预紧力范围的规则分类（与 RuleBasedClassifier 对齐）"""
        vals = values.flatten()
        if len(vals) == 0:
            return 0
        last = float(vals[-1])
        mean = float(np.mean(vals))
        nominal = 600.0

        if last < nominal * 0.15 or last < 100:
            return 4
        if last < nominal * 0.4 or mean < nominal * 0.5:
            return 3
        if last < nominal * 0.6 or mean < nominal * 0.7:
            return 2
        if last < nominal * 0.8 or last > nominal * 1.2:
            return 1
        return 0

    # =============================================================
    # 指标计算
    # =============================================================

    def _compute_metrics(
        self, y_true: List[int], y_pred: List[int]
    ) -> Dict[str, Any]:
        """
        计算 accuracy, macro-F1, weighted-F1, per-class 指标, 混淆矩阵
        """
        n = len(y_true)
        if n == 0:
            cm = [[0] * NUM_CLASSES for _ in range(NUM_CLASSES)]
            return {
                "accuracy": 0.0,
                "macro_f1": 0.0,
                "weighted_f1": 0.0,
                "per_class": {
                    str(c): RegressionPerClassMetrics()
                    for c in STATUS_CODES
                },
                "confusion_matrix": cm,
            }

        cm = [[0] * NUM_CLASSES for _ in range(NUM_CLASSES)]
        for t, p in zip(y_true, y_pred):
            if 0 <= t < NUM_CLASSES and 0 <= p < NUM_CLASSES:
                cm[t][p] += 1

        correct = sum(cm[i][i] for i in range(NUM_CLASSES))
        accuracy = correct / n if n > 0 else 0.0

        per_class: Dict[str, RegressionPerClassMetrics] = {}
        f1_sum = 0.0
        weighted_f1_sum = 0.0
        total_valid = 0

        for c in STATUS_CODES:
            tp = cm[c][c]
            fp = sum(cm[r][c] for r in range(NUM_CLASSES)) - tp
            fn = sum(cm[c][r] for r in range(NUM_CLASSES)) - tp
            support = sum(cm[c][r] for r in range(NUM_CLASSES))

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            per_class[str(c)] = RegressionPerClassMetrics(
                precision=round(precision, 6),
                recall=round(recall, 6),
                f1=round(f1, 6),
                support=support,
            )

            if support > 0:
                f1_sum += f1
                weighted_f1_sum += f1 * support
                total_valid += 1

        macro_f1 = f1_sum / total_valid if total_valid > 0 else 0.0
        weighted_f1 = weighted_f1_sum / n if n > 0 else 0.0

        return {
            "accuracy": round(accuracy, 6),
            "macro_f1": round(macro_f1, 6),
            "weighted_f1": round(weighted_f1, 6),
            "per_class": per_class,
            "confusion_matrix": cm,
        }

    # =============================================================
    # 基线对比
    # =============================================================

    def compare_with_baseline(
        self,
        target_result: RegressionResult,
        baseline_version: Optional[str] = None,
    ) -> RegressionGateResult:
        """
        将目标回归结果与基线版本对比，给出门禁判定

        规则：
        - accuracy 下降 > threshold → 不通过
        - macro_f1 下降 > threshold → 不通过
        - weighted_f1 下降 > threshold → 不通过
        - 无基线版本（首次注册）→ 直接通过
        """
        if baseline_version:
            baseline = self.golden.get_version(baseline_version)
        else:
            baseline = self.golden.get_baseline_version()

        if baseline is None:
            return RegressionGateResult(
                gate_passed=True,
                threshold=self.gate_threshold,
                baseline_version=None,
                target_version=target_result.version,
                baseline_accuracy=0.0,
                target_accuracy=target_result.accuracy,
                delta_accuracy=0.0,
                baseline_macro_f1=0.0,
                target_macro_f1=target_result.macro_f1,
                delta_macro_f1=0.0,
                baseline_weighted_f1=0.0,
                target_weighted_f1=target_result.weighted_f1,
                delta_weighted_f1=0.0,
                blocked_reason="",
                details={"note": "无基线版本，首次评估自动通过"},
            )

        bm = baseline.metrics
        delta_acc = target_result.accuracy - bm.accuracy
        delta_macro = target_result.macro_f1 - bm.macro_f1
        delta_weighted = target_result.weighted_f1 - bm.weighted_f1

        reasons = []
        if delta_acc < -self.gate_threshold:
            reasons.append(
                f"accuracy 下降 {abs(delta_acc) * 100:.2f}% "
                f"(> {self.gate_threshold * 100:.1f}% 阈值)"
            )
        if delta_macro < -self.gate_threshold:
            reasons.append(
                f"macro_f1 下降 {abs(delta_macro) * 100:.2f}% "
                f"(> {self.gate_threshold * 100:.1f}% 阈值)"
            )
        if delta_weighted < -self.gate_threshold:
            reasons.append(
                f"weighted_f1 下降 {abs(delta_weighted) * 100:.2f}% "
                f"(> {self.gate_threshold * 100:.1f}% 阈值)"
            )

        per_class_delta = {}
        baseline_per_f1 = bm.per_class_f1 or {}
        for code_str, pc in target_result.per_class_metrics.items():
            base_f1 = float(baseline_per_f1.get(code_str, 0.0))
            per_class_delta[code_str] = {
                "baseline_f1": base_f1,
                "target_f1": pc.f1,
                "delta": round(pc.f1 - base_f1, 6),
                "support": pc.support,
                "label": STATUS_LABELS[int(code_str)]
                if code_str.isdigit() and int(code_str) < len(STATUS_LABELS)
                else code_str,
            }

        gate_passed = len(reasons) == 0

        return RegressionGateResult(
            gate_passed=gate_passed,
            threshold=self.gate_threshold,
            baseline_version=baseline.version,
            target_version=target_result.version,
            baseline_accuracy=bm.accuracy,
            target_accuracy=target_result.accuracy,
            delta_accuracy=round(delta_acc, 6),
            baseline_macro_f1=bm.macro_f1,
            target_macro_f1=target_result.macro_f1,
            delta_macro_f1=round(delta_macro, 6),
            baseline_weighted_f1=bm.weighted_f1,
            target_weighted_f1=target_result.weighted_f1,
            delta_weighted_f1=round(delta_weighted, 6),
            blocked_reason="; ".join(reasons) if reasons else "",
            details={
                "per_class_delta": per_class_delta,
                "target_confusion_matrix": target_result.confusion_matrix,
                "baseline_confusion_matrix": bm.confusion_matrix or [],
                "evaluation_samples": target_result.total_samples,
                "baseline_samples": bm.total_samples,
                "target_model_version": target_result.model_version_used,
                "baseline_model_version": bm.evaluation_model_version,
            },
        )

    # =============================================================
    # model/activate 门禁
    # =============================================================

    def model_activate_gate(
        self,
        model_type: str,
        node_id: str,
        target_model_version: str,
        gate_threshold: Optional[float] = None,
        skip_gate: bool = False,
    ) -> Dict[str, Any]:
        """
        model/activate 门禁：在激活前先跑回归，下降超过阈值则阻断

        Args:
            model_type:           模型类型 bolt/flange
            node_id:              节点ID
            target_model_version: 目标版本号
            gate_threshold:       自定义阈值（默认用配置/构造值）
            skip_gate:            是否跳过门禁（admin override）

        Returns:
            {
              "gate_passed": bool,
              "can_activate": bool,  # gate_passed OR skip_gate
              "skip_gate": bool,
              "threshold": float,
              "blocked_reason": str,
              "regression": { ...RegressionResult },
              "gate": { ...RegressionGateResult },
            }
        """
        original_threshold = self.gate_threshold
        if gate_threshold is not None:
            self.gate_threshold = float(gate_threshold)

        response: Dict[str, Any] = {
            "gate_passed": False,
            "can_activate": False,
            "skip_gate": skip_gate,
            "threshold": self.gate_threshold,
            "blocked_reason": "",
            "regression": None,
            "gate": None,
        }

        try:
            if skip_gate:
                response["gate_passed"] = True
                response["can_activate"] = True
                response["blocked_reason"] = "门禁已被显式跳过（admin override）"
                return response

            baseline_gs = self.golden.get_baseline_version()
            if baseline_gs is None:
                response["gate_passed"] = True
                response["can_activate"] = True
                response["blocked_reason"] = "尚未注册基线金样本，门禁自动跳过"
                return response

            reg_result = self.evaluate_model(
                golden_sample_version=baseline_gs.version,
                model_version=target_model_version,
                model_type=model_type,
                node_id_override=node_id,
            )
            gate_result = self.compare_with_baseline(reg_result)

            response["regression"] = {
                "version": reg_result.version,
                "golden_sample_version": reg_result.golden_sample_version,
                "model_version_used": reg_result.model_version_used,
                "accuracy": reg_result.accuracy,
                "macro_f1": reg_result.macro_f1,
                "weighted_f1": reg_result.weighted_f1,
                "total_samples": reg_result.total_samples,
                "evaluation_time_seconds": reg_result.evaluation_time_seconds,
                "evaluated_at": reg_result.evaluated_at,
            }

            gate_dict = asdict(gate_result)
            pcm = {}
            for k, v in gate_result.details.get("per_class_delta", {}).items():
                pcm[k] = v
            gate_dict["per_class_delta"] = pcm
            gate_dict.pop("details", None)
            response["gate"] = gate_dict
            response["gate_passed"] = gate_result.gate_passed
            response["can_activate"] = gate_result.gate_passed
            response["blocked_reason"] = gate_result.blocked_reason

            if gate_result.gate_passed:
                logger.info(
                    f"model/activate 门禁通过: "
                    f"{model_type}/{node_id} -> {target_model_version}, "
                    f"accΔ={gate_result.delta_accuracy * 100:+.2f}%, "
                    f"macro_f1Δ={gate_result.delta_macro_f1 * 100:+.2f}%"
                )
            else:
                logger.warning(
                    f"model/activate 门禁阻断: "
                    f"{model_type}/{node_id} -> {target_model_version}, "
                    f"原因={gate_result.blocked_reason}"
                )

            return response

        except Exception as e:
            logger.exception(f"model/activate 门禁运行异常: {e}")
            response["gate_passed"] = False
            response["can_activate"] = False
            response["blocked_reason"] = f"门禁运行异常: {str(e)}"
            return response
        finally:
            self.gate_threshold = original_threshold


_regression_service: Optional[RegressionService] = None


def get_regression_service() -> RegressionService:
    """获取回归测试服务单例"""
    global _regression_service
    if _regression_service is None:
        _regression_service = RegressionService()
    return _regression_service
