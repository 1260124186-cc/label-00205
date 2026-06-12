"""
预警策略模块

根据置信度和策略类型，对模型预测结果进行调整，
控制预警的灵敏度（应报尽报 vs 精准报警）。
"""

from typing import Tuple
from loguru import logger

from app.models.bolt_lstm import STATUS_LABELS
from app.utils.config import config


class WarningStrategyPolicy:
    """
    预警策略策略类（Strategy Pattern）

    支持两种策略：
    - 策略1（应报尽报）: 置信度 ≥ 阈值则按原值输出，否则降一级
    - 策略2（精准报警）: 置信度 ≥ 高阈值才按原值输出，否则仅报告正常

    Attributes:
        strategy_type: 策略编号 (1 或 2)
        strategy_1_threshold: 策略1的置信度阈值
        strategy_2_threshold: 策略2的置信度阈值
    """

    STRATEGY_REPORT_ALL = 1
    STRATEGY_PRECISE = 2

    def __init__(self, strategy_type: int = None):
        """
        初始化预警策略

        Args:
            strategy_type: 策略编号，None 时从配置读取
        """
        strategy_config = config.get('warning_strategy', {})
        self.strategy_type = (
            strategy_type
            if strategy_type is not None
            else strategy_config.get('strategy_type', self.STRATEGY_REPORT_ALL)
        )
        self.strategy_1_threshold = (
            strategy_config.get('strategy_1', {}).get('confidence_threshold', 0.7)
        )
        self.strategy_2_threshold = (
            strategy_config.get('strategy_2', {}).get('confidence_threshold', 0.95)
        )
        logger.debug(
            f"预警策略初始化: 类型={self.strategy_type}, "
            f"阈值1={self.strategy_1_threshold}, 阈值2={self.strategy_2_threshold}"
        )

    def apply(
        self,
        status_code: int,
        status: str,
        confidence: float
    ) -> Tuple[int, str]:
        """
        对预测结果应用预警策略

        Args:
            status_code: 原始状态码 (0-4)
            status: 原始状态标签
            confidence: 模型置信度 (0-1)

        Returns:
            (调整后的状态码, 调整后的状态标签)
        """
        if self.strategy_type == self.STRATEGY_REPORT_ALL:
            return self._apply_report_all(status_code, confidence)
        else:
            return self._apply_precise(status_code, confidence)

    def _apply_report_all(
        self,
        status_code: int,
        confidence: float
    ) -> Tuple[int, str]:
        """
        策略一：应报尽报

        置信度充足则原样输出，否则降低一级。
        适用于对漏报敏感的场景。
        """
        if confidence >= self.strategy_1_threshold:
            new_code = status_code
        else:
            new_code = max(0, status_code - 1)
        return new_code, STATUS_LABELS.get(new_code, '正常')

    def _apply_precise(
        self,
        status_code: int,
        confidence: float
    ) -> Tuple[int, str]:
        """
        策略二：精准报警

        仅当置信度极高时输出预警，否则报告正常。
        适用于对误报敏感的场景。
        """
        if confidence >= self.strategy_2_threshold:
            new_code = status_code
        else:
            new_code = 0
        return new_code, STATUS_LABELS.get(new_code, '正常')
