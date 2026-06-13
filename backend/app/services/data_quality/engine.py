"""
数据质量引擎核心模块

整合所有数据质量治理组件，提供统一的入口接口。

主要功能:
1. evaluate_sensor_data: 评估传感器数据质量
2. filter_training_data: 过滤训练数据
3. classify_anomalies: 分类异常数据
4. generate_daily_report: 生成每日质量报告
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from loguru import logger

from app.services.data_quality.rules_engine import (
    RulesEngine,
    QualityCheckResult,
)
from app.services.data_quality.quality_scoring import (
    QualityScorer,
    SensorQualityScore,
)
from app.services.data_quality.filtering import (
    DataQualityFilter,
    FilteredDataResult,
)
from app.services.data_quality.anomaly_linker import (
    AnomalyLinker,
    AnomalyLinkResult,
    ClassifiedAnomaly,
)
from app.services.data_quality.report_service import (
    QualityReportService,
    DailyQualityReport,
)


class DataQualityEngine:
    """
    数据质量引擎

    整合所有数据质量治理组件，提供统一的入口。
    """

    def __init__(
        self,
        rules_engine: Optional[RulesEngine] = None,
        quality_scorer: Optional[QualityScorer] = None,
        data_filter: Optional[DataQualityFilter] = None,
        anomaly_linker: Optional[AnomalyLinker] = None,
        report_service: Optional[QualityReportService] = None,
    ):
        """
        初始化数据质量引擎

        Args:
            rules_engine: 规则引擎
            quality_scorer: 质量评分器
            data_filter: 数据过滤器
            anomaly_linker: 异常联动器
            report_service: 报告服务
        """
        self.rules_engine = rules_engine or RulesEngine()
        self.quality_scorer = quality_scorer or QualityScorer()
        self.data_filter = data_filter or DataQualityFilter()
        self.anomaly_linker = anomaly_linker or AnomalyLinker()
        self.report_service = report_service or QualityReportService()

        # 历史评分缓存
        self._score_history: Dict[str, List[SensorQualityScore]] = {}

        logger.info("数据质量引擎初始化完成")

    def evaluate_sensor_data(
        self,
        sensor_id: str,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        data_age_minutes: Optional[float] = None,
        include_anomaly_classification: bool = True,
    ) -> Dict[str, Any]:
        """
        评估传感器数据质量（完整流程）

        Args:
            sensor_id: 传感器ID
            values: 数据值数组
            timestamps: 时间戳数组
            data_age_minutes: 数据新鲜度（分钟）
            include_anomaly_classification: 是否包含异常分类

        Returns:
            Dict[str, Any]: 包含质量检查、评分、过滤结果的完整评估
        """
        logger.info(f"开始评估传感器数据质量: {sensor_id}, 数据点数: {len(values)}")

        # Step 1: 质量规则检查
        check_result = self.rules_engine.check(
            sensor_id=sensor_id,
            values=values,
            timestamps=timestamps,
        )

        # Step 2: 质量评分
        historical_scores = self._score_history.get(sensor_id, [])
        quality_score = self.quality_scorer.score(
            check_result=check_result,
            historical_scores=historical_scores,
            data_age_minutes=data_age_minutes,
        )

        # 保存历史评分
        if sensor_id not in self._score_history:
            self._score_history[sensor_id] = []
        self._score_history[sensor_id].append(quality_score)
        if len(self._score_history[sensor_id]) > 30:
            self._score_history[sensor_id] = self._score_history[sensor_id][-30:]

        # Step 3: 数据过滤（用于预测）
        filter_result = self.data_filter.filter_for_prediction(
            data=values,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
        )

        # Step 4: 异常分类（可选）
        anomaly_result = None
        if include_anomaly_classification:
            anomalies = self.anomaly_linker.fetch_anomalies_from_db(
                sensor_id=sensor_id,
                limit=100,
            )
            if anomalies:
                anomaly_result = self.anomaly_linker.link_and_classify(
                    sensor_id=sensor_id,
                    anomalies=anomalies,
                    data=values,
                    timestamps=timestamps,
                    quality_result=check_result,
                )

        result = {
            'sensor_id': sensor_id,
            'quality_check': check_result.to_dict(),
            'quality_score': quality_score.to_dict(),
            'filter_result': filter_result.to_dict(),
            'anomaly_classification': anomaly_result.to_dict() if anomaly_result else None,
            'evaluate_time': datetime.now().isoformat(),
        }

        logger.info(
            f"传感器 {sensor_id} 质量评估完成: "
            f"综合评分 {quality_score.overall_score:.1f}, "
            f"等级 {quality_score.overall_level.value}"
        )

        return result

    def evaluate_quality_only(
        self,
        sensor_id: str,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        data_age_minutes: Optional[float] = None,
    ) -> Tuple[QualityCheckResult, SensorQualityScore]:
        """
        仅评估质量（轻量版本）

        Args:
            sensor_id: 传感器ID
            values: 数据值数组
            timestamps: 时间戳数组
            data_age_minutes: 数据新鲜度（分钟）

        Returns:
            Tuple[QualityCheckResult, SensorQualityScore]: 质量检查结果和评分
        """
        check_result = self.rules_engine.check(sensor_id, values, timestamps)
        historical_scores = self._score_history.get(sensor_id, [])
        quality_score = self.quality_scorer.score(
            check_result=check_result,
            historical_scores=historical_scores,
            data_age_minutes=data_age_minutes,
        )
        return check_result, quality_score

    def filter_training_data(
        self,
        sensor_id: str,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
    ) -> FilteredDataResult:
        """
        过滤训练数据

        Args:
            sensor_id: 传感器ID
            values: 数据值数组
            timestamps: 时间戳数组

        Returns:
            FilteredDataResult: 过滤结果
        """
        check_result = self.rules_engine.check(sensor_id, values, timestamps)
        historical_scores = self._score_history.get(sensor_id, [])
        quality_score = self.quality_scorer.score(check_result, historical_scores)

        return self.data_filter.filter_for_training(
            data=values,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
        )

    def filter_prediction_data(
        self,
        sensor_id: str,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
    ) -> FilteredDataResult:
        """
        过滤预测数据

        Args:
            sensor_id: 传感器ID
            values: 数据值数组
            timestamps: 时间戳数组

        Returns:
            FilteredDataResult: 过滤结果
        """
        check_result = self.rules_engine.check(sensor_id, values, timestamps)
        historical_scores = self._score_history.get(sensor_id, [])
        quality_score = self.quality_scorer.score(check_result, historical_scores)

        return self.data_filter.filter_for_prediction(
            data=values,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
        )

    def classify_sensor_anomalies(
        self,
        sensor_id: str,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Optional[AnomalyLinkResult]:
        """
        分类传感器异常

        Args:
            sensor_id: 传感器ID
            data: 数据数组
            timestamps: 时间戳数组
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            Optional[AnomalyLinkResult]: 异常分类结果
        """
        anomalies = self.anomaly_linker.fetch_anomalies_from_db(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time,
        )

        if not anomalies:
            logger.info(f"传感器 {sensor_id} 没有找到异常数据")
            return None

        check_result = self.rules_engine.check(sensor_id, data, timestamps)

        return self.anomaly_linker.link_and_classify(
            sensor_id=sensor_id,
            anomalies=anomalies,
            data=data,
            timestamps=timestamps,
            quality_result=check_result,
        )

    def generate_daily_report(
        self,
        report_date: Optional[datetime] = None,
        sensor_ids: Optional[List[str]] = None,
        save_to_db: bool = True,
    ) -> DailyQualityReport:
        """
        生成每日质量报告

        Args:
            report_date: 报告日期
            sensor_ids: 传感器ID列表，None则处理所有
            save_to_db: 是否保存到数据库

        Returns:
            DailyQualityReport: 每日质量报告
        """
        return self.report_service.generate_daily_report(
            engine=self,
            report_date=report_date,
            sensor_ids=sensor_ids,
            save_to_db=save_to_db,
        )

    def adjust_prediction_confidence(
        self,
        sensor_id: str,
        original_confidence: float,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
    ) -> float:
        """
        调整预测置信度

        Args:
            sensor_id: 传感器ID
            original_confidence: 原始置信度
            values: 数据值数组
            timestamps: 时间戳数组

        Returns:
            float: 调整后的置信度
        """
        check_result, quality_score = self.evaluate_quality_only(
            sensor_id=sensor_id,
            values=values,
            timestamps=timestamps,
        )

        filter_result = self.data_filter.filter_for_prediction(
            data=values,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
        )

        return self.data_filter.adjust_prediction_confidence(
            original_confidence=original_confidence,
            quality_score=quality_score,
            filter_result=filter_result,
        )

    def get_sensor_quality_summary(
        self,
        sensor_ids: List[str],
    ) -> Dict[str, Any]:
        """
        获取多个传感器的质量汇总

        Args:
            sensor_ids: 传感器ID列表

        Returns:
            Dict[str, Any]: 质量汇总
        """
        scores = []
        for sensor_id in sensor_ids:
            if sensor_id in self._score_history and self._score_history[sensor_id]:
                scores.append(self._score_history[sensor_id][-1])

        return self.quality_scorer.get_quality_summary(scores)

    def batch_evaluate(
        self,
        sensor_data: Dict[str, Tuple[np.ndarray, Optional[np.ndarray]]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量评估多个传感器

        Args:
            sensor_data: 传感器数据字典 {sensor_id: (values, timestamps)}

        Returns:
            Dict[str, Dict[str, Any]]: 各传感器评估结果
        """
        results = {}
        for sensor_id, (values, timestamps) in sensor_data.items():
            try:
                results[sensor_id] = self.evaluate_sensor_data(
                    sensor_id=sensor_id,
                    values=values,
                    timestamps=timestamps,
                    include_anomaly_classification=False,
                )
            except Exception as e:
                logger.error(f"批量评估传感器 {sensor_id} 失败: {e}")
                results[sensor_id] = {'error': str(e)}

        return results

    def get_problem_sensors(
        self,
        sensor_ids: List[str],
        min_score: float = 60.0,
    ) -> List[Dict[str, Any]]:
        """
        获取问题传感器列表

        Args:
            sensor_ids: 传感器ID列表
            min_score: 最低评分阈值

        Returns:
            List[Dict[str, Any]]: 问题传感器列表，按评分升序排列
        """
        problem_sensors = []

        for sensor_id in sensor_ids:
            if sensor_id in self._score_history and self._score_history[sensor_id]:
                latest_score = self._score_history[sensor_id][-1]
                if latest_score.overall_score < min_score:
                    problem_sensors.append({
                        'sensor_id': sensor_id,
                        'score': latest_score.overall_score,
                        'level': latest_score.overall_level.value,
                        'valid_for_training': latest_score.valid_for_training,
                        'confidence_adjustment': latest_score.confidence_adjustment,
                    })

        problem_sensors.sort(key=lambda x: x['score'])
        return problem_sensors
