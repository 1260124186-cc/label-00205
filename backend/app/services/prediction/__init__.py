"""
预测模块

按职责拆分的子模块：
- rule_classifier: 规则分类器（模型未训练时的规则判断）
- warning_strategy: 预警策略（应报尽报 vs 精准报警）
- repository: 数据仓库（历史数据查询、结果持久化、批量数据获取）
- orchestrator: 预测编排器（预处理 → 模型 → 风险 → 策略）
"""

from app.services.prediction.rule_classifier import RuleBasedClassifier
from app.services.prediction.warning_strategy import WarningStrategyPolicy
from app.services.prediction.repository import PredictionRepository
from app.services.prediction.orchestrator import PredictionOrchestrator

__all__ = [
    "RuleBasedClassifier",
    "WarningStrategyPolicy",
    "PredictionRepository",
    "PredictionOrchestrator",
]
