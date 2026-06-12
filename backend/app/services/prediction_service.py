"""
预测服务模块（Facade 兼容层）

本文件为向后兼容保留，职责已拆分至 app.services.prediction 子包：
- RuleBasedClassifier:      规则判断（模型未训练时的兜底）
- WarningStrategyPolicy:    预警策略（应报尽报 / 精准报警）
- PredictionRepository:     DB 读写（历史查询 + 结果持久化）
- PredictionOrchestrator:   编排流水线（预处理 → 模型 → 风险 → 策略）

新代码请直接 import 子包中的类：
    from app.services.prediction import PredictionOrchestrator
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple

from app.models.bolt_lstm import BoltLSTMModel, STATUS_LABELS
from app.models.flange_attention import FlangeAttentionModel
from app.services.prediction import (
    RuleBasedClassifier,
    WarningStrategyPolicy,
    PredictionRepository,
    PredictionOrchestrator,
)


class PredictionService(PredictionOrchestrator):
    """
    预测服务类（兼容层，继承自 PredictionOrchestrator）

    所有功能已在父类 PredictionOrchestrator 中按职责拆分实现。
    本类仅保留原名以供现有调用方无缝升级。

    新增功能请直接修改子包中对应的类，不要在此处添加实现。
    """

    # ---------- 为了保持完全兼容，再暴露底层内部类（如有旧代码访问） ----------

    @property
    def strategy(self) -> int:
        """兼容旧代码读取 self.strategy"""
        return self.warning_policy.strategy_type

    def _rule_based_prediction(
        self, data: np.ndarray
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """兼容旧代码的内部方法名"""
        return self.rule_classifier.predict(data)

    def _aggregate_bolt_predictions(
        self, multi_bolt_data: List[np.ndarray]
    ) -> Tuple[int, float]:
        """兼容旧代码的内部方法名"""
        return self.rule_classifier.aggregate_predictions(multi_bolt_data)

    def _apply_warning_strategy(
        self, status_code: int, status: str, confidence: float
    ) -> Tuple[int, str]:
        """兼容旧代码的内部方法名"""
        return self.warning_policy.apply(status_code, status, confidence)

    def _get_bolt_history(self, bolt_id: str) -> Optional[Dict]:
        """兼容旧代码的内部方法名"""
        return self.repository.get_bolt_history(bolt_id)

    def _get_flange_history(self, flange_id: str) -> Optional[Dict]:
        """兼容旧代码的内部方法名"""
        return self.repository.get_flange_history(flange_id)

    def _save_bolt_prediction(self, bolt_id: str, result: Dict) -> None:
        """兼容旧代码的内部方法名"""
        self.repository.save_bolt_prediction(bolt_id, result)

    def _save_flange_prediction(self, flange_id: str, result: Dict) -> None:
        """兼容旧代码的内部方法名"""
        self.repository.save_flange_prediction(flange_id, result)

    def _save_monthly_prediction(
        self, node_id: str, node_type: str, result: Dict
    ) -> None:
        """兼容旧代码的内部方法名"""
        self.repository.save_monthly_prediction(node_id, node_type, result)
