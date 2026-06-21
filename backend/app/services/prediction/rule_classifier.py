"""
规则分类器模块

当机器学习模型未训练时，使用基于阈值的规则进行状态判断。
"""

import numpy as np
from typing import Tuple, Optional, List
from loguru import logger

from app.utils.config import config


class RuleBasedClassifier:

    def __init__(self, node_type: Optional[str] = None, node_id: Optional[str] = None):
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        self.min_normal = thresholds.get('min_normal', 400)
        self.max_normal = thresholds.get('max_normal', 800)
        self._node_type = node_type
        self._node_id = node_id

        if node_type and node_id:
            try:
                from app.services.prediction.threshold_service import get_effective_threshold
                effective = get_effective_threshold(node_type, node_id, 'preload')
                params = effective.get('parameters', {})
                if 'min_normal' in params:
                    self.min_normal = params['min_normal']
                if 'max_normal' in params:
                    self.max_normal = params['max_normal']
            except Exception:
                pass

        logger.debug(
            f"Rule classifier init: range [{self.min_normal}, {self.max_normal}]"
        )

    def predict(
        self,
        data: np.ndarray,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        min_normal = self.min_normal
        max_normal = self.max_normal

        if node_type and node_id and (node_type != self._node_type or node_id != self._node_id):
            try:
                from app.services.prediction.threshold_service import get_effective_threshold
                effective = get_effective_threshold(node_type, node_id, 'preload')
                params = effective.get('parameters', {})
                if 'min_normal' in params:
                    min_normal = params['min_normal']
                if 'max_normal' in params:
                    max_normal = params['max_normal']
            except Exception:
                pass

        mean_val = float(np.mean(data))
        std_val = float(np.std(data))

        if mean_val < min_normal * 0.5 or mean_val > max_normal * 1.5:
            return 4, 0.8, None
        elif mean_val < min_normal * 0.8 or mean_val > max_normal * 1.2:
            return 3, 0.7, None
        elif mean_val < min_normal or mean_val > max_normal:
            return 2, 0.7, None
        elif std_val > mean_val * 0.2:
            return 1, 0.6, None
        else:
            return 0, 0.9, None

    def aggregate_predictions(
        self,
        multi_bolt_data: List[np.ndarray]
    ) -> Tuple[int, float]:
        """
        聚合多个螺栓的状态作为法兰面整体状态

        策略：取所有螺栓中最严重的状态。

        Args:
            multi_bolt_data: 多螺栓数据列表

        Returns:
            (聚合后的状态码, 置信度)
        """
        statuses = []
        for bolt_data in multi_bolt_data:
            status, _, _ = self.predict(bolt_data)
            statuses.append(status)

        max_status = max(statuses) if statuses else 0
        confidence = 0.7

        return max_status, confidence
