"""
故障类型识别模块

识别和区分不同的螺栓故障类型：
1. 松动 (Loosening) - 预紧力逐渐下降
2. 过载 (Overload) - 预紧力突然或持续过高
3. 断裂 (Fracture) - 预紧力急剧下降到极低值

使用示例:
    from app.models.fault_classifier import FaultClassifier
    
    classifier = FaultClassifier()
    result = classifier.classify(preload_data)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
from scipy.signal import find_peaks
from loguru import logger

from app.utils.config import config


class FaultType(Enum):
    """故障类型枚举"""
    NORMAL = "normal"           # 正常
    LOOSENING = "loosening"     # 松动
    OVERLOAD = "overload"       # 过载
    FRACTURE = "fracture"       # 断裂
    FATIGUE = "fatigue"         # 疲劳
    CORROSION = "corrosion"     # 腐蚀
    UNKNOWN = "unknown"         # 未知


@dataclass
class FaultPattern:
    """
    故障模式特征
    
    Attributes:
        trend_slope: 趋势斜率
        volatility: 波动性
        sudden_changes: 突变点数量
        min_value: 最小值
        max_value: 最大值
        mean_value: 平均值
    """
    trend_slope: float
    volatility: float
    sudden_changes: int
    min_value: float
    max_value: float
    mean_value: float
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'trend_slope': self.trend_slope,
            'volatility': self.volatility,
            'sudden_changes': self.sudden_changes,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'mean_value': self.mean_value
        }


@dataclass
class FaultClassificationResult:
    """
    故障分类结果
    
    Attributes:
        fault_type: 主要故障类型
        confidence: 分类置信度
        severity: 严重程度 (1-10)
        pattern: 故障模式特征
        evidence: 判定依据
        recommendations: 处理建议
    """
    fault_type: FaultType
    confidence: float
    severity: int
    pattern: FaultPattern
    evidence: List[str]
    recommendations: List[str]
    
    @property
    def fault_name(self) -> str:
        """获取故障类型名称"""
        names = {
            FaultType.NORMAL: "正常",
            FaultType.LOOSENING: "松动",
            FaultType.OVERLOAD: "过载",
            FaultType.FRACTURE: "断裂",
            FaultType.FATIGUE: "疲劳",
            FaultType.CORROSION: "腐蚀",
            FaultType.UNKNOWN: "未知"
        }
        return names.get(self.fault_type, "未知")


class FaultPatternExtractor:
    """
    故障模式特征提取器
    
    从预紧力时序数据中提取故障相关特征。
    """
    
    def __init__(self):
        """初始化特征提取器"""
        self.thresholds = config.get('risk_assessment.preload_thresholds', {})
        self.min_normal = self.thresholds.get('min_normal', 400)
        self.max_normal = self.thresholds.get('max_normal', 800)
        
    def extract(self, data: np.ndarray) -> FaultPattern:
        """
        提取故障模式特征
        
        Args:
            data: 预紧力数据
            
        Returns:
            FaultPattern: 故障模式特征
        """
        # 趋势分析
        x = np.arange(len(data))
        slope, _, r_value, _, _ = stats.linregress(x, data)
        
        # 波动性
        volatility = np.std(data) / (np.mean(data) + 1e-8)
        
        # 突变检测
        diff = np.abs(np.diff(data))
        threshold = np.mean(diff) + 2 * np.std(diff)
        sudden_changes = np.sum(diff > threshold)
        
        return FaultPattern(
            trend_slope=float(slope),
            volatility=float(volatility),
            sudden_changes=int(sudden_changes),
            min_value=float(np.min(data)),
            max_value=float(np.max(data)),
            mean_value=float(np.mean(data))
        )


class LooseningDetector:
    """
    松动检测器
    
    检测螺栓松动特征：
    - 预紧力持续下降趋势
    - 波动逐渐增大
    - 无突变
    """
    
    def __init__(self, thresholds: Dict[str, float] = None):
        """初始化松动检测器"""
        self.thresholds = thresholds or {
            'slope_threshold': -0.5,      # 下降斜率阈值
            'min_decline_ratio': 0.1,     # 最小下降比例
            'max_volatility': 0.3         # 最大波动率
        }
    
    def detect(self, pattern: FaultPattern) -> Tuple[bool, float, List[str]]:
        """
        检测松动
        
        Args:
            pattern: 故障模式特征
            
        Returns:
            Tuple: (是否松动, 置信度, 依据)
        """
        evidence = []
        score = 0.0
        
        # 检查下降趋势
        if pattern.trend_slope < self.thresholds['slope_threshold']:
            score += 0.4
            evidence.append(f"预紧力呈下降趋势，斜率={pattern.trend_slope:.4f}")
        
        # 检查下降幅度
        decline_ratio = (pattern.max_value - pattern.min_value) / pattern.max_value
        if decline_ratio > self.thresholds['min_decline_ratio']:
            score += 0.3
            evidence.append(f"预紧力下降幅度达{decline_ratio*100:.1f}%")
        
        # 检查波动性（松动通常波动较小）
        if pattern.volatility < self.thresholds['max_volatility']:
            score += 0.2
            evidence.append("波动性在正常范围内")
        
        # 检查突变（松动通常无突变）
        if pattern.sudden_changes < 3:
            score += 0.1
            evidence.append("无明显突变")
        
        is_loosening = score >= 0.5
        
        return is_loosening, score, evidence


class OverloadDetector:
    """
    过载检测器
    
    检测螺栓过载特征：
    - 预紧力超过正常上限
    - 可能伴随突然增加
    """
    
    def __init__(self, max_normal: float = 800):
        """初始化过载检测器"""
        self.max_normal = max_normal
        self.overload_threshold = max_normal * 1.2  # 超过20%为过载
    
    def detect(self, pattern: FaultPattern, data: np.ndarray) -> Tuple[bool, float, List[str]]:
        """
        检测过载
        
        Args:
            pattern: 故障模式特征
            data: 原始数据
            
        Returns:
            Tuple: (是否过载, 置信度, 依据)
        """
        evidence = []
        score = 0.0
        
        # 检查最大值
        if pattern.max_value > self.overload_threshold:
            score += 0.5
            evidence.append(f"预紧力最大值{pattern.max_value:.1f}超过过载阈值{self.overload_threshold:.1f}")
        
        # 检查超载比例
        overload_ratio = np.sum(data > self.max_normal) / len(data)
        if overload_ratio > 0.1:
            score += 0.3
            evidence.append(f"有{overload_ratio*100:.1f}%的数据点超过正常上限")
        
        # 检查上升趋势
        if pattern.trend_slope > 0.5:
            score += 0.2
            evidence.append("预紧力呈上升趋势")
        
        is_overload = score >= 0.5
        
        return is_overload, score, evidence


class FractureDetector:
    """
    断裂检测器
    
    检测螺栓断裂特征：
    - 预紧力急剧下降
    - 最终值接近零或极低
    - 存在明显突变点
    """
    
    def __init__(self, min_normal: float = 400):
        """初始化断裂检测器"""
        self.min_normal = min_normal
        self.fracture_threshold = min_normal * 0.2  # 低于20%为断裂
    
    def detect(self, pattern: FaultPattern, data: np.ndarray) -> Tuple[bool, float, List[str]]:
        """
        检测断裂
        
        Args:
            pattern: 故障模式特征
            data: 原始数据
            
        Returns:
            Tuple: (是否断裂, 置信度, 依据)
        """
        evidence = []
        score = 0.0
        
        # 检查最小值
        if pattern.min_value < self.fracture_threshold:
            score += 0.4
            evidence.append(f"预紧力最小值{pattern.min_value:.1f}低于断裂阈值{self.fracture_threshold:.1f}")
        
        # 检查最终值
        final_value = data[-1] if len(data) > 0 else 0
        if final_value < self.fracture_threshold:
            score += 0.3
            evidence.append(f"当前预紧力{final_value:.1f}处于极低水平")
        
        # 检查突变
        if pattern.sudden_changes > 0:
            score += 0.2
            evidence.append(f"检测到{pattern.sudden_changes}个突变点")
        
        # 检查急剧下降
        if len(data) > 10:
            recent_drop = (data[-10:].max() - data[-1]) / (data[-10:].max() + 1e-8)
            if recent_drop > 0.5:
                score += 0.1
                evidence.append(f"近期预紧力急剧下降{recent_drop*100:.1f}%")
        
        is_fracture = score >= 0.5
        
        return is_fracture, score, evidence


class FaultClassifier:
    """
    故障类型分类器
    
    综合多个检测器进行故障分类。
    """
    
    def __init__(self):
        """初始化故障分类器"""
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        min_normal = thresholds.get('min_normal', 400)
        max_normal = thresholds.get('max_normal', 800)
        
        self.pattern_extractor = FaultPatternExtractor()
        self.loosening_detector = LooseningDetector()
        self.overload_detector = OverloadDetector(max_normal)
        self.fracture_detector = FractureDetector(min_normal)
        
        # 故障处理建议
        self.recommendations = {
            FaultType.NORMAL: [
                "继续保持常规监测",
                "按计划执行定期维护"
            ],
            FaultType.LOOSENING: [
                "立即检查螺栓扭矩",
                "重新拧紧到规定扭矩",
                "检查垫圈和螺纹状态",
                "缩短监测周期"
            ],
            FaultType.OVERLOAD: [
                "立即停机检查",
                "分析过载原因",
                "检查相邻螺栓状态",
                "评估是否需要更换"
            ],
            FaultType.FRACTURE: [
                "紧急停机",
                "更换损坏螺栓",
                "全面检查法兰面所有螺栓",
                "分析断裂原因防止再次发生"
            ],
            FaultType.UNKNOWN: [
                "进行人工检查",
                "收集更多数据",
                "联系专业人员分析"
            ]
        }
        
        logger.info("故障分类器初始化完成")
    
    def classify(self, data: np.ndarray) -> FaultClassificationResult:
        """
        分类故障类型
        
        Args:
            data: 预紧力数据
            
        Returns:
            FaultClassificationResult: 分类结果
        """
        # 提取模式特征
        pattern = self.pattern_extractor.extract(data)
        
        # 各检测器检测
        loosening_result = self.loosening_detector.detect(pattern)
        overload_result = self.overload_detector.detect(pattern, data)
        fracture_result = self.fracture_detector.detect(pattern, data)
        
        # 选择最可能的故障类型
        results = [
            (FaultType.LOOSENING, loosening_result[1], loosening_result[2]),
            (FaultType.OVERLOAD, overload_result[1], overload_result[2]),
            (FaultType.FRACTURE, fracture_result[1], fracture_result[2])
        ]
        
        # 按置信度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        best_type, best_score, best_evidence = results[0]
        
        # 如果所有分数都很低，判定为正常或未知
        if best_score < 0.3:
            best_type = FaultType.NORMAL
            best_evidence = ["各项指标正常"]
        elif best_score < 0.5:
            best_type = FaultType.UNKNOWN
            best_evidence = ["无法明确判定故障类型"]
        
        # 计算严重程度
        severity = self._calculate_severity(best_type, pattern, best_score)
        
        return FaultClassificationResult(
            fault_type=best_type,
            confidence=best_score,
            severity=severity,
            pattern=pattern,
            evidence=best_evidence,
            recommendations=self.recommendations.get(best_type, [])
        )
    
    def _calculate_severity(
        self,
        fault_type: FaultType,
        pattern: FaultPattern,
        confidence: float
    ) -> int:
        """计算故障严重程度"""
        base_severity = {
            FaultType.NORMAL: 1,
            FaultType.LOOSENING: 4,
            FaultType.OVERLOAD: 6,
            FaultType.FRACTURE: 9,
            FaultType.UNKNOWN: 3
        }.get(fault_type, 5)
        
        # 根据置信度调整
        adjusted = base_severity * (0.5 + 0.5 * confidence)
        
        return min(10, max(1, int(adjusted)))
    
    def classify_batch(
        self,
        data_list: List[np.ndarray],
        node_ids: List[str]
    ) -> Dict[str, FaultClassificationResult]:
        """
        批量分类
        
        Args:
            data_list: 预紧力数据列表
            node_ids: 节点ID列表
            
        Returns:
            Dict: {node_id: result}
        """
        results = {}
        
        for node_id, data in zip(node_ids, data_list):
            try:
                results[node_id] = self.classify(data)
            except Exception as e:
                logger.error(f"分类失败 {node_id}: {e}")
                results[node_id] = FaultClassificationResult(
                    fault_type=FaultType.UNKNOWN,
                    confidence=0.0,
                    severity=5,
                    pattern=FaultPattern(0, 0, 0, 0, 0, 0),
                    evidence=[f"分类错误: {str(e)}"],
                    recommendations=["检查数据质量"]
                )
        
        return results
