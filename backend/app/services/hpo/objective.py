"""
优化目标函数模块

实现综合优化目标：验证 F1 + 误报惩罚 + 推理延迟约束

目标函数公式:
    objective = w_f1 * f1_score 
              - w_fp * false_positive_rate 
              - w_latency * max(0, latency - latency_threshold) / latency_threshold

其中:
- w_f1: F1 权重 (默认 1.0)
- w_fp: 误报惩罚系数 (默认 0.5)
- w_latency: 延迟权重 (默认 0.3)
- latency_threshold: 延迟阈值 (默认 100ms)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import time
import json
import numpy as np
import torch
from loguru import logger

from app.services.training_service import TrainingService
from app.models.bolt_lstm import BoltLSTMModel, LSTMNetwork, get_device
from app.models.flange_attention import FlangeAttentionModel


@dataclass
class ObjectiveConfig:
    """优化目标配置"""
    f1_weight: float = 1.0
    false_positive_penalty: float = 0.5
    false_negative_penalty: float = 0.3
    latency_threshold_ms: float = 100.0
    latency_weight: float = 0.3
    min_f1_constraint: Optional[float] = 0.7
    max_latency_constraint: Optional[float] = 200.0
    training_time_weight: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "f1_weight": self.f1_weight,
            "false_positive_penalty": self.false_positive_penalty,
            "false_negative_penalty": self.false_negative_penalty,
            "latency_threshold_ms": self.latency_threshold_ms,
            "latency_weight": self.latency_weight,
            "min_f1_constraint": self.min_f1_constraint,
            "max_latency_constraint": self.max_latency_constraint,
            "training_time_weight": self.training_time_weight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectiveConfig":
        return cls(
            f1_weight=data.get("f1_weight", 1.0),
            false_positive_penalty=data.get("false_positive_penalty", 0.5),
            false_negative_penalty=data.get("false_negative_penalty", 0.3),
            latency_threshold_ms=data.get("latency_threshold_ms", 100.0),
            latency_weight=data.get("latency_weight", 0.3),
            min_f1_constraint=data.get("min_f1_constraint"),
            max_latency_constraint=data.get("max_latency_constraint"),
            training_time_weight=data.get("training_time_weight", 0.0),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "ObjectiveConfig":
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class HPOResult:
    """HPO 试验结果"""
    val_f1_score: float
    val_precision: float
    val_recall: float
    val_accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    inference_latency_ms: float
    training_time_seconds: float
    objective_value: float
    latency_constraint_violated: bool = False
    f1_constraint_violated: bool = False
    extra_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "val_f1_score": self.val_f1_score,
            "val_precision": self.val_precision,
            "val_recall": self.val_recall,
            "val_accuracy": self.val_accuracy,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "inference_latency_ms": self.inference_latency_ms,
            "training_time_seconds": self.training_time_seconds,
            "objective_value": self.objective_value,
            "latency_constraint_violated": self.latency_constraint_violated,
            "f1_constraint_violated": self.f1_constraint_violated,
            "extra_metrics": self.extra_metrics,
        }


def compute_objective(
    f1_score: float,
    false_positive_rate: float,
    false_negative_rate: float,
    inference_latency_ms: float,
    training_time_seconds: float,
    config: ObjectiveConfig,
) -> Tuple[float, bool, bool]:
    """
    计算综合优化目标值

    Args:
        f1_score: 验证集 F1 分数
        false_positive_rate: 误报率
        false_negative_rate: 漏报率
        inference_latency_ms: 推理延迟（毫秒）
        training_time_seconds: 训练耗时（秒）
        config: 优化目标配置

    Returns:
        Tuple[float, bool, bool]: 
            - 综合目标值（越大越好）
            - 是否违反延迟约束
            - 是否违反 F1 约束
    """
    latency_violated = False
    f1_violated = False

    if config.max_latency_constraint and inference_latency_ms > config.max_latency_constraint:
        latency_violated = True

    if config.min_f1_constraint and f1_score < config.min_f1_constraint:
        f1_violated = True

    if latency_violated or f1_violated:
        return -1.0, latency_violated, f1_violated

    latency_penalty = 0.0
    if inference_latency_ms > config.latency_threshold_ms:
        latency_excess = (inference_latency_ms - config.latency_threshold_ms) / config.latency_threshold_ms
        latency_penalty = config.latency_weight * latency_excess

    training_time_penalty = config.training_time_weight * (training_time_seconds / 3600.0)

    objective = (
        config.f1_weight * f1_score
        - config.false_positive_penalty * false_positive_rate
        - config.false_negative_penalty * false_negative_rate
        - latency_penalty
        - training_time_penalty
    )

    return float(objective), latency_violated, f1_violated


def _build_training_config(
    params: Dict[str, Any],
    model_type: str,
) -> Dict[str, Any]:
    """
    根据超参构建训练配置

    Args:
        params: 超参配置
        model_type: 模型类型

    Returns:
        Dict[str, Any]: 训练配置
    """
    num_layers = params.get("num_layers", 2)
    hidden_size = params.get("hidden_size", 128)
    dropout_rate = params.get("dropout_rate", 0.2)
    learning_rate = params.get("learning_rate", 0.001)
    sequence_length = params.get("sequence_length", 100)

    base_config = {
        "batch_size": 32,
        "epochs": 30,
        "learning_rate": learning_rate,
        "validation_split": 0.2,
        "sequence_length": sequence_length,
        "early_stopping": {
            "enabled": True,
            "patience": 5,
            "min_delta": 0.001,
            "mode": "max",
        },
        "class_imbalance": {
            "strategy": "weighted_loss",
        },
    }

    if model_type == "bolt":
        lstm_units = [hidden_size] * num_layers
        if num_layers >= 1:
            base_config["lstm_units_1"] = lstm_units[0]
        if num_layers >= 2:
            base_config["lstm_units_2"] = lstm_units[1] if num_layers > 1 else 64
        base_config["dropout_rate"] = dropout_rate
        base_config["dense_units"] = max(16, hidden_size // 4)

    elif model_type == "flange":
        base_config["lstm_units"] = hidden_size
        base_config["num_attention_layers"] = num_layers
        base_config["attention_heads"] = max(2, hidden_size // 32)
        base_config["dropout_rate"] = dropout_rate

    return base_config


def _measure_inference_latency(
    model: torch.nn.Module,
    sample_input: torch.Tensor,
    device: torch.device,
    num_warmup: int = 10,
    num_measurements: int = 100,
) -> float:
    """
    测量模型推理延迟

    Args:
        model: 模型
        sample_input: 样本输入
        device: 设备
        num_warmup: 预热次数
        num_measurements: 测量次数

    Returns:
        float: 平均推理延迟（毫秒）
    """
    model.eval()
    model.to(device)

    for _ in range(num_warmup):
        with torch.no_grad():
            _ = model(sample_input)

    if device.type == "cuda":
        torch.cuda.synchronize()

    latencies = []
    for _ in range(num_measurements):
        start_time = time.perf_counter()
        with torch.no_grad():
            _ = model(sample_input)
        if device.type == "cuda":
            torch.cuda.synchronize()
        end_time = time.perf_counter()
        latencies.append((end_time - start_time) * 1000.0)

    return float(np.median(latencies))


def evaluate_model_with_params(
    params: Dict[str, Any],
    model_type: str,
    node_id: Optional[str] = None,
    objective_config: Optional[ObjectiveConfig] = None,
    fixed_params: Optional[Dict[str, Any]] = None,
) -> HPOResult:
    """
    使用指定超参训练并评估模型

    Args:
        params: 超参配置
        model_type: 模型类型 (bolt/flange)
        node_id: 节点ID
        objective_config: 优化目标配置
        fixed_params: 固定参数

    Returns:
        HPOResult: 评估结果
    """
    if objective_config is None:
        objective_config = ObjectiveConfig()

    if fixed_params:
        params = {**params, **fixed_params}

    training_config = _build_training_config(params, model_type)

    logger.info(
        f"开始评估模型超参: model_type={model_type}, "
        f"node_id={node_id or 'all'}, params={params}"
    )

    training_start = time.time()

    training_service = TrainingService()
    session_id = training_service.start_training(
        model_type=model_type,
        node_id=node_id,
        force_retrain=True,
        training_config=training_config,
    )

    result = training_service.execute_training(session_id)

    training_time = time.time() - training_start

    if result.get("status") != "completed":
        raise RuntimeError(f"训练失败: {result.get('error', '未知错误')}")

    f1_score = result.get("f1_score", 0.0)
    precision = result.get("precision", 0.0)
    recall = result.get("recall", 0.0)
    accuracy = result.get("final_val_acc", 0.0)

    confusion_matrix = result.get("confusion_matrix")
    false_positive_rate = 0.0
    false_negative_rate = 0.0

    if confusion_matrix is not None:
        try:
            cm = np.array(confusion_matrix)
            if cm.ndim == 2 and cm.shape[0] == cm.shape[1]:
                num_classes = cm.shape[0]
                fp = 0
                fn = 0
                total_negatives = 0
                total_positives = 0

                for i in range(num_classes):
                    for j in range(num_classes):
                        if i != j:
                            fp += cm[j, i]
                            fn += cm[i, j]
                    total_negatives += cm[:, i].sum() - cm[i, i]
                    total_positives += cm[i, :].sum() - cm[i, i]

                false_positive_rate = fp / max(total_negatives, 1)
                false_negative_rate = fn / max(total_positives, 1)
        except Exception as e:
            logger.warning(f"计算误报/漏报率失败: {e}")

    device = get_device()
    try:
        sequence_length = params.get("sequence_length", 100)

        if model_type == "bolt":
            input_dim = 2
            lstm_units_1 = training_config.get("lstm_units_1", 128)
            lstm_units_2 = training_config.get("lstm_units_2", 64)
            dropout_rate = training_config.get("dropout_rate", 0.2)
            dense_units = training_config.get("dense_units", 32)

            model = LSTMNetwork(
                input_dim=input_dim,
                lstm_units_1=lstm_units_1,
                lstm_units_2=lstm_units_2,
                dropout_rate=dropout_rate,
                dense_units=dense_units,
                output_classes=5,
            )
            sample_input = torch.randn(1, sequence_length, input_dim).to(device)

        else:
            model = FlangeAttentionModel(
                flange_id=node_id or "test",
                max_bolts=20,
                sequence_length=sequence_length,
            ).model
            sample_input = (
                torch.randn(1, 20, sequence_length).to(device),
                torch.tensor([20]).to(device),
            )

        inference_latency = _measure_inference_latency(model, sample_input, device)

    except Exception as e:
        logger.warning(f"测量推理延迟失败: {e}")
        inference_latency = 999.0

    objective_value, latency_violated, f1_violated = compute_objective(
        f1_score=f1_score,
        false_positive_rate=false_positive_rate,
        false_negative_rate=false_negative_rate,
        inference_latency_ms=inference_latency,
        training_time_seconds=training_time,
        config=objective_config,
    )

    hpo_result = HPOResult(
        val_f1_score=float(f1_score),
        val_precision=float(precision),
        val_recall=float(recall),
        val_accuracy=float(accuracy),
        false_positive_rate=float(false_positive_rate),
        false_negative_rate=float(false_negative_rate),
        inference_latency_ms=float(inference_latency),
        training_time_seconds=float(training_time),
        objective_value=float(objective_value),
        latency_constraint_violated=latency_violated,
        f1_constraint_violated=f1_violated,
        extra_metrics={
            "training_session_id": session_id,
            "best_epoch": result.get("best_epoch"),
            "total_epochs": result.get("total_epochs"),
            "samples_count": result.get("samples_count"),
            "class_distribution": result.get("class_distribution"),
        },
    )

    logger.info(
        f"超参评估完成: objective={objective_value:.4f}, "
        f"f1={f1_score:.4f}, fpr={false_positive_rate:.4f}, "
        f"latency={inference_latency:.2f}ms, "
        f"latency_violated={latency_violated}, f1_violated={f1_violated}"
    )

    return hpo_result
