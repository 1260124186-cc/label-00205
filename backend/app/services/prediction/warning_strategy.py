"""
预警策略模块

根据置信度和策略类型，对模型预测结果进行调整，
控制预警的灵敏度（应报尽报 vs 精准报警）。

策略源优先级：
1. 数据库 sc_strategy_config（动态配置，定时任务与实时 API 共用）
2. YAML 配置文件 warning_strategy（兜底默认值）

策略二增强：
当 risk_level=中 且 lstm_confidence 低于 lstm_confidence_threshold 时，
提高报警门槛（将 status_code 降级为 0）。

不确定性联动增强：
高认知不确定性 + 中风险时，策略二可降级或升级为需人工复核。
"""

from typing import Tuple, Optional, Dict, Any
from loguru import logger

from app.models.bolt_lstm import STATUS_LABELS
from app.utils.config import config


STATUS_MANUAL_REVIEW = -1
STATUS_LABEL_MANUAL_REVIEW = '需人工复核'


class WarningStrategyPolicy:

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

        self.medium_risk_lstm_threshold = config.get(
            'warning_strategy.strategy_2.medium_risk_lstm_confidence_threshold', 0.6
        )

        self.epistemic_uncertainty_high_threshold = config.get(
            'warning_strategy.uncertainty.epistemic_high_threshold', 0.3
        )
        self.epistemic_uncertainty_critical_threshold = config.get(
            'warning_strategy.uncertainty.epistemic_critical_threshold', 0.5
        )
        self.uncertainty_strategy_action = config.get(
            'warning_strategy.uncertainty.medium_risk_action', 'manual_review'
        )

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
        risk_level: Optional[str] = None,
        lstm_confidence: Optional[float] = None,
        epistemic_uncertainty: Optional[float] = None,
    ) -> Tuple[int, str]:
        effective_threshold = None
        if node_type and node_id:
            try:
                from app.services.prediction.threshold_service import get_effective_threshold
                t = get_effective_threshold(node_type, node_id, 'preload')
                params = t.get('parameters', {})
                if 'confidence_threshold' in params:
                    effective_threshold = params['confidence_threshold']
            except Exception:
                pass

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

            if effective_threshold is not None:
                ct = effective_threshold

            if st == self.STRATEGY_REPORT_ALL:
                return self._apply_with_threshold(
                    status_code, confidence, ct, mode='report_all',
                    epistemic_uncertainty=epistemic_uncertainty,
                )
            else:
                return self._apply_with_threshold(
                    status_code, confidence, ct, mode='precise',
                    risk_level=risk_level, lstm_confidence=lstm_confidence,
                    epistemic_uncertainty=epistemic_uncertainty,
                )

        if self.strategy_type == self.STRATEGY_REPORT_ALL:
            return self._apply_report_all(
                status_code, confidence,
                epistemic_uncertainty=epistemic_uncertainty,
            )
        else:
            return self._apply_precise(
                status_code, confidence,
                risk_level=risk_level, lstm_confidence=lstm_confidence,
                epistemic_uncertainty=epistemic_uncertainty,
            )

    def _apply_report_all(
        self,
        status_code: int,
        confidence: float,
        epistemic_uncertainty: Optional[float] = None,
    ) -> Tuple[int, str]:
        if confidence >= self.strategy_1_threshold:
            new_code = status_code
        else:
            new_code = max(0, status_code - 1)

        if (
            new_code > 0
            and epistemic_uncertainty is not None
            and epistemic_uncertainty >= self.epistemic_uncertainty_critical_threshold
        ):
            logger.info(
                f"策略一不确定性联动: 认知不确定性{epistemic_uncertainty:.3f} >= "
                f"{self.epistemic_uncertainty_critical_threshold}，升级为需人工复核"
            )
            return STATUS_MANUAL_REVIEW, STATUS_LABEL_MANUAL_REVIEW

        return new_code, STATUS_LABELS.get(new_code, '正常')

    def _apply_precise(
        self,
        status_code: int,
        confidence: float,
        risk_level: Optional[str] = None,
        lstm_confidence: Optional[float] = None,
        epistemic_uncertainty: Optional[float] = None,
    ) -> Tuple[int, str]:
        if confidence >= self.strategy_2_threshold:
            new_code = status_code
        else:
            new_code = 0

        if new_code > 0 and risk_level in ('中', 'medium') and lstm_confidence is not None:
            if lstm_confidence < self.medium_risk_lstm_threshold:
                new_code = 0
                logger.info(
                    f"策略二联动: 中风险 + LSTM置信度{lstm_confidence:.3f} < "
                    f"{self.medium_risk_lstm_threshold}，报警门槛提高，降级为正常"
                )

        if (
            new_code > 0
            and epistemic_uncertainty is not None
            and epistemic_uncertainty >= self.epistemic_uncertainty_high_threshold
            and risk_level in ('中', 'medium')
        ):
            action = self.uncertainty_strategy_action
            if action == 'manual_review':
                logger.info(
                    f"策略二不确定性联动: 高不确定性{epistemic_uncertainty:.3f} + "
                    f"中风险 → 升级为需人工复核"
                )
                return STATUS_MANUAL_REVIEW, STATUS_LABEL_MANUAL_REVIEW
            elif action == 'downgrade':
                new_code = 0
                logger.info(
                    f"策略二不确定性联动: 高不确定性{epistemic_uncertainty:.3f} + "
                    f"中风险 → 降级为正常"
                )

        if (
            new_code > 0
            and epistemic_uncertainty is not None
            and epistemic_uncertainty >= self.epistemic_uncertainty_critical_threshold
        ):
            logger.info(
                f"策略二不确定性联动: 极高不确定性{epistemic_uncertainty:.3f} >= "
                f"{self.epistemic_uncertainty_critical_threshold}，升级为需人工复核"
            )
            return STATUS_MANUAL_REVIEW, STATUS_LABEL_MANUAL_REVIEW

        return new_code, STATUS_LABELS.get(new_code, '正常')

    @staticmethod
    def _apply_with_threshold(
        status_code: int,
        confidence: float,
        threshold: float,
        mode: str = 'report_all',
        risk_level: Optional[str] = None,
        lstm_confidence: Optional[float] = None,
        epistemic_uncertainty: Optional[float] = None,
    ) -> Tuple[int, str]:
        epistemic_high = config.get(
            'warning_strategy.uncertainty.epistemic_high_threshold', 0.3
        )
        epistemic_critical = config.get(
            'warning_strategy.uncertainty.epistemic_critical_threshold', 0.5
        )
        action = config.get(
            'warning_strategy.uncertainty.medium_risk_action', 'manual_review'
        )

        if mode == 'report_all':
            if confidence >= threshold:
                new_code = status_code
            else:
                new_code = max(0, status_code - 1)

            if (
                new_code > 0
                and epistemic_uncertainty is not None
                and epistemic_uncertainty >= epistemic_critical
            ):
                return STATUS_MANUAL_REVIEW, STATUS_LABEL_MANUAL_REVIEW
        else:
            if confidence >= threshold:
                new_code = status_code
            else:
                new_code = 0

            if new_code > 0 and risk_level in ('中', 'medium') and lstm_confidence is not None:
                med_threshold = config.get(
                    'warning_strategy.strategy_2.medium_risk_lstm_confidence_threshold', 0.6
                )
                if lstm_confidence < med_threshold:
                    new_code = 0

            if (
                new_code > 0
                and epistemic_uncertainty is not None
                and epistemic_uncertainty >= epistemic_high
                and risk_level in ('中', 'medium')
            ):
                if action == 'manual_review':
                    return STATUS_MANUAL_REVIEW, STATUS_LABEL_MANUAL_REVIEW
                elif action == 'downgrade':
                    new_code = 0

            if (
                new_code > 0
                and epistemic_uncertainty is not None
                and epistemic_uncertainty >= epistemic_critical
            ):
                return STATUS_MANUAL_REVIEW, STATUS_LABEL_MANUAL_REVIEW

        return new_code, STATUS_LABELS.get(new_code, '正常')

    @staticmethod
    def classify_uncertainty(
        epistemic_uncertainty: float,
    ) -> Dict[str, Any]:
        """
        对认知不确定性进行分级

        Args:
            epistemic_uncertainty: 认知不确定性值

        Returns:
            Dict: 不确定性分级信息
        """
        high_threshold = config.get(
            'warning_strategy.uncertainty.epistemic_high_threshold', 0.3
        )
        critical_threshold = config.get(
            'warning_strategy.uncertainty.epistemic_critical_threshold', 0.5
        )

        if epistemic_uncertainty >= critical_threshold:
            level = 'critical'
            label = '极高不确定性'
        elif epistemic_uncertainty >= high_threshold:
            level = 'high'
            label = '高不确定性'
        else:
            level = 'normal'
            label = '正常'

        return {
            'level': level,
            'label': label,
            'value': epistemic_uncertainty,
            'high_threshold': high_threshold,
            'critical_threshold': critical_threshold,
        }
