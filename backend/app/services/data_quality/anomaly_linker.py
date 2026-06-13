"""
异常数据联动模块

与 sc_anomaly_data 表联动，区分真异常与采集异常：
1. 真异常：物理系统真实发生的异常（如预紧力下降、突变）
2. 采集异常：数据采集过程中产生的异常（如缺失、重复、时间错乱、越界、漂移）

设计模式: 责任链模式 (Chain of Responsibility)
通过多个分类器依次判断异常类型。
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger

from app.utils.database import get_db
from app.services.data_quality.rules_engine import (
    QualityCheckResult,
    RuleType,
    RuleViolation,
    RuleSeverity,
)
from app.services.anomaly_detection import AnomalyType


class AnomalyClassification(Enum):
    """异常分类"""
    TRUE_ANOMALY = "true_anomaly"
    COLLECTION_ANOMALY = "collection_anomaly"
    UNCERTAIN = "uncertain"
    MIXED = "mixed"


class CollectionAnomalySubtype(Enum):
    """采集异常子类型"""
    MISSING = "missing"
    DUPLICATE = "duplicate"
    TIME_INVERSION = "time_inversion"
    OUT_OF_BOUNDS = "out_of_bounds"
    DRIFT = "drift"
    SIGNAL_LOSS = "signal_loss"
    NOISE = "noise"


class TrueAnomalySubtype(Enum):
    """真异常子类型"""
    PRELOAD_DROP = "preload_drop"
    SUDDEN_CHANGE = "sudden_change"
    GRADUAL_DEGRADATION = "gradual_degradation"
    OSCILLATION = "oscillation"


@dataclass
class ClassifiedAnomaly:
    """
    分类后的异常记录

    Attributes:
        anomaly_id: 异常数据ID（来自sc_anomaly_data）
        sensor_id: 传感器ID
        anomaly_value: 异常值
        anomaly_type: 原始异常类型
        classification: 分类结果
        subtype: 子类型
        confidence: 分类置信度
        evidence: 分类证据
        quality_violations: 关联的质量违规
        original_time: 原始数据时间
        classify_time: 分类时间
    """
    anomaly_id: Optional[int]
    sensor_id: str
    anomaly_value: float
    anomaly_type: str
    classification: AnomalyClassification
    subtype: Optional[str]
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    quality_violations: List[RuleViolation] = field(default_factory=list)
    original_time: Optional[datetime] = None
    classify_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'anomaly_id': self.anomaly_id,
            'sensor_id': self.sensor_id,
            'anomaly_value': self.anomaly_value,
            'anomaly_type': self.anomaly_type,
            'classification': self.classification.value,
            'subtype': self.subtype,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'quality_violations': [v.to_dict() for v in self.quality_violations],
            'original_time': self.original_time.isoformat() if self.original_time else None,
            'classify_time': self.classify_time.isoformat(),
        }


@dataclass
class AnomalyLinkResult:
    """
    异常联动结果

    Attributes:
        sensor_id: 传感器ID
        total_anomalies: 总异常数
        true_anomalies: 真异常数
        collection_anomalies: 采集异常数
        uncertain_anomalies: 不确定异常数
        classified_anomalies: 分类后的异常列表
        quality_impact_score: 质量影响评分 (0-100，越高表示采集异常影响越大)
    """
    sensor_id: str
    total_anomalies: int
    true_anomalies: int
    collection_anomalies: int
    uncertain_anomalies: int
    classified_anomalies: List[ClassifiedAnomaly]
    quality_impact_score: float

    @property
    def true_anomaly_ratio(self) -> float:
        if self.total_anomalies == 0:
            return 0.0
        return self.true_anomalies / self.total_anomalies

    @property
    def collection_anomaly_ratio(self) -> float:
        if self.total_anomalies == 0:
            return 0.0
        return self.collection_anomalies / self.total_anomalies

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'total_anomalies': self.total_anomalies,
            'true_anomalies': self.true_anomalies,
            'collection_anomalies': self.collection_anomalies,
            'uncertain_anomalies': self.uncertain_anomalies,
            'true_anomaly_ratio': self.true_anomaly_ratio,
            'collection_anomaly_ratio': self.collection_anomaly_ratio,
            'quality_impact_score': self.quality_impact_score,
            'classified_anomalies': [a.to_dict() for a in self.classified_anomalies],
        }


class AnomalyClassifier:
    """
    异常分类器基类
    """

    def classify(
        self,
        anomaly: Dict[str, Any],
        quality_result: Optional[QualityCheckResult] = None,
        context_data: Optional[np.ndarray] = None,
    ) -> Tuple[AnomalyClassification, Optional[str], float, Dict[str, Any]]:
        """
        对异常进行分类

        Args:
            anomaly: 异常数据
            quality_result: 质量检查结果
            context_data: 上下文数据（异常点周围的数据）

        Returns:
            Tuple[AnomalyClassification, Optional[str], float, Dict[str, Any]]:
                - 分类结果
                - 子类型
                - 置信度
                - 证据
        """
        raise NotImplementedError


class QualityBasedClassifier(AnomalyClassifier):
    """
    基于数据质量的异常分类器

    如果异常点同时存在数据质量问题，则判定为采集异常。
    """

    def classify(
        self,
        anomaly: Dict[str, Any],
        quality_result: Optional[QualityCheckResult] = None,
        context_data: Optional[np.ndarray] = None,
    ) -> Tuple[AnomalyClassification, Optional[str], float, Dict[str, Any]]:
        if quality_result is None:
            return AnomalyClassification.UNCERTAIN, None, 0.3, {}

        anomaly_index = anomaly.get('index', -1)

        # 检查该异常点是否在质量违规索引中
        for violation in quality_result.violations:
            if anomaly_index in violation.indices:
                # 根据违规类型确定采集异常子类型
                subtype = self._violation_to_subtype(violation.rule_type)
                confidence = min(0.9, 0.5 + violation.score / 200)

                evidence = {
                    'violation_type': violation.rule_type.value,
                    'violation_severity': violation.severity.value,
                    'violation_score': violation.score,
                    'violation_message': violation.message,
                }

                return (
                    AnomalyClassification.COLLECTION_ANOMALY,
                    subtype,
                    confidence,
                    evidence,
                )

        return AnomalyClassification.UNCERTAIN, None, 0.2, {}

    def _violation_to_subtype(self, rule_type: RuleType) -> Optional[str]:
        """将规则违规类型映射到采集异常子类型"""
        mapping = {
            RuleType.MISSING_RATE: CollectionAnomalySubtype.MISSING.value,
            RuleType.DUPLICATE: CollectionAnomalySubtype.DUPLICATE.value,
            RuleType.TIME_INVERSION: CollectionAnomalySubtype.TIME_INVERSION.value,
            RuleType.OUT_OF_BOUNDS: CollectionAnomalySubtype.OUT_OF_BOUNDS.value,
            RuleType.DRIFT: CollectionAnomalySubtype.DRIFT.value,
        }
        return mapping.get(rule_type)


class PatternBasedClassifier(AnomalyClassifier):
    """
    基于模式的异常分类器

    通过分析异常点周围的数据模式，判断是真异常还是采集异常。
    """

    def __init__(
        self,
        context_window: int = 10,
        preload_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.context_window = context_window
        self.preload_thresholds = preload_thresholds or {
            'min_normal': 400,
            'max_normal': 800,
        }

    def classify(
        self,
        anomaly: Dict[str, Any],
        quality_result: Optional[QualityCheckResult] = None,
        context_data: Optional[np.ndarray] = None,
    ) -> Tuple[AnomalyClassification, Optional[str], float, Dict[str, Any]]:
        if context_data is None or len(context_data) < 3:
            return AnomalyClassification.UNCERTAIN, None, 0.2, {}

        anomaly_value = anomaly.get('anomaly_value', 0.0)
        anomaly_index = min(anomaly.get('index', len(context_data) // 2), len(context_data) - 1)

        # 提取上下文数据
        start_idx = max(0, anomaly_index - self.context_window)
        end_idx = min(len(context_data), anomaly_index + self.context_window + 1)
        window = context_data[start_idx:end_idx]

        if len(window) < 3:
            return AnomalyClassification.UNCERTAIN, None, 0.2, {}

        # 排除异常点本身进行统计
        window_without_anomaly = np.delete(
            window,
            min(anomaly_index - start_idx, len(window) - 1)
        )

        if len(window_without_anomaly) == 0:
            return AnomalyClassification.UNCERTAIN, None, 0.2, {}

        window_mean = float(np.mean(window_without_anomaly))
        window_std = float(np.std(window_without_anomaly)) + 1e-9

        # 计算Z-score
        z_score = abs(anomaly_value - window_mean) / window_std

        evidence = {
            'window_mean': window_mean,
            'window_std': window_std,
            'z_score': z_score,
            'window_size': len(window),
        }

        # 判断是否为单调趋势（渐变退化）
        if len(window) >= 5:
            x = np.arange(len(window))
            slope = float(np.polyfit(x, window, 1)[0])
            evidence['slope'] = slope

            # 判断趋势方向
            if abs(slope) > window_std * 0.1:
                if slope < 0 and anomaly_value < window_mean:
                    return (
                        AnomalyClassification.TRUE_ANOMALY,
                        TrueAnomalySubtype.GRADUAL_DEGRADATION.value,
                        min(0.85, 0.5 + abs(slope) / window_std),
                        {**evidence, 'pattern': 'gradual_degradation'},
                    )

        # 判断是否为突变
        if anomaly_index > 0 and anomaly_index < len(context_data) - 1:
            prev_value = context_data[anomaly_index - 1]
            next_value = context_data[anomaly_index + 1]
            change_to_prev = abs(anomaly_value - prev_value) / (window_std + 1e-9)
            change_to_next = abs(next_value - anomaly_value) / (window_std + 1e-9)

            evidence['change_to_prev'] = change_to_prev
            evidence['change_to_next'] = change_to_next

            # 真异常：突变后维持在新的水平
            if change_to_prev > 3 and change_to_next < 1:
                if anomaly_value < self.preload_thresholds['min_normal']:
                    return (
                        AnomalyClassification.TRUE_ANOMALY,
                        TrueAnomalySubtype.PRELOAD_DROP.value,
                        min(0.9, 0.6 + change_to_prev / 10),
                        {**evidence, 'pattern': 'preload_drop'},
                    )
                else:
                    return (
                        AnomalyClassification.TRUE_ANOMALY,
                        TrueAnomalySubtype.SUDDEN_CHANGE.value,
                        min(0.85, 0.6 + change_to_prev / 10),
                        {**evidence, 'pattern': 'sudden_change'},
                    )

            # 采集异常：孤立点（前后都正常）
            if change_to_prev > 3 and change_to_next > 3:
                return (
                    AnomalyClassification.COLLECTION_ANOMALY,
                    CollectionAnomalySubtype.NOISE.value,
                    min(0.85, 0.5 + min(change_to_prev, change_to_next) / 10),
                    {**evidence, 'pattern': 'isolated_spike'},
                )

        # 越界但模式正常的可能是采集异常
        min_normal = self.preload_thresholds['min_normal']
        max_normal = self.preload_thresholds['max_normal']
        if anomaly_value < min_normal * 0.3 or anomaly_value > max_normal * 2:
            return (
                AnomalyClassification.COLLECTION_ANOMALY,
                CollectionAnomalySubtype.OUT_OF_BOUNDS.value,
                0.7,
                {**evidence, 'pattern': 'extreme_out_of_bounds'},
            )

        # Z-score极高可能是采集异常
        if z_score > 10:
            return (
                AnomalyClassification.COLLECTION_ANOMALY,
                CollectionAnomalySubtype.NOISE.value,
                min(0.8, 0.5 + z_score / 30),
                {**evidence, 'pattern': 'extreme_z_score'},
            )

        # 中等Z-score可能是真异常
        if z_score > 3:
            return (
                AnomalyClassification.TRUE_ANOMALY,
                None,
                min(0.7, 0.4 + z_score / 20),
                {**evidence, 'pattern': 'high_z_score'},
            )

        return AnomalyClassification.UNCERTAIN, None, 0.3, evidence


class AnomalyTypeClassifier(AnomalyClassifier):
    """
    基于原始异常类型的分类器

    利用sc_anomaly_data中记录的原始异常类型辅助分类。
    """

    def classify(
        self,
        anomaly: Dict[str, Any],
        quality_result: Optional[QualityCheckResult] = None,
        context_data: Optional[np.ndarray] = None,
    ) -> Tuple[AnomalyClassification, Optional[str], float, Dict[str, Any]]:
        anomaly_type = anomaly.get('anomaly_type', '')
        evidence = {'original_anomaly_type': anomaly_type}

        # 范围越界类型的异常更可能是采集异常
        if anomaly_type == AnomalyType.OUT_OF_RANGE.value:
            return (
                AnomalyClassification.COLLECTION_ANOMALY,
                CollectionAnomalySubtype.OUT_OF_BOUNDS.value,
                0.5,
                evidence,
            )

        # 突变类型的异常需要进一步判断，但更倾向于真异常
        if anomaly_type == AnomalyType.SUDDEN_CHANGE.value:
            return (
                AnomalyClassification.TRUE_ANOMALY,
                TrueAnomalySubtype.SUDDEN_CHANGE.value,
                0.6,
                evidence,
            )

        # 统计方法检测的异常不确定
        if anomaly_type in [AnomalyType.ZSCORE.value, AnomalyType.IQR.value]:
            return AnomalyClassification.UNCERTAIN, None, 0.4, evidence

        # 孤立森林检测的异常不确定
        if anomaly_type == AnomalyType.ISOLATION_FOREST.value:
            return AnomalyClassification.UNCERTAIN, None, 0.3, evidence

        return AnomalyClassification.UNCERTAIN, None, 0.2, evidence


class AnomalyLinker:
    """
    异常联动器

    协调多个分类器，对异常进行综合分类，并与数据质量检查结果联动。
    """

    def __init__(
        self,
        classifiers: Optional[List[AnomalyClassifier]] = None,
        min_confidence: float = 0.5,
    ):
        """
        初始化异常联动器

        Args:
            classifiers: 分类器列表，按优先级排序
            min_confidence: 最低分类置信度
        """
        self.classifiers = classifiers or [
            QualityBasedClassifier(),
            AnomalyTypeClassifier(),
            PatternBasedClassifier(),
        ]
        self.min_confidence = min_confidence

        logger.info("异常联动器初始化完成")

    def link_and_classify(
        self,
        sensor_id: str,
        anomalies: List[Dict[str, Any]],
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        quality_result: Optional[QualityCheckResult] = None,
    ) -> AnomalyLinkResult:
        """
        对异常进行分类

        Args:
            sensor_id: 传感器ID
            anomalies: 异常数据列表
            data: 完整数据数组
            timestamps: 时间戳数组
            quality_result: 质量检查结果

        Returns:
            AnomalyLinkResult: 分类结果
        """
        classified_anomalies: List[ClassifiedAnomaly] = []
        true_count = 0
        collection_count = 0
        uncertain_count = 0

        for anomaly in anomalies:
            classified = self._classify_single(
                anomaly=anomaly,
                data=data,
                timestamps=timestamps,
                quality_result=quality_result,
            )
            classified_anomalies.append(classified)

            if classified.classification == AnomalyClassification.TRUE_ANOMALY:
                true_count += 1
            elif classified.classification == AnomalyClassification.COLLECTION_ANOMALY:
                collection_count += 1
            else:
                uncertain_count += 1

        # 计算质量影响评分
        quality_impact_score = self._calculate_quality_impact_score(
            collection_count,
            len(anomalies),
            quality_result,
        )

        result = AnomalyLinkResult(
            sensor_id=sensor_id,
            total_anomalies=len(anomalies),
            true_anomalies=true_count,
            collection_anomalies=collection_count,
            uncertain_anomalies=uncertain_count,
            classified_anomalies=classified_anomalies,
            quality_impact_score=quality_impact_score,
        )

        logger.info(
            f"传感器 {sensor_id} 异常分类完成: "
            f"总计 {len(anomalies)}, "
            f"真异常 {true_count} ({result.true_anomaly_ratio:.1%}), "
            f"采集异常 {collection_count} ({result.collection_anomaly_ratio:.1%}), "
            f"不确定 {uncertain_count}"
        )

        return result

    def _classify_single(
        self,
        anomaly: Dict[str, Any],
        data: np.ndarray,
        timestamps: Optional[np.ndarray],
        quality_result: Optional[QualityCheckResult],
    ) -> ClassifiedAnomaly:
        """
        对单个异常进行分类

        Args:
            anomaly: 异常数据
            data: 完整数据数组
            timestamps: 时间戳数组
            quality_result: 质量检查结果

        Returns:
            ClassifiedAnomaly: 分类后的异常
        """
        votes: Dict[AnomalyClassification, List[Tuple[float, Optional[str], Dict[str, Any]]]] = {
            AnomalyClassification.TRUE_ANOMALY: [],
            AnomalyClassification.COLLECTION_ANOMALY: [],
            AnomalyClassification.UNCERTAIN: [],
        }

        # 收集所有分类器的投票
        for classifier in self.classifiers:
            try:
                classification, subtype, confidence, evidence = classifier.classify(
                    anomaly=anomaly,
                    quality_result=quality_result,
                    context_data=data,
                )
                votes[classification].append((confidence, subtype, evidence))
            except Exception as e:
                logger.warning(f"分类器 {classifier.__class__.__name__} 执行失败: {e}")
                votes[AnomalyClassification.UNCERTAIN].append((0.1, None, {'error': str(e)}))

        # 统计投票
        final_classification = AnomalyClassification.UNCERTAIN
        final_subtype = None
        final_confidence = 0.0
        final_evidence: Dict[str, Any] = {}
        final_violations: List[RuleViolation] = []

        # 计算加权投票
        for classification, class_votes in votes.items():
            if not class_votes:
                continue

            total_confidence = sum(c for c, _, _ in class_votes)
            avg_confidence = total_confidence / len(class_votes)

            if avg_confidence > final_confidence and avg_confidence >= self.min_confidence:
                final_classification = classification
                final_confidence = avg_confidence

                # 选择置信度最高的子类型
                best_vote = max(class_votes, key=lambda x: x[0])
                final_subtype = best_vote[1]

                # 合并所有证据
                for _, _, evidence in class_votes:
                    final_evidence.update(evidence)

        # 收集相关的质量违规
        if quality_result is not None:
            anomaly_index = anomaly.get('index', -1)
            for violation in quality_result.violations:
                if anomaly_index in violation.indices:
                    final_violations.append(violation)

        return ClassifiedAnomaly(
            anomaly_id=anomaly.get('id'),
            sensor_id=anomaly.get('sensor_id', ''),
            anomaly_value=float(anomaly.get('anomaly_value', 0.0)),
            anomaly_type=str(anomaly.get('anomaly_type', '')),
            classification=final_classification,
            subtype=final_subtype,
            confidence=final_confidence,
            evidence=final_evidence,
            quality_violations=final_violations,
            original_time=anomaly.get('original_time'),
        )

    def _calculate_quality_impact_score(
        self,
        collection_count: int,
        total_count: int,
        quality_result: Optional[QualityCheckResult],
    ) -> float:
        """
        计算质量影响评分

        Args:
            collection_count: 采集异常数
            total_count: 总异常数
            quality_result: 质量检查结果

        Returns:
            float: 质量影响评分 (0-100，越高表示采集异常影响越大)
        """
        if total_count == 0:
            return 0.0

        # 采集异常比例
        collection_ratio = collection_count / total_count

        # 质量评分惩罚（质量越差，影响越大）
        quality_penalty = 0.0
        if quality_result is not None:
            quality_penalty = (100 - quality_result.overall_score) / 100 * 0.3

        # 综合评分
        impact_score = (collection_ratio + quality_penalty) * 100
        impact_score = max(0.0, min(100.0, impact_score))

        return impact_score

    def fetch_anomalies_from_db(
        self,
        sensor_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        从数据库获取异常数据

        Args:
            sensor_id: 传感器ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量

        Returns:
            List[Dict[str, Any]]: 异常数据列表
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法获取异常数据")
                    return []

                from sqlalchemy import text

                query = """
                    SELECT id, sensor_id, anomaly_value, anomaly_type, 
                           anomaly_score, original_time, details, create_time
                    FROM sc_anomaly_data
                    WHERE sensor_id = :sensor_id
                """
                params = {'sensor_id': str(sensor_id)}

                if start_time:
                    query += " AND original_time >= :start_time"
                    params['start_time'] = start_time
                if end_time:
                    query += " AND original_time <= :end_time"
                    params['end_time'] = end_time

                query += " ORDER BY original_time DESC LIMIT :limit"
                params['limit'] = limit

                result = db.execute(text(query), params)
                anomalies = []

                for i, row in enumerate(result.fetchall()):
                    anomaly_dict = {
                        'id': row[0],
                        'sensor_id': row[1],
                        'anomaly_value': row[2],
                        'anomaly_type': row[3],
                        'anomaly_score': row[4],
                        'original_time': row[5],
                        'details': row[6],
                        'create_time': row[7],
                        'index': i,
                    }
                    anomalies.append(anomaly_dict)

                logger.info(f"从数据库获取到 {len(anomalies)} 条异常数据: sensor_id={sensor_id}")
                return anomalies

        except Exception as e:
            logger.error(f"获取异常数据失败: {e}")
            return []

    def update_classification_to_db(
        self,
        classified_anomalies: List[ClassifiedAnomaly],
    ) -> bool:
        """
        将分类结果更新到数据库

        Args:
            classified_anomalies: 分类后的异常列表

        Returns:
            bool: 是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法更新分类结果")
                    return False

                from sqlalchemy import text

                updated_count = 0
                for anomaly in classified_anomalies:
                    if anomaly.anomaly_id is None:
                        continue

                    update_sql = text("""
                        UPDATE sc_anomaly_data
                        SET classification = :classification,
                            subtype = :subtype,
                            classification_confidence = :confidence,
                            classification_evidence = :evidence
                        WHERE id = :id
                    """)

                    db.execute(update_sql, {
                        'classification': anomaly.classification.value,
                        'subtype': anomaly.subtype,
                        'confidence': anomaly.confidence,
                        'evidence': str(anomaly.evidence),
                        'id': anomaly.anomaly_id,
                    })
                    updated_count += 1

                db.commit()
                logger.info(f"已更新 {updated_count} 条异常分类结果")
                return True

        except Exception as e:
            logger.error(f"更新异常分类结果失败: {e}")
            return False
