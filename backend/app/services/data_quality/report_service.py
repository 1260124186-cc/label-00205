"""
质量报告服务模块

生成数据质量日报，包括：
1. 问题传感器排行
2. 修复建议
3. 整体质量趋势
4. 异常分类统计

设计模式: 模板方法模式 (Template Method Pattern)
"""

import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger

from app.services.data_quality.rules_engine import RuleType, RuleSeverity
from app.services.data_quality.quality_scoring import (
    SensorQualityScore,
    QualityLevel,
    QualityDimension,
)
from app.services.data_quality.anomaly_linker import (
    AnomalyClassification,
)


class RecommendationPriority(Enum):
    """推荐优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RepairRecommendation:
    """
    修复建议

    Attributes:
        sensor_id: 传感器ID
        problem_type: 问题类型
        description: 问题描述
        recommendation: 修复建议
        priority: 优先级
        estimated_effort: 预估工作量（小时）
        affected_metrics: 受影响的质量指标
        evidence: 证据
    """
    sensor_id: str
    problem_type: str
    description: str
    recommendation: str
    priority: RecommendationPriority
    estimated_effort: float = 0.0
    affected_metrics: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'problem_type': self.problem_type,
            'description': self.description,
            'recommendation': self.recommendation,
            'priority': self.priority.value,
            'estimated_effort': self.estimated_effort,
            'affected_metrics': self.affected_metrics,
            'evidence': self.evidence,
        }


@dataclass
class ProblemSensorRanking:
    """
    问题传感器排行

    Attributes:
        rank: 排名
        sensor_id: 传感器ID
        quality_score: 质量评分
        quality_level: 质量等级
        problem_types: 主要问题类型
        violation_count: 违规数量
        anomaly_count: 异常数量
        collection_anomaly_ratio: 采集异常比例
        trend: 质量趋势 ('improving', 'stable', 'declining')
    """
    rank: int
    sensor_id: str
    quality_score: float
    quality_level: QualityLevel
    problem_types: List[str]
    violation_count: int
    anomaly_count: int
    collection_anomaly_ratio: float
    trend: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rank': self.rank,
            'sensor_id': self.sensor_id,
            'quality_score': self.quality_score,
            'quality_level': self.quality_level.value,
            'problem_types': self.problem_types,
            'violation_count': self.violation_count,
            'anomaly_count': self.anomaly_count,
            'collection_anomaly_ratio': self.collection_anomaly_ratio,
            'trend': self.trend,
        }


@dataclass
class DailyQualityReport:
    """
    每日质量报告

    Attributes:
        report_date: 报告日期
        total_sensors: 总传感器数
        average_quality_score: 平均质量评分
        quality_distribution: 各等级传感器数量
        problem_sensors: 问题传感器排行
        recommendations: 修复建议列表
        anomaly_statistics: 异常统计
        quality_trend: 质量趋势（近7天）
        summary: 摘要
        generated_at: 生成时间
    """
    report_date: datetime
    total_sensors: int
    average_quality_score: float
    quality_distribution: Dict[QualityLevel, int]
    problem_sensors: List[ProblemSensorRanking]
    recommendations: List[RepairRecommendation]
    anomaly_statistics: Dict[str, Any]
    quality_trend: List[Dict[str, Any]]
    summary: str
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_date': self.report_date.isoformat(),
            'total_sensors': self.total_sensors,
            'average_quality_score': self.average_quality_score,
            'quality_distribution': {k.value: v for k, v in self.quality_distribution.items()},
            'problem_sensors': [p.to_dict() for p in self.problem_sensors],
            'recommendations': [r.to_dict() for r in self.recommendations],
            'anomaly_statistics': self.anomaly_statistics,
            'quality_trend': self.quality_trend,
            'summary': self.summary,
            'generated_at': self.generated_at.isoformat(),
        }


class QualityReportService:
    """
    质量报告服务

    生成数据质量日报和各种分析报告。
    """

    def __init__(
        self,
        top_n_problems: int = 10,
        min_score_threshold: float = 60.0,
    ):
        """
        初始化报告服务

        Args:
            top_n_problems: 问题传感器排行数量
            min_score_threshold: 问题传感器最低评分阈值
        """
        self.top_n_problems = top_n_problems
        self.min_score_threshold = min_score_threshold

        # 问题类型到修复建议的映射
        self.recommendation_templates = self._init_recommendation_templates()

        logger.info("质量报告服务初始化完成")

    def _init_recommendation_templates(self) -> Dict[str, Dict[str, Any]]:
        """初始化修复建议模板"""
        return {
            RuleType.MISSING_RATE.value: {
                'problem_type': '数据缺失',
                'description': '传感器数据存在较高缺失率',
                'recommendations': [
                    '检查传感器连接是否松动',
                    '检查采集器网络连接稳定性',
                    '检查数据采集程序运行状态',
                    '考虑增加数据重传机制',
                ],
                'priority': RecommendationPriority.HIGH,
                'estimated_effort': 2.0,
            },
            RuleType.DUPLICATE.value: {
                'problem_type': '数据重复',
                'description': '传感器数据存在重复记录',
                'recommendations': [
                    '检查采集程序是否存在重复提交',
                    '检查数据库去重机制是否正常',
                    '检查采集器时钟同步',
                ],
                'priority': RecommendationPriority.MEDIUM,
                'estimated_effort': 1.0,
            },
            RuleType.TIME_INVERSION.value: {
                'problem_type': '时间倒挂',
                'description': '数据时间戳存在倒流现象',
                'recommendations': [
                    '检查采集器系统时钟是否正常',
                    '检查NTP时间同步服务',
                    '检查数据传输过程中的乱序问题',
                    '考虑在接收端增加时间戳校验',
                ],
                'priority': RecommendationPriority.HIGH,
                'estimated_effort': 3.0,
            },
            RuleType.OUT_OF_BOUNDS.value: {
                'problem_type': '数据越界',
                'description': '数据值超出合理范围',
                'recommendations': [
                    '检查传感器校准是否正确',
                    '检查传感器量程设置',
                    '检查是否存在电磁干扰',
                    '考虑更换老化的传感器',
                ],
                'priority': RecommendationPriority.HIGH,
                'estimated_effort': 4.0,
            },
            RuleType.DRIFT.value: {
                'problem_type': '数据漂移',
                'description': '数据统计特性发生显著漂移',
                'recommendations': [
                    '进行传感器重新校准',
                    '检查传感器安装位置是否变动',
                    '检查环境条件变化（温度、湿度等）',
                    '考虑传感器老化，必要时更换',
                ],
                'priority': RecommendationPriority.MEDIUM,
                'estimated_effort': 3.0,
            },
            'low_quality': {
                'problem_type': '综合质量差',
                'description': '传感器综合数据质量低于阈值',
                'recommendations': [
                    '进行全面的传感器健康检查',
                    '检查采集链路各环节',
                    '考虑更换传感器',
                    '升级数据采集系统',
                ],
                'priority': RecommendationPriority.CRITICAL,
                'estimated_effort': 8.0,
            },
            'high_collection_anomaly': {
                'problem_type': '采集异常过多',
                'description': '异常数据中采集异常占比过高',
                'recommendations': [
                    '排查采集系统故障',
                    '优化数据采集算法',
                    '增加数据校验机制',
                    '考虑升级采集硬件',
                ],
                'priority': RecommendationPriority.HIGH,
                'estimated_effort': 5.0,
            },
        }

    def generate_daily_report(
        self,
        engine: Any,
        report_date: Optional[datetime] = None,
        sensor_ids: Optional[List[str]] = None,
        save_to_db: bool = True,
    ) -> DailyQualityReport:
        """
        生成每日质量报告

        Args:
            engine: 数据质量引擎实例
            report_date: 报告日期，默认今天
            sensor_ids: 传感器ID列表
            save_to_db: 是否保存到数据库

        Returns:
            DailyQualityReport: 每日质量报告
        """
        if report_date is None:
            report_date = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        logger.info(f"开始生成 {report_date.date()} 的质量报告")

        # Step 1: 获取各传感器的最新质量评分
        quality_scores = self._get_quality_scores(engine, sensor_ids)

        if not quality_scores:
            logger.warning("没有可用的质量评分数据")
            return self._create_empty_report(report_date)

        # Step 2: 计算整体统计
        total_sensors = len(quality_scores)
        average_score = float(np.mean([s.overall_score for s in quality_scores]))
        quality_dist = self._calculate_quality_distribution(quality_scores)

        # Step 3: 生成问题传感器排行
        problem_sensors = self._generate_problem_sensor_ranking(quality_scores, engine)

        # Step 4: 生成修复建议
        recommendations = self._generate_recommendations(quality_scores, problem_sensors)

        # Step 5: 异常统计
        anomaly_stats = self._calculate_anomaly_statistics(quality_scores, engine)

        # Step 6: 质量趋势
        quality_trend = self._calculate_quality_trend(engine, sensor_ids)

        # Step 7: 生成摘要
        summary = self._generate_summary(
            total_sensors=total_sensors,
            average_score=average_score,
            quality_dist=quality_dist,
            problem_count=len(problem_sensors),
            critical_count=sum(
                1 for r in recommendations
                if r.priority == RecommendationPriority.CRITICAL
            ),
        )

        report = DailyQualityReport(
            report_date=report_date,
            total_sensors=total_sensors,
            average_quality_score=average_score,
            quality_distribution=quality_dist,
            problem_sensors=problem_sensors,
            recommendations=recommendations,
            anomaly_statistics=anomaly_stats,
            quality_trend=quality_trend,
            summary=summary,
        )

        if save_to_db:
            self._save_report_to_db(report)

        logger.info(
            f"质量报告生成完成: 平均评分 {average_score:.1f}, "
            f"问题传感器 {len(problem_sensors)} 个, "
            f"修复建议 {len(recommendations)} 条"
        )

        return report

    def _get_quality_scores(
        self,
        engine: Any,
        sensor_ids: Optional[List[str]],
    ) -> List[SensorQualityScore]:
        """获取传感器质量评分"""
        scores = []

        if sensor_ids is None:
            # 从引擎历史中获取所有传感器
            sensor_ids = list(engine._score_history.keys())

        for sensor_id in sensor_ids:
            history = engine._score_history.get(sensor_id, [])
            if history:
                scores.append(history[-1])

        return scores

    def _calculate_quality_distribution(
        self,
        scores: List[SensorQualityScore],
    ) -> Dict[QualityLevel, int]:
        """计算各质量等级的传感器数量"""
        distribution = {
            QualityLevel.EXCELLENT: 0,
            QualityLevel.GOOD: 0,
            QualityLevel.FAIR: 0,
            QualityLevel.POOR: 0,
            QualityLevel.CRITICAL: 0,
        }

        for score in scores:
            distribution[score.overall_level] += 1

        return distribution

    def _generate_problem_sensor_ranking(
        self,
        scores: List[SensorQualityScore],
        engine: Any,
    ) -> List[ProblemSensorRanking]:
        """生成问题传感器排行"""
        problem_sensors = []

        for score in scores:
            if score.overall_score >= self.min_score_threshold:
                continue

            # 确定问题类型
            problem_types = self._identify_problem_types(score)

            # 计算违规数量
            violation_count = sum(score.rule_violations_count.values())

            # 计算异常统计（简化处理）
            anomaly_count = violation_count
            collection_anomaly_ratio = self._estimate_collection_anomaly_ratio(score)

            # 确定趋势
            trend = self._determine_trend(score.sensor_id, engine)

            problem_sensors.append({
                'score': score,
                'problem_types': problem_types,
                'violation_count': violation_count,
                'anomaly_count': anomaly_count,
                'collection_anomaly_ratio': collection_anomaly_ratio,
                'trend': trend,
            })

        # 按质量评分升序排列（分数越低，问题越严重）
        problem_sensors.sort(key=lambda x: x['score'].overall_score)

        # 取前N个
        top_problems = problem_sensors[:self.top_n_problems]

        # 转换为ProblemSensorRanking对象
        rankings = []
        for i, ps in enumerate(top_problems, 1):
            rankings.append(ProblemSensorRanking(
                rank=i,
                sensor_id=ps['score'].sensor_id,
                quality_score=ps['score'].overall_score,
                quality_level=ps['score'].overall_level,
                problem_types=ps['problem_types'],
                violation_count=ps['violation_count'],
                anomaly_count=ps['anomaly_count'],
                collection_anomaly_ratio=ps['collection_anomaly_ratio'],
                trend=ps['trend'],
            ))

        return rankings

    def _identify_problem_types(
        self,
        score: SensorQualityScore,
    ) -> List[str]:
        """识别问题类型"""
        problem_types = []

        # 检查各维度评分
        dimension_threshold = 70.0
        for dim, dim_score in score.dimensions.items():
            if dim_score.score < dimension_threshold:
                problem_types.append(dim.value)

        # 检查严重违规
        if score.rule_violations_count.get(RuleSeverity.CRITICAL, 0) > 0:
            problem_types.append('critical_violations')
        if score.rule_violations_count.get(RuleSeverity.ERROR, 0) > 0:
            problem_types.append('error_violations')

        return list(set(problem_types))

    def _estimate_collection_anomaly_ratio(
        self,
        score: SensorQualityScore,
    ) -> float:
        """估算采集异常比例"""
        # 基于完整性和一致性维度评分估算
        completeness_score = score.dimensions.get(
            QualityDimension.COMPLETENESS
        ).score if QualityDimension.COMPLETENESS in score.dimensions else 100
        consistency_score = score.dimensions.get(
            QualityDimension.CONSISTENCY
        ).score if QualityDimension.CONSISTENCY in score.dimensions else 100

        # 分数越低，采集异常比例越高
        avg_collect_score = (completeness_score + consistency_score) / 2
        ratio = max(0.0, min(1.0, (100 - avg_collect_score) / 100))

        return ratio

    def _determine_trend(
        self,
        sensor_id: str,
        engine: Any,
    ) -> str:
        """确定质量趋势"""
        history = engine._score_history.get(sensor_id, [])
        if len(history) < 3:
            return 'stable'

        recent_scores = [s.overall_score for s in history[-5:]]
        if len(recent_scores) < 2:
            return 'stable'

        # 计算斜率
        x = np.arange(len(recent_scores))
        slope = float(np.polyfit(x, recent_scores, 1)[0])

        if slope > 1:
            return 'improving'
        elif slope < -1:
            return 'declining'
        else:
            return 'stable'

    def _generate_recommendations(
        self,
        scores: List[SensorQualityScore],
        problem_sensors: List[ProblemSensorRanking],
    ) -> List[RepairRecommendation]:
        """生成修复建议"""
        recommendations = []

        # 为每个问题传感器生成建议
        for ranking in problem_sensors:
            sensor_id = ranking.sensor_id
            sensor_score = None

            # 找到对应的评分
            for s in scores:
                if s.sensor_id == sensor_id:
                    sensor_score = s
                    break

            if sensor_score is None:
                continue

            # 基于最低维度评分生成建议
            lowest_dimension = None
            lowest_score = 100.0

            for dim, dim_score in sensor_score.dimensions.items():
                if dim_score.score < lowest_score:
                    lowest_score = dim_score.score
                    lowest_dimension = dim

            if lowest_dimension is not None:
                # 将维度映射到规则类型
                rule_type_map = {
                    QualityDimension.COMPLETENESS: RuleType.MISSING_RATE.value,
                    QualityDimension.CONSISTENCY: RuleType.DUPLICATE.value,
                    QualityDimension.VALIDITY: RuleType.OUT_OF_BOUNDS.value,
                    QualityDimension.STABILITY: RuleType.DRIFT.value,
                }

                rule_type = rule_type_map.get(lowest_dimension)
                if rule_type and rule_type in self.recommendation_templates:
                    template = self.recommendation_templates[rule_type]
                    recommendation = self._create_recommendation(
                        sensor_id=sensor_id,
                        template=template,
                        score=sensor_score,
                        dimension=lowest_dimension,
                        dimension_score=lowest_score,
                    )
                    recommendations.append(recommendation)

            # 如果评分特别低，增加综合建议
            if sensor_score.overall_score < 40:
                template = self.recommendation_templates['low_quality']
                recommendation = self._create_recommendation(
                    sensor_id=sensor_id,
                    template=template,
                    score=sensor_score,
                    dimension=None,
                    dimension_score=sensor_score.overall_score,
                )
                recommendations.append(recommendation)

            # 如果采集异常比例高，增加采集系统建议
            if ranking.collection_anomaly_ratio > 0.5:
                template = self.recommendation_templates['high_collection_anomaly']
                recommendation = self._create_recommendation(
                    sensor_id=sensor_id,
                    template=template,
                    score=sensor_score,
                    dimension=None,
                    dimension_score=ranking.collection_anomaly_ratio * 100,
                    extra_evidence={
                        'collection_anomaly_ratio': ranking.collection_anomaly_ratio,
                    },
                )
                recommendations.append(recommendation)

        # 按优先级排序
        priority_order = [
            RecommendationPriority.CRITICAL,
            RecommendationPriority.HIGH,
            RecommendationPriority.MEDIUM,
            RecommendationPriority.LOW,
        ]
        recommendations.sort(key=lambda r: priority_order.index(r.priority))

        return recommendations

    def _create_recommendation(
        self,
        sensor_id: str,
        template: Dict[str, Any],
        score: SensorQualityScore,
        dimension: Optional[QualityDimension],
        dimension_score: float,
        extra_evidence: Optional[Dict[str, Any]] = None,
    ) -> RepairRecommendation:
        """创建修复建议"""
        evidence = {
            'overall_score': score.overall_score,
            'dimension': dimension.value if dimension else 'overall',
            'dimension_score': dimension_score,
            'violations': {
                k.value: v for k, v in score.rule_violations_count.items()
            },
        }
        if extra_evidence:
            evidence.update(extra_evidence)

        # 根据评分调整优先级
        priority = template['priority']
        if dimension_score < 40:
            if priority == RecommendationPriority.HIGH:
                priority = RecommendationPriority.CRITICAL
            elif priority == RecommendationPriority.MEDIUM:
                priority = RecommendationPriority.HIGH

        affected_metrics = [dimension.value] if dimension else ['overall_quality']

        return RepairRecommendation(
            sensor_id=sensor_id,
            problem_type=template['problem_type'],
            description=template['description'],
            recommendation='; '.join(template['recommendations']),
            priority=priority,
            estimated_effort=template['estimated_effort'],
            affected_metrics=affected_metrics,
            evidence=evidence,
        )

    def _calculate_anomaly_statistics(
        self,
        scores: List[SensorQualityScore],
        engine: Any,
    ) -> Dict[str, Any]:
        """计算异常统计"""
        total_violations = 0
        severity_counts = {
            RuleSeverity.CRITICAL.value: 0,
            RuleSeverity.ERROR.value: 0,
            RuleSeverity.WARNING.value: 0,
            RuleSeverity.INFO.value: 0,
        }

        for score in scores:
            for severity, count in score.rule_violations_count.items():
                total_violations += count
                severity_counts[severity.value] += count

        # 估算真异常和采集异常比例
        true_anomalies = 0
        collection_anomalies = 0

        for score in scores:
            completeness = score.dimensions.get(
                QualityDimension.COMPLETENESS
            ).score if QualityDimension.COMPLETENESS in score.dimensions else 100
            consistency = score.dimensions.get(
                QualityDimension.CONSISTENCY
            ).score if QualityDimension.CONSISTENCY in score.dimensions else 100

            avg_collect = (completeness + consistency) / 2
            total_sensor_violations = sum(score.rule_violations_count.values())

            collection_anomalies += int(total_sensor_violations * (100 - avg_collect) / 100)
            true_anomalies += total_sensor_violations - collection_anomalies

        total_classified = true_anomalies + collection_anomalies
        if total_classified > 0:
            true_ratio = true_anomalies / total_classified
            collection_ratio = collection_anomalies / total_classified
        else:
            true_ratio = 0.0
            collection_ratio = 0.0

        return {
            'total_violations': total_violations,
            'severity_distribution': severity_counts,
            'estimated_true_anomalies': true_anomalies,
            'estimated_collection_anomalies': collection_anomalies,
            'true_anomaly_ratio': true_ratio,
            'collection_anomaly_ratio': collection_ratio,
        }

    def _calculate_quality_trend(
        self,
        engine: Any,
        sensor_ids: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """计算近7天质量趋势"""
        trend = []
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(6, -1, -1):
            date = end_date - timedelta(days=i)

            # 简化处理：使用历史评分的平均值
            daily_scores = []
            if sensor_ids:
                for sensor_id in sensor_ids:
                    history = engine._score_history.get(sensor_id, [])
                    if history:
                        daily_scores.append(history[-1].overall_score)

            if daily_scores:
                avg_score = float(np.mean(daily_scores))
                trend.append({
                    'date': date.isoformat(),
                    'average_score': avg_score,
                    'sensor_count': len(daily_scores),
                })
            else:
                trend.append({
                    'date': date.isoformat(),
                    'average_score': None,
                    'sensor_count': 0,
                })

        return trend

    def _generate_summary(
        self,
        total_sensors: int,
        average_score: float,
        quality_dist: Dict[QualityLevel, int],
        problem_count: int,
        critical_count: int,
    ) -> str:
        """生成报告摘要"""
        level = QualityLevel.from_score(average_score)

        parts = []
        parts.append(
            f"今日共监控 {total_sensors} 个传感器，"
            f"平均质量评分 {average_score:.1f} 分（{level.value}）。"
        )

        # 质量分布
        dist_parts = []
        for lvl in [QualityLevel.EXCELLENT, QualityLevel.GOOD, QualityLevel.FAIR,
                   QualityLevel.POOR, QualityLevel.CRITICAL]:
            count = quality_dist.get(lvl, 0)
            if count > 0:
                dist_parts.append(f"{lvl.value}{count}个")
        if dist_parts:
            parts.append("质量分布：" + "，".join(dist_parts) + "。")

        # 问题和建议
        if problem_count > 0:
            parts.append(
                f"发现问题传感器 {problem_count} 个，"
                f"生成修复建议 {critical_count} 条紧急建议。"
            )
        else:
            parts.append("所有传感器质量良好，无需要处理的问题。")

        # 整体评价
        if average_score >= 90:
            parts.append("整体数据质量优秀，系统运行稳定。")
        elif average_score >= 75:
            parts.append("整体数据质量良好，建议关注少量传感器的轻微问题。")
        elif average_score >= 60:
            parts.append("整体数据质量一般，建议及时处理问题传感器。")
        elif average_score >= 40:
            parts.append("整体数据质量较差，需要立即处理多个传感器问题。")
        else:
            parts.append("整体数据质量极差，建议立即进行全面排查和维护。")

        return "".join(parts)

    def _create_empty_report(self, report_date: datetime) -> DailyQualityReport:
        """创建空报告"""
        return DailyQualityReport(
            report_date=report_date,
            total_sensors=0,
            average_quality_score=0.0,
            quality_distribution={
                QualityLevel.EXCELLENT: 0,
                QualityLevel.GOOD: 0,
                QualityLevel.FAIR: 0,
                QualityLevel.POOR: 0,
                QualityLevel.CRITICAL: 0,
            },
            problem_sensors=[],
            recommendations=[],
            anomaly_statistics={},
            quality_trend=[],
            summary="无可用数据，无法生成质量报告。",
        )

    def _save_report_to_db(self, report: DailyQualityReport) -> bool:
        """保存报告到数据库"""
        try:
            from app.utils.database import get_db
            from sqlalchemy import text

            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，跳过报告保存")
                    return False

                insert_sql = text("""
                    INSERT INTO sc_quality_reports
                    (report_date, total_sensors, average_score, quality_distribution,
                     problem_sensors, recommendations, anomaly_statistics,
                     quality_trend, summary, create_time)
                    VALUES
                    (:report_date, :total_sensors, :average_score, :quality_distribution,
                     :problem_sensors, :recommendations, :anomaly_statistics,
                     :quality_trend, :summary, NOW())
                """)

                db.execute(insert_sql, {
                    'report_date': report.report_date,
                    'total_sensors': report.total_sensors,
                    'average_score': report.average_quality_score,
                    'quality_distribution': str(
                        {k.value: v for k, v in report.quality_distribution.items()}
                    ),
                    'problem_sensors': str([p.to_dict() for p in report.problem_sensors]),
                    'recommendations': str([r.to_dict() for r in report.recommendations]),
                    'anomaly_statistics': str(report.anomaly_statistics),
                    'quality_trend': str(report.quality_trend),
                    'summary': report.summary,
                })

                db.commit()
                logger.info("质量报告已保存到数据库")
                return True

        except Exception as e:
            logger.error(f"保存质量报告失败: {e}")
            return False
