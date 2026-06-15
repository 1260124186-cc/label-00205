"""
预警策略模块

根据置信度和策略类型，对模型预测结果进行调整，
控制预警的灵敏度（应报尽报 vs 精准报警）。

策略源优先级：
1. 数据库 sc_strategy_config（动态配置，定时任务与实时 API 共用）
2. YAML 配置文件 warning_strategy（兜底默认值）
"""

from typing import Tuple, Optional
from loguru import logger

from app.models.bolt_lstm import STATUS_LABELS
from app.utils.config import config


class WarningStrategyPolicy:
    """
    预警策略策略类（Strategy Pattern）

    支持两种策略：
    - 策略1（应报尽报）: 置信度 ≥ 阈值则按原值输出，否则降一级
    - 策略2（精准报警）: 置信度 ≥ 高阈值才按原值输出，否则仅报告正常

    策略参数从数据库 sc_strategy_config 读取（节点级可覆盖全局），
    数据库不可用时回退到 YAML 配置。
    """

    STRATEGY_REPORT_ALL = 1
    STRATEGY_PRECISE = 2

    def __init__(
        self,
        strategy_type: int = None,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        self.strategy_type = strategy_type
        self.strategy_1_threshold = None
        self.strategy_2_threshold = None
        self._node_type = node_type
        self._node_id = node_id

        db_loaded = False
        if strategy_type is None:
            try:
                from app.services.prediction.strategy_config_service import (
                    get_effective_strategy,
                )
                effective = get_effective_strategy(node_type, node_id)
                self.strategy_type = effective.get('strategy_type', self.STRATEGY_REPORT_ALL)
                self.strategy_1_threshold = effective.get('confidence_threshold')
                self.strategy_2_threshold = effective.get('confidence_threshold')
                db_loaded = True
            except Exception:
                pass

        if self.strategy_type is None:
            self.strategy_type = self.STRATEGY_REPORT_ALL

        strategy_config = config.get('warning_strategy', {})
        if self.strategy_1_threshold is None:
            self.strategy_1_threshold = (
                strategy_config.get('strategy_1', {}).get('confidence_threshold', 0.7)
            )
        if self.strategy_2_threshold is None:
            self.strategy_2_threshold = (
                strategy_config.get('strategy_2', {}).get('confidence_threshold', 0.95)
            )

        source = '数据库' if db_loaded else '配置文件'
        logger.debug(
            f"预警策略初始化: 类型={self.strategy_type}, "
            f"阈值1={self.strategy_1_threshold}, 阈值2={self.strategy_2_threshold}, "
            f"来源={source}"
        )

    def apply(
        self,
        status_code: int,
        status: str,
        confidence: float,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Tuple[int, str]:
        if node_type and node_id and (
            node_type != self._node_type or node_id != self._node_id
        ):
            try:
                from app.services.prediction.strategy_config_service import (
                    get_effective_strategy,
                )
                effective = get_effective_strategy(node_type, node_id)
                st = effective.get('strategy_type', self.strategy_type)
                ct = effective.get('confidence_threshold', self.strategy_1_threshold)
            except Exception:
                st = self.strategy_type
                ct = self.strategy_1_threshold

            if st == self.STRATEGY_REPORT_ALL:
                return self._apply_with_threshold(status_code, confidence, ct, mode='report_all')
            else:
                return self._apply_with_threshold(status_code, confidence, ct, mode='precise')

        if self.strategy_type == self.STRATEGY_REPORT_ALL:
            return self._apply_report_all(status_code, confidence)
        else:
            return self._apply_precise(status_code, confidence)

    def _apply_report_all(
        self,
        status_code: int,
        confidence: float
    ) -> Tuple[int, str]:
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
        if confidence >= self.strategy_2_threshold:
            new_code = status_code
        else:
            new_code = 0
        return new_code, STATUS_LABELS.get(new_code, '正常')

    @staticmethod
    def _apply_with_threshold(
        status_code: int,
        confidence: float,
        threshold: float,
        mode: str = 'report_all',
    ) -> Tuple[int, str]:
        if mode == 'report_all':
            if confidence >= threshold:
                new_code = status_code
            else:
                new_code = max(0, status_code - 1)
        else:
            if confidence >= threshold:
                new_code = status_code
            else:
                new_code = 0
        return new_code, STATUS_LABELS.get(new_code, '正常')
