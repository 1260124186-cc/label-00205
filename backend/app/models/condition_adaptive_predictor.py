"""
工况自适应预测器模块

基于工况识别的场景自适应预测：
1. 预测前先识别当前工况
2. 根据工况选择对应的基线模型和动态阈值
3. 结合 Prophet 季节性分解进行互补预测
4. 工况变更事件记录与审计

功能:
1. 工况识别与模型自动选择
2. 多工况基线模型管理
3. 异常检测（工况自适应阈值）
4. Prophet 季节性分解互补
5. 工况变更事件追踪
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from app.models.working_condition_classifier import (
    WorkingCondition,
    WorkingConditionClassifier,
    ConditionClassificationResult,
    WORKING_CONDITION_LABELS,
)
from app.models.condition_baseline import (
    ConditionBaselineManager,
    AnomalyResult,
    ConditionBaseline,
)
from app.models.prophet_forecaster import ProphetForecaster, ForecastResult
from app.utils.config import config


@dataclass
class ConditionAdaptivePrediction:
    """
    工况自适应预测结果
    """
    condition: WorkingCondition
    condition_label: str
    condition_confidence: float
    condition_probabilities: Dict[str, float]
    is_transition: bool

    baseline: Optional[Dict[str, Any]]
    anomaly_results: List[Dict[str, Any]]
    anomaly_summary: Dict[str, Any]

    prophet_forecast: Optional[Dict[str, Any]] = None
    seasonal_decomposition: Optional[Dict[str, Any]] = None

    overall_status: str = "normal"
    overall_confidence: float = 0.0

    condition_changed: bool = False
    previous_condition: Optional[WorkingCondition] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'condition': self.condition.value,
            'condition_label': self.condition_label,
            'condition_confidence': self.condition_confidence,
            'condition_probabilities': {
                k.value: v for k, v in self.condition_probabilities.items()
            } if hasattr(next(iter(self.condition_probabilities)), 'value')
            else self.condition_probabilities,
            'is_transition': self.is_transition,
            'baseline': self.baseline,
            'anomaly_summary': self.anomaly_summary,
            'anomalies': self.anomaly_results[:20],
            'prophet_forecast': self.prophet_forecast,
            'seasonal_decomposition': self.seasonal_decomposition,
            'overall_status': self.overall_status,
            'overall_confidence': self.overall_confidence,
            'condition_changed': self.condition_changed,
            'previous_condition': self.previous_condition.value if self.previous_condition else None,
        }


@dataclass
class ConditionChangeEvent:
    """
    工况变更事件
    """
    event_id: str
    node_type: str
    node_id: str
    timestamp: datetime
    from_condition: WorkingCondition
    to_condition: WorkingCondition
    from_confidence: float
    to_confidence: float
    trigger_data_points: int
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'node_type': self.node_type,
            'node_id': self.node_id,
            'timestamp': self.timestamp.isoformat(),
            'from_condition': self.from_condition.value,
            'from_condition_label': WORKING_CONDITION_LABELS[self.from_condition],
            'to_condition': self.to_condition.value,
            'to_condition_label': WORKING_CONDITION_LABELS[self.to_condition],
            'from_confidence': self.from_confidence,
            'to_confidence': self.to_confidence,
            'trigger_data_points': self.trigger_data_points,
            'evidence': self.evidence,
        }


class ConditionAdaptivePredictor:
    """
    工况自适应预测器

    先识别工况，再选择对应模型/阈值进行预测和异常检测。
    支持与 Prophet 季节性分解互补。

    Attributes:
        classifier: 工况分类器
        baseline_manager: 工况基线管理器
        prophet: Prophet 预测器（可选）
        current_conditions: 当前各节点的工况 {node_id: condition}
        change_events: 工况变更事件历史
        max_change_history: 最大事件历史记录数
        enable_prophet_complement: 是否启用 Prophet 互补
    """

    def __init__(
        self,
        classifier: Optional[WorkingConditionClassifier] = None,
        baseline_manager: Optional[ConditionBaselineManager] = None,
        prophet: Optional[ProphetForecaster] = None,
    ):
        """
        初始化工况自适应预测器

        Args:
            classifier: 工况分类器（可选，自动创建）
            baseline_manager: 基线管理器（可选，自动创建）
            prophet: Prophet 预测器（可选）
        """
        self.classifier = classifier or WorkingConditionClassifier()
        self.baseline_manager = baseline_manager or ConditionBaselineManager()
        self.prophet = prophet

        wc_config = config.get('working_condition', {})
        self.max_change_history = wc_config.get('max_change_history', 100)
        self.enable_prophet_complement = wc_config.get(
            'enable_prophet_complement', True
        )
        self.min_data_for_prediction = wc_config.get('min_data_for_prediction', 50)
        self.condition_change_threshold = wc_config.get(
            'condition_change_threshold', 0.6
        )

        self.current_conditions: Dict[str, WorkingCondition] = {}
        self.current_condition_confidences: Dict[str, float] = {}
        self.change_events: Dict[str, List[ConditionChangeEvent]] = {}

        logger.info("工况自适应预测器初始化完成")

    def identify_condition(
        self,
        node_id: str,
        data: np.ndarray,
        historical_data: Optional[np.ndarray] = None,
        use_clustering: bool = False,
    ) -> ConditionClassificationResult:
        """
        识别当前工况

        Args:
            node_id: 节点ID
            data: 当前数据序列
            historical_data: 历史数据（用于基准对比）
            use_clustering: 是否使用聚类方法

        Returns:
            ConditionClassificationResult: 工况分类结果
        """
        result = self.classifier.classify(
            data,
            historical_data=historical_data,
            use_clustering=use_clustering,
        )

        previous_condition = self.current_conditions.get(node_id)
        previous_confidence = self.current_condition_confidences.get(node_id, 0.0)

        condition_changed = (
            previous_condition is not None
            and previous_condition != result.condition
            and result.confidence >= self.condition_change_threshold
        )

        if condition_changed:
            self._record_condition_change(
                node_id=node_id,
                from_condition=previous_condition,
                to_condition=result.condition,
                from_confidence=previous_confidence,
                to_confidence=result.confidence,
                data_points=len(data),
                evidence=result.features,
            )

        self.current_conditions[node_id] = result.condition
        self.current_condition_confidences[node_id] = result.confidence

        return result

    def _record_condition_change(
        self,
        node_id: str,
        from_condition: WorkingCondition,
        to_condition: WorkingCondition,
        from_confidence: float,
        to_confidence: float,
        data_points: int,
        evidence: Dict[str, Any],
        node_type: str = "bolt",
    ) -> ConditionChangeEvent:
        """
        记录工况变更事件

        Args:
            node_id: 节点ID
            from_condition: 原工况
            to_condition: 新工况
            from_confidence: 原置信度
            to_confidence: 新置信度
            data_points: 触发数据点数
            evidence: 证据特征
            node_type: 节点类型

        Returns:
            ConditionChangeEvent: 变更事件
        """
        import uuid

        event = ConditionChangeEvent(
            event_id=str(uuid.uuid4()),
            node_type=node_type,
            node_id=str(node_id),
            timestamp=datetime.now(),
            from_condition=from_condition,
            to_condition=to_condition,
            from_confidence=from_confidence,
            to_confidence=to_confidence,
            trigger_data_points=data_points,
            evidence=evidence,
        )

        if node_id not in self.change_events:
            self.change_events[node_id] = []

        self.change_events[node_id].append(event)

        if len(self.change_events[node_id]) > self.max_change_history:
            self.change_events[node_id].pop(0)

        logger.info(
            f"工况变更: {node_id}, "
            f"{WORKING_CONDITION_LABELS[from_condition]} -> "
            f"{WORKING_CONDITION_LABELS[to_condition]}, "
            f"置信度: {from_confidence:.3f} -> {to_confidence:.3f}"
        )

        return event

    def update_baselines(
        self,
        node_id: str,
        data: np.ndarray,
        condition: Optional[WorkingCondition] = None,
        timestamps: Optional[np.ndarray] = None,
    ) -> Dict[str, bool]:
        """
        更新基线模型

        Args:
            node_id: 节点ID
            data: 数据序列
            condition: 工况（None则自动识别）
            timestamps: 时间戳（用于Prophet）

        Returns:
            更新结果字典
        """
        if condition is None:
            result = self.identify_condition(node_id, data)
            condition = result.condition

        results = {}

        success = self.baseline_manager.update_baseline(condition, data)
        results[condition.value] = success

        if self.enable_prophet_complement and self.prophet is not None:
            if timestamps is not None and len(timestamps) > 10:
                try:
                    self.prophet.fit(data, timestamps)
                    results['prophet'] = True
                except Exception as e:
                    logger.warning(f"Prophet拟合失败: {e}")
                    results['prophet'] = False

        return results

    def predict(
        self,
        node_id: str,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        forecast_days: int = 7,
        historical_data: Optional[np.ndarray] = None,
        node_type: str = "bolt",
    ) -> ConditionAdaptivePrediction:
        """
        工况自适应预测（主接口）

        流程:
            1. 识别当前工况
            2. 选择对应基线模型
            3. 异常检测（动态阈值）
            4. Prophet 季节性分解互补（可选）
            5. 综合结果

        Args:
            node_id: 节点ID
            data: 当前数据序列
            timestamps: 时间戳
            forecast_days: 预测天数
            historical_data: 历史数据
            node_type: 节点类型

        Returns:
            ConditionAdaptivePrediction: 预测结果
        """
        previous_condition = self.current_conditions.get(node_id)

        condition_result = self.identify_condition(
            node_id,
            data,
            historical_data=historical_data,
        )

        condition = condition_result.condition
        condition_changed = previous_condition != condition if previous_condition else False

        baseline = self.baseline_manager.get_baseline(condition)
        baseline_dict = baseline.to_dict() if baseline else None

        anomaly_results = self.baseline_manager.batch_check_anomaly(
            condition, data
        )
        anomaly_dicts = [
            {
                'index': i,
                'value': r.value,
                'is_anomaly': r.is_anomaly,
                'is_warning': r.is_warning,
                'level': r.anomaly_level,
                'type': r.anomaly_type,
                'deviation': r.deviation,
                'confidence': r.confidence,
            }
            for i, r in enumerate(anomaly_results)
        ]

        anomaly_summary = self.baseline_manager.get_anomaly_summary(
            condition, data
        )

        prophet_forecast_dict = None
        seasonal_decomp = None

        if self.enable_prophet_complement and timestamps is not None:
            prophet_result = self._prophet_complement(
                data, timestamps, condition, forecast_days
            )
            if prophet_result:
                prophet_forecast_dict = prophet_result.get('forecast')
                seasonal_decomp = prophet_result.get('seasonal_decomposition')

        anomaly_count = anomaly_summary.get('anomaly_count', 0)
        warning_count = anomaly_summary.get('warning_count', 0)

        if anomaly_count > 0:
            overall_status = "anomaly"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "normal"

        overall_confidence = min(
            1.0,
            condition_result.confidence * 0.4
            + (1.0 - anomaly_summary.get('anomaly_ratio', 0)) * 0.6
        )

        result = ConditionAdaptivePrediction(
            condition=condition,
            condition_label=condition_result.condition_label,
            condition_confidence=condition_result.confidence,
            condition_probabilities=condition_result.probabilities,
            is_transition=condition_result.is_transition,
            baseline=baseline_dict,
            anomaly_results=anomaly_dicts,
            anomaly_summary=anomaly_summary,
            prophet_forecast=prophet_forecast_dict,
            seasonal_decomposition=seasonal_decomp,
            overall_status=overall_status,
            overall_confidence=float(overall_confidence),
            condition_changed=condition_changed,
            previous_condition=previous_condition,
        )

        return result

    def _prophet_complement(
        self,
        data: np.ndarray,
        timestamps: np.ndarray,
        condition: WorkingCondition,
        forecast_days: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Prophet 季节性分解互补

        结合工况进行季节性分解，提供更准确的预测。

        Args:
            data: 数据序列
            timestamps: 时间戳
            condition: 当前工况
            forecast_days: 预测天数

        Returns:
            预测和分解结果字典
        """
        if self.prophet is None:
            return None

        try:
            if not self.prophet.is_fitted:
                self.prophet.fit(data, timestamps)

            forecast = self.prophet.forecast(days=forecast_days)

            seasonal_components = self._extract_seasonal_components(
                forecast, condition
            )

            return {
                'forecast': {
                    'values': forecast.values.tolist()[:forecast_days],
                    'lower_bound': forecast.lower_bound.tolist()[:forecast_days],
                    'upper_bound': forecast.upper_bound.tolist()[:forecast_days],
                    'dates': [d.isoformat() for d in forecast.dates[:forecast_days]],
                    'confidence': forecast.confidence,
                    'anomaly_dates': [
                        (s.isoformat(), e.isoformat())
                        for s, e in forecast.anomaly_dates
                    ],
                },
                'seasonal_decomposition': seasonal_components,
            }

        except Exception as e:
            logger.warning(f"Prophet互补预测失败: {e}")
            return None

    def _extract_seasonal_components(
        self,
        forecast: ForecastResult,
        condition: WorkingCondition,
    ) -> Dict[str, Any]:
        """
        提取季节性分量（结合工况调整）

        Args:
            forecast: Prophet 预测结果
            condition: 当前工况

        Returns:
            季节性分量字典
        """
        try:
            values = forecast.values
            n = len(values)

            if n < 7:
                return {
                    'trend': [],
                    'weekly_seasonal': [],
                    'daily_seasonal': [],
                    'residual': [],
                }

            trend = np.zeros_like(values)
            if len(values) >= 5:
                from scipy.ndimage import uniform_filter1d
                trend = uniform_filter1d(values, size=min(7, len(values) // 2))

            detrended = values - trend

            weekly_seasonal = np.zeros_like(values)
            if len(detrended) >= 7:
                weekly_pattern = np.zeros(7)
                for i in range(7):
                    indices = np.arange(i, len(detrended), 7)
                    if len(indices) > 0:
                        weekly_pattern[i] = np.mean(detrended[indices])
                for i in range(len(detrended)):
                    weekly_seasonal[i] = weekly_pattern[i % 7]

            residual = detrended - weekly_seasonal

            condition_amplitude = self._get_condition_amplitude(condition)
            weekly_seasonal = weekly_seasonal * condition_amplitude

            return {
                'trend': trend.tolist(),
                'weekly_seasonal': weekly_seasonal.tolist(),
                'daily_seasonal': np.zeros_like(values).tolist(),
                'residual': residual.tolist(),
                'condition_amplitude': condition_amplitude,
            }

        except Exception as e:
            logger.warning(f"季节性分量提取失败: {e}")
            return {
                'trend': [],
                'weekly_seasonal': [],
                'daily_seasonal': [],
                'residual': [],
                'error': str(e),
            }

    def _get_condition_amplitude(self, condition: WorkingCondition) -> float:
        """
        获取工况对应的季节性振幅调整系数

        不同工况下季节性的影响程度不同：
        - 稳态运行：季节性影响正常
        - 升/降负荷：季节性影响减弱，趋势主导
        - 停机冷却：季节性影响很弱
        - 检修后恢复：季节性影响中等

        Args:
            condition: 工况

        Returns:
            振幅系数
        """
        amplitudes = {
            WorkingCondition.STEADY_STATE: 1.0,
            WorkingCondition.LOAD_INCREASE: 0.5,
            WorkingCondition.LOAD_DECREASE: 0.5,
            WorkingCondition.SHUTDOWN_COOLING: 0.2,
            WorkingCondition.POST_MAINTENANCE_RECOVERY: 0.7,
            WorkingCondition.UNKNOWN: 0.8,
        }
        return amplitudes.get(condition, 0.8)

    def get_condition_change_history(
        self,
        node_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        获取工况变更历史

        Args:
            node_id: 节点ID
            limit: 返回数量限制

        Returns:
            变更事件列表
        """
        events = self.change_events.get(node_id, [])
        return [event.to_dict() for event in events[-limit:]]

    def get_current_condition(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        获取节点当前工况

        Args:
            node_id: 节点ID

        Returns:
            工况信息字典
        """
        condition = self.current_conditions.get(node_id)
        if condition is None:
            return None

        confidence = self.current_condition_confidences.get(node_id, 0.0)
        return {
            'condition': condition.value,
            'condition_label': WORKING_CONDITION_LABELS[condition],
            'confidence': confidence,
        }

    def get_all_conditions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有节点的当前工况

        Returns:
            各节点工况字典
        """
        result = {}
        for node_id in self.current_conditions:
            condition_info = self.get_current_condition(node_id)
            if condition_info:
                result[node_id] = condition_info
        return result

    def reset_node(self, node_id: str) -> None:
        """
        重置节点状态

        Args:
            node_id: 节点ID
        """
        if node_id in self.current_conditions:
            del self.current_conditions[node_id]
        if node_id in self.current_condition_confidences:
            del self.current_condition_confidences[node_id]
        if node_id in self.change_events:
            del self.change_events[node_id]
        self.classifier.reset_smoothing()
        logger.info(f"节点状态已重置: {node_id}")

    def get_baselines(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有工况基线

        Returns:
            各工况基线字典
        """
        return self.baseline_manager.get_all_baselines()

    def detect_anomalies_with_condition(
        self,
        data: np.ndarray,
        node_id: Optional[str] = None,
        window_size: int = 100,
        step_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        检测长序列中的异常（带工况分段）

        Args:
            data: 长序列数据
            node_id: 节点ID（可选）
            window_size: 窗口大小
            step_size: 步长

        Returns:
            分段检测结果列表
        """
        results = []
        n = len(data)

        for start in range(0, n - window_size + 1, step_size):
            segment = data[start:start + window_size]

            if node_id:
                condition_result = self.identify_condition(node_id, segment)
                condition = condition_result.condition
            else:
                temp_classifier = WorkingConditionClassifier()
                temp_result = temp_classifier.classify(segment)
                condition = temp_result.condition

            anomaly_summary = self.baseline_manager.get_anomaly_summary(
                condition, segment
            )

            results.append({
                'start_index': start,
                'end_index': start + window_size,
                'condition': condition.value,
                'condition_label': WORKING_CONDITION_LABELS[condition],
                **anomaly_summary,
            })

        return results
