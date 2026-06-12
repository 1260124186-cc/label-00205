"""
规则分类器模块

当机器学习模型未训练时，使用基于阈值的规则进行状态判断。
"""

import numpy as np
from typing import Tuple, Optional, List
from loguru import logger

from app.utils.config import config


class RuleBasedClassifier:
    """
    基于规则的分类器

    当模型文件不存在或未训练时，使用预定义阈值进行状态判断。
    同时提供法兰面的多螺栓状态聚合能力。

    Attributes:
        min_normal: 正常预紧力下限
        max_normal: 正常预紧力上限
    """

    def __init__(self):
        """
        初始化规则分类器，从配置中读取阈值
        """
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        self.min_normal = thresholds.get('min_normal', 400)
        self.max_normal = thresholds.get('max_normal', 800)
        logger.debug(
            f"规则分类器初始化: 正常范围 [{self.min_normal}, {self.max_normal}]"
        )

    def predict(
        self,
        data: np.ndarray
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """
        基于规则预测单条螺栓状态

        判断逻辑（优先级从高到低）：
        1. 均值超出正常范围 50% → 故障(4)
        2. 均值超出正常范围 20% → 紧急预警(3)
        3. 均值超出正常范围 → 检查预警(2)
        4. 标准差大于均值 20% → 关注预警(1)
        5. 其他 → 正常(0)

        Args:
            data: 预紧力数据数组

        Returns:
            (状态码, 置信度, 概率分布)
            概率分布在规则模式下始终为 None
        """
        mean_val = float(np.mean(data))
        std_val = float(np.std(data))

        if mean_val < self.min_normal * 0.5 or mean_val > self.max_normal * 1.5:
            return 4, 0.8, None
        elif mean_val < self.min_normal * 0.8 or mean_val > self.max_normal * 1.2:
            return 3, 0.7, None
        elif mean_val < self.min_normal or mean_val > self.max_normal:
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
