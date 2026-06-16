"""
颜色映射模块

将预测状态、健康度指数(HI)、风险等级映射为可视化颜色。
支持多种可视化模式：状态色、HI渐变色、风险色。
"""

from enum import Enum
from typing import Tuple, Dict, Any, Optional
import numpy as np


class VisualizationMode(Enum):
    """可视化模式枚举"""
    STATUS = "status"
    HI = "hi"
    RISK = "risk"


class StatusCode(Enum):
    """状态代码枚举"""
    NORMAL = 0
    ATTENTION = 1
    WARNING = 2
    CRITICAL = 3
    FAULT = 4


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ColorMapper:
    """
    颜色映射器

    将各种状态/数值映射为RGB颜色值。
    支持：
    - 状态色：5级状态对应5种颜色
    - HI渐变色：0-100分对应红-黄-绿渐变
    - 风险色：4级风险对应4种颜色
    """

    def __init__(self):
        self._init_status_colors()
        self._init_risk_colors()
        self._init_hi_gradient()

    def _init_status_colors(self):
        """初始化状态颜色映射"""
        self.status_colors: Dict[int, Tuple[int, int, int]] = {
            StatusCode.NORMAL.value: (76, 175, 80),
            StatusCode.ATTENTION.value: (255, 193, 7),
            StatusCode.WARNING.value: (255, 152, 0),
            StatusCode.CRITICAL.value: (244, 67, 54),
            StatusCode.FAULT.value: (156, 39, 176),
        }

    def _init_risk_colors(self):
        """初始化风险颜色映射"""
        self.risk_colors: Dict[str, Tuple[int, int, int]] = {
            RiskLevel.LOW.value: (76, 175, 80),
            RiskLevel.MEDIUM.value: (255, 193, 7),
            RiskLevel.HIGH.value: (255, 87, 34),
            RiskLevel.CRITICAL.value: (244, 67, 54),
        }

    def _init_hi_gradient(self):
        """初始化HI渐变颜色（0=红色, 50=黄色, 100=绿色）"""
        self.hi_gradient_stops = [
            (0.0, (244, 67, 54)),
            (0.3, (255, 152, 0)),
            (0.5, (255, 193, 7)),
            (0.7, (139, 195, 74)),
            (1.0, (76, 175, 80)),
        ]

    def get_status_color(self, status_code: int) -> Tuple[int, int, int]:
        """
        根据状态代码获取颜色

        Args:
            status_code: 状态代码 (0-4)

        Returns:
            RGB颜色元组
        """
        return self.status_colors.get(status_code, self.status_colors[0])

    def get_hi_color(self, hi_score: float) -> Tuple[int, int, int]:
        """
        根据HI健康度分数获取渐变色

        Args:
            hi_score: 健康度分数 (0-100)

        Returns:
            RGB颜色元组
        """
        hi_score = float(np.clip(hi_score, 0, 100))
        t = hi_score / 100.0

        for i in range(len(self.hi_gradient_stops) - 1):
            t0, c0 = self.hi_gradient_stops[i]
            t1, c1 = self.hi_gradient_stops[i + 1]
            if t0 <= t <= t1:
                ratio = (t - t0) / (t1 - t0) if t1 != t0 else 0
                r = int(c0[0] + (c1[0] - c0[0]) * ratio)
                g = int(c0[1] + (c1[1] - c0[1]) * ratio)
                b = int(c0[2] + (c1[2] - c0[2]) * ratio)
                return (r, g, b)

        return self.hi_gradient_stops[-1][1]

    def get_risk_color(self, risk_level: str) -> Tuple[int, int, int]:
        """
        根据风险等级获取颜色

        Args:
            risk_level: 风险等级 (low/medium/high/critical)

        Returns:
            RGB颜色元组
        """
        return self.risk_colors.get(risk_level, self.risk_colors['low'])

    def get_risk_score_color(self, risk_score: float) -> Tuple[int, int, int]:
        """
        根据风险评分(1-10)获取渐变色

        Args:
            risk_score: 风险评分 (1-10)

        Returns:
            RGB颜色元组
        """
        risk_score = float(np.clip(risk_score, 1, 10))
        t = (risk_score - 1) / 9.0
        r = int(76 + (244 - 76) * t)
        g = int(175 - (175 - 67) * t)
        b = int(80 - (80 - 54) * t)
        return (r, g, b)

    def get_color(
        self,
        mode: str,
        bolt_data: Dict[str, Any]
    ) -> Tuple[int, int, int]:
        """
        根据可视化模式和螺栓数据获取颜色

        Args:
            mode: 可视化模式 (status/hi/risk)
            bolt_data: 螺栓数据字典

        Returns:
            RGB颜色元组
        """
        if mode == VisualizationMode.STATUS.value:
            status_code = bolt_data.get('status_code', 0)
            return self.get_status_color(status_code)
        elif mode == VisualizationMode.HI.value:
            hi_score = bolt_data.get('hi_score', 100)
            return self.get_hi_color(hi_score)
        elif mode == VisualizationMode.RISK.value:
            risk_level = bolt_data.get('risk_level', 'low')
            if risk_level:
                return self.get_risk_color(risk_level)
            risk_score = bolt_data.get('risk_score', 1)
            return self.get_risk_score_color(risk_score)
        else:
            return self.get_status_color(0)

    def rgb_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        """RGB颜色转十六进制字符串"""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def rgb_to_normalized(self, rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """RGB颜色转0-1归一化值"""
        return (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
