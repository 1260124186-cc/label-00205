"""
数据质量治理平台单元测试

测试数据质量规则引擎、质量评分、数据过滤、异常分类和报告生成功能。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from datetime import datetime, timedelta
import unittest
from typing import List, Tuple

from app.services.data_quality.rules_engine import (
    RulesEngine,
    MissingRateRule,
    DuplicateRule,
    TimeInversionRule,
    OutOfBoundsRule,
    DriftDetectionRule,
    RuleType,
    RuleSeverity,
)
from app.services.data_quality.quality_scoring import (
    QualityScorer,
    QualityLevel,
    QualityDimension,
)
from app.services.data_quality.filtering import (
    DataQualityFilter,
    FilterStrategy,
)
from app.services.data_quality.anomaly_linker import (
    AnomalyLinker,
    AnomalyClassification,
    CollectionAnomalySubtype,
    TrueAnomalySubtype,
)
from app.services.data_quality.report_service import (
    QualityReportService,
    RecommendationPriority,
)
from app.services.data_quality.engine import DataQualityEngine


def generate_test_data(
    n_points: int = 200,
    add_missing: bool = False,
    add_duplicates: bool = False,
    add_time_inversion: bool = False,
    add_outliers: bool = False,
    add_drift: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    """生成测试数据"""
    np.random.seed(42)

    # 基础数据：模拟预紧力数据
    base_value = 500.0
    values = base_value + np.random.normal(0, 20, n_points)

    # 生成时间戳
    start_time = datetime.now() - timedelta(minutes=n_points)
    timestamps = np.array([
        start_time + timedelta(minutes=i) for i in range(n_points)
    ])

    # 添加缺失值
    if add_missing:
        missing_indices = np.random.choice(
            n_points, size=int(n_points * 0.08), replace=False
        )
        values[missing_indices] = np.nan

    # 添加重复值
    if add_duplicates:
        for i in range(5, n_points - 5, 20):
            values[i] = values[i - 1]
            timestamps[i] = timestamps[i - 1]

    # 添加时间倒挂
    if add_time_inversion:
        for i in range(10, n_points - 10, 30):
            timestamps[i] = timestamps[i + 5] - timedelta(minutes=5)

    # 添加异常值（越界）- 使用相对位置避免索引越界
    if add_outliers:
        max_idx = n_points - 1
        outlier_indices = [
            int(n_points * 0.1),
            int(n_points * 0.22),
            int(n_points * 0.4),
            int(n_points * 0.6),
            int(n_points * 0.8),
        ]
        outlier_indices = [min(i, max_idx) for i in outlier_indices]
        values[outlier_indices] = base_value + 200  # 远高于正常范围

    # 添加漂移
    if add_drift:
        # 后半部分数据均值漂移
        drift_size = 50
        half = int(n_points / 2)
        values[half:] += drift_size + np.linspace(0, drift_size, n_points - half)

    return values, timestamps


class TestRulesEngine(unittest.TestCase):
    """测试规则引擎"""

    def setUp(self):
        self.rules_engine = RulesEngine()

    def test_missing_rate_detection(self):
        """测试缺失率检测"""
        values, timestamps = generate_test_data(add_missing=True)

        rule = MissingRateRule()
        score, violation = rule.evaluate(values, timestamps, "test_sensor")

        self.assertIsNotNone(violation)
        self.assertEqual(violation.rule_type, RuleType.MISSING_RATE)
        missing_rate = violation.details.get('missing_rate', 0)
        self.assertGreater(missing_rate, 0.05)
        print(f"✓ 缺失率检测: 缺失率 {missing_rate:.2%}, "
              f"严重程度 {violation.severity.value}, "
              f"质量评分: {score:.1f}")

    def test_duplicate_detection(self):
        """测试重复数据检测"""
        values, timestamps = generate_test_data(add_duplicates=True)

        rule = DuplicateRule()
        score, violation = rule.evaluate(values, timestamps, "test_sensor")

        self.assertIsNotNone(violation)
        self.assertEqual(violation.rule_type, RuleType.DUPLICATE)
        self.assertGreater(len(violation.indices), 0)
        print(f"✓ 重复检测: 发现 {len(violation.indices)} 处重复, "
              f"质量评分: {score:.1f}")

    def test_time_inversion_detection(self):
        """测试时间倒挂检测"""
        values, timestamps = generate_test_data(
            n_points=200,
            add_time_inversion=True,
        )
        # 手动增加更多的时间倒挂点确保能检测到
        invert_count = 15
        for i in range(5, 5 + invert_count * 10, 10):
            if i + 2 < len(timestamps):
                timestamps[i] = timestamps[i + 2] - timedelta(minutes=10)

        rule = TimeInversionRule(threshold=0.03)
        score, violation = rule.evaluate(values, timestamps, "test_sensor")

        self.assertIsNotNone(violation)
        self.assertEqual(violation.rule_type, RuleType.TIME_INVERSION)
        self.assertGreater(len(violation.indices), 0)
        print(f"✓ 时间倒挂检测: 发现 {len(violation.indices)} 处时间倒挂, "
              f"质量评分: {score:.1f}")

    def test_out_of_bounds_detection(self):
        """测试越界检测"""
        values, timestamps = generate_test_data(
            n_points=200,
            add_outliers=True,
        )
        # 手动增加更多的越界点确保能检测到
        outlier_count = 20
        for i in range(10, 10 + outlier_count * 8, 8):
            if i < len(values):
                values[i] = 10000.0  # 极端越界值

        rule = OutOfBoundsRule(threshold=0.05)
        score, violation = rule.evaluate(values, timestamps, "test_sensor")

        self.assertIsNotNone(violation)
        self.assertEqual(violation.rule_type, RuleType.OUT_OF_BOUNDS)
        self.assertGreater(len(violation.indices), 0)
        print(f"✓ 越界检测: 发现 {len(violation.indices)} 个越界值, "
              f"质量评分: {score:.1f}")

    def test_drift_detection(self):
        """测试漂移检测"""
        values, timestamps = generate_test_data(add_drift=True)

        rule = DriftDetectionRule(
            reference_window_size=60,
            test_window_size=30,
            step_size=15,
        )
        score, violation = rule.evaluate(values, timestamps, "test_sensor")

        self.assertIsNotNone(violation)
        self.assertEqual(violation.rule_type, RuleType.DRIFT)
        drift_magnitude = violation.details.get('drift_magnitude', violation.score)
        print(f"✓ 漂移检测: 漂移幅度 {drift_magnitude:.4f}, "
              f"严重程度 {violation.severity.value}, "
              f"质量评分: {score:.1f}")

    def test_full_rules_engine(self):
        """测试完整规则引擎"""
        values, timestamps = generate_test_data(
            add_missing=True,
            add_duplicates=True,
            add_outliers=True,
        )

        result = self.rules_engine.check(
            sensor_id="test_sensor",
            values=values,
            timestamps=timestamps,
        )

        self.assertEqual(result.sensor_id, "test_sensor")
        self.assertGreater(len(result.violations), 0)
        self.assertLess(result.overall_score, 100.0)

        print(f"\n✓ 完整规则引擎测试:")
        print(f"  - 总数据点: {result.total_points}")
        print(f"  - 有效数据点: {result.valid_points}")
        print(f"  - 综合评分: {result.overall_score:.2f}")
        print(f"  - 违规数量: {len(result.violations)}")
        for violation in result.violations:
            print(f"    * {violation.rule_type.value}: {violation.message}")

    def test_clean_data(self):
        """测试干净数据（无违规）"""
        values, timestamps = generate_test_data()

        result = self.rules_engine.check("test_sensor", values, timestamps)

        self.assertEqual(len(result.violations), 0)
        self.assertGreater(result.overall_score, 95.0)
        print(f"\n✓ 干净数据测试: 评分 {result.overall_score:.2f}, 无违规")


class TestQualityScoring(unittest.TestCase):
    """测试质量评分系统"""

    def setUp(self):
        self.rules_engine = RulesEngine()
        self.scorer = QualityScorer()

    def test_quality_scoring_good_data(self):
        """测试良好数据的质量评分"""
        values, timestamps = generate_test_data()
        check_result = self.rules_engine.check("test_sensor", values, timestamps)
        score = self.scorer.score(check_result)

        self.assertEqual(score.sensor_id, "test_sensor")
        self.assertGreater(score.overall_score, 90.0)
        self.assertEqual(score.overall_level, QualityLevel.EXCELLENT)
        self.assertTrue(score.valid_for_training)
        self.assertGreater(score.confidence_adjustment, 0.95)

        print(f"\n✓ 良好数据评分:")
        print(f"  - 综合评分: {score.overall_score:.2f}")
        print(f"  - 质量等级: {score.overall_level.value}")
        print(f"  - 可用于训练: {score.valid_for_training}")
        print(f"  - 置信度调整系数: {score.confidence_adjustment:.3f}")

    def test_quality_scoring_poor_data(self):
        """测试较差数据的质量评分"""
        values, timestamps = generate_test_data(
            n_points=300,
            add_missing=True,
            add_outliers=True,
            add_duplicates=True,
            add_time_inversion=True,
            add_drift=True,
        )
        check_result = self.rules_engine.check("test_sensor", values, timestamps)
        score = self.scorer.score(check_result)

        self.assertLess(score.overall_score, 85.0)
        print(f"\n✓ 较差数据评分:")
        print(f"  - 综合评分: {score.overall_score:.2f}")
        print(f"  - 质量等级: {score.overall_level.value}")
        print(f"  - 可用于训练: {score.valid_for_training}")

        for dim, dim_score in score.dimensions.items():
            print(f"  - {dim.value}: {dim_score.score:.2f}")

    def test_quality_level_thresholds(self):
        """测试质量等级阈值"""
        self.assertEqual(QualityLevel.from_score(95.0), QualityLevel.EXCELLENT)
        self.assertEqual(QualityLevel.from_score(85.0), QualityLevel.GOOD)
        self.assertEqual(QualityLevel.from_score(70.0), QualityLevel.FAIR)
        self.assertEqual(QualityLevel.from_score(50.0), QualityLevel.POOR)
        self.assertEqual(QualityLevel.from_score(30.0), QualityLevel.CRITICAL)
        print("\n✓ 质量等级阈值测试通过")

    def test_quality_summary(self):
        """测试质量汇总"""
        scores = []
        for i in range(5):
            values, timestamps = generate_test_data()
            if i >= 3:
                values, timestamps = generate_test_data(add_missing=True)
            check_result = self.rules_engine.check(f"sensor_{i}", values, timestamps)
            scores.append(self.scorer.score(check_result))

        summary = self.scorer.get_quality_summary(scores)

        self.assertIn('average_score', summary)
        self.assertIn('level_distribution', summary)
        print(f"\n✓ 质量汇总:")
        print(f"  - 平均评分: {summary['average_score']:.2f}")
        print(f"  - 质量分布: {summary['level_distribution']}")
        print(f"  - 问题传感器: {summary['training_eligible_count']} 个合格")


class TestDataFiltering(unittest.TestCase):
    """测试数据过滤功能"""

    def setUp(self):
        self.rules_engine = RulesEngine()
        self.scorer = QualityScorer()
        self.filter = DataQualityFilter()

    def test_filter_for_training(self):
        """测试训练数据过滤"""
        values, timestamps = generate_test_data(
            add_missing=True,
            add_outliers=True,
        )

        check_result = self.rules_engine.check("test_sensor", values, timestamps)
        quality_score = self.scorer.score(check_result)

        filter_result = self.filter.filter_for_training(
            data=values,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
        )

        self.assertIsNotNone(filter_result.filtered_data)
        self.assertLessEqual(
            len(filter_result.filtered_data),
            len(filter_result.original_data)
        )
        self.assertEqual(
            filter_result.filter_strategy,
            FilterStrategy.EXCLUDE
        )

        print(f"\n✓ 训练数据过滤:")
        print(f"  - 原始数据量: {len(filter_result.original_data)}")
        print(f"  - 过滤后数据量: {len(filter_result.filtered_data)}")
        print(f"  - 移除数据点: {len(filter_result.filtered_indices)}")
        print(f"  - 过滤策略: {filter_result.filter_strategy.value}")
        print(f"  - 可用于训练: {filter_result.valid_for_training}")

    def test_filter_for_prediction(self):
        """测试预测数据过滤"""
        values, timestamps = generate_test_data(
            add_missing=True,
            add_duplicates=True,
        )

        check_result = self.rules_engine.check("test_sensor", values, timestamps)
        quality_score = self.scorer.score(check_result)

        filter_result = self.filter.filter_for_prediction(
            data=values,
            timestamps=timestamps,
            check_result=check_result,
            quality_score=quality_score,
        )

        self.assertIsNotNone(filter_result.filtered_data)
        self.assertIn(
            filter_result.filter_strategy,
            list(FilterStrategy)
        )

        print(f"\n✓ 预测数据过滤:")
        print(f"  - 原始数据量: {len(filter_result.original_data)}")
        print(f"  - 过滤后数据量: {len(filter_result.filtered_data)}")
        print(f"  - 置信度乘数: {filter_result.confidence_multiplier:.3f}")

    def test_adjust_prediction_confidence(self):
        """测试预测置信度调整"""
        # 测试良好数据
        values_good, timestamps_good = generate_test_data()
        check_result_good = self.rules_engine.check(
            "good_sensor", values_good, timestamps_good
        )
        score_good = self.scorer.score(check_result_good)
        filter_result_good = self.filter.filter_for_prediction(
            values_good, timestamps_good, check_result_good, score_good
        )

        adjusted_good = self.filter.adjust_prediction_confidence(
            original_confidence=0.9,
            quality_score=score_good,
            filter_result=filter_result_good,
        )

        self.assertGreater(adjusted_good, 0.85)
        self.assertLessEqual(adjusted_good, 0.9)

        # 测试较差数据
        values_poor, timestamps_poor = generate_test_data(
            add_missing=True,
            add_outliers=True,
            add_drift=True,
        )
        check_result_poor = self.rules_engine.check(
            "poor_sensor", values_poor, timestamps_poor
        )
        score_poor = self.scorer.score(check_result_poor)
        filter_result_poor = self.filter.filter_for_prediction(
            values_poor, timestamps_poor, check_result_poor, score_poor
        )

        adjusted_poor = self.filter.adjust_prediction_confidence(
            original_confidence=0.9,
            quality_score=score_poor,
            filter_result=filter_result_poor,
        )

        self.assertLess(adjusted_poor, 0.9)
        self.assertGreaterEqual(adjusted_poor, 0.2)

        print(f"\n✓ 置信度调整:")
        print(f"  - 良好数据: 0.900 → {adjusted_good:.3f}")
        print(f"  - 较差数据: 0.900 → {adjusted_poor:.3f}")
        print(f"  - 质量评分差: {score_good.overall_score:.1f} vs {score_poor.overall_score:.1f}")


class TestAnomalyLinker(unittest.TestCase):
    """测试异常分类功能"""

    def setUp(self):
        self.rules_engine = RulesEngine()
        self.linker = AnomalyLinker()

    def test_classify_collection_anomaly(self):
        """测试采集异常分类"""
        values, timestamps = generate_test_data(
            add_missing=True,
            add_duplicates=True,
        )

        quality_result = self.rules_engine.check(
            "test_sensor", values, timestamps
        )

        anomalies = [
            {
                'id': 1,
                'sensor_id': 'test_sensor',
                'anomaly_value': 600.0,
                'anomaly_type': 'out_of_range',
                'anomaly_score': 0.8,
                'original_time': timestamps[20],
                'details': {},
            }
        ]

        result = self.linker.link_and_classify(
            sensor_id="test_sensor",
            anomalies=anomalies,
            data=values,
            timestamps=timestamps,
            quality_result=quality_result,
        )

        self.assertIsNotNone(result)
        self.assertGreater(result.total_anomalies, 0)

        if result.classified_anomalies:
            classified = result.classified_anomalies[0]
            print(f"\n✓ 异常分类测试:")
            print(f"  - 分类: {classified.classification.value}")
            print(f"  - 置信度: {classified.confidence:.3f}")
            if classified.subtype:
                print(f"  - 子类型: {classified.subtype}")

    def test_classify_true_anomaly(self):
        """测试真异常分类（预紧力突降）"""
        values, timestamps = generate_test_data(n_points=200)

        # 添加真实的预紧力突降
        drop_start = 100
        values[drop_start:] = values[drop_start:] * 0.6  # 突降40%

        quality_result = self.rules_engine.check(
            "test_sensor", values, timestamps
        )

        anomalies = [
            {
                'id': 1,
                'sensor_id': 'test_sensor',
                'anomaly_value': values[drop_start],
                'anomaly_type': 'sudden_change',
                'anomaly_score': 0.95,
                'original_time': timestamps[drop_start],
                'details': {},
            }
        ]

        result = self.linker.link_and_classify(
            sensor_id="test_sensor",
            anomalies=anomalies,
            data=values,
            timestamps=timestamps,
            quality_result=quality_result,
        )

        self.assertIsNotNone(result)
        if result.classified_anomalies:
            classified = result.classified_anomalies[0]
            print(f"\n✓ 真异常分类测试:")
            print(f"  - 分类: {classified.classification.value}")
            print(f"  - 置信度: {classified.confidence:.3f}")
            if classified.subtype:
                print(f"  - 子类型: {classified.subtype}")


class TestQualityReportService(unittest.TestCase):
    """测试质量报告服务"""

    def setUp(self):
        self.engine = DataQualityEngine()
        self.report_service = QualityReportService()

        # 预处理一些传感器数据用于报告生成
        sensor_ids = ['sensor_001', 'sensor_002', 'sensor_003',
                      'sensor_004', 'sensor_005']

        for i, sensor_id in enumerate(sensor_ids):
            if i < 3:
                # 良好数据
                values, timestamps = generate_test_data(n_points=150)
            elif i == 3:
                # 中等问题
                values, timestamps = generate_test_data(
                    n_points=150, add_missing=True, add_outliers=True
                )
            else:
                # 严重问题
                values, timestamps = generate_test_data(
                    n_points=150, add_missing=True, add_duplicates=True,
                    add_outliers=True, add_drift=True
                )

            self.engine.evaluate_sensor_data(
                sensor_id=sensor_id,
                values=values,
                timestamps=timestamps,
                include_anomaly_classification=False,
            )

    def test_generate_daily_report(self):
        """测试生成每日质量报告"""
        report = self.report_service.generate_daily_report(
            engine=self.engine,
            sensor_ids=['sensor_001', 'sensor_002', 'sensor_003',
                        'sensor_004', 'sensor_005'],
            save_to_db=False,
        )

        self.assertIsNotNone(report)
        self.assertEqual(report.total_sensors, 5)
        self.assertGreater(report.average_quality_score, 0.0)
        self.assertLessEqual(report.average_quality_score, 100.0)

        print(f"\n✓ 每日质量报告生成:")
        print(f"  - 报告日期: {report.report_date.date()}")
        print(f"  - 总传感器数: {report.total_sensors}")
        print(f"  - 平均评分: {report.average_quality_score:.1f}")
        print(f"  - 质量分布: {report.quality_distribution}")
        print(f"  - 问题传感器数: {len(report.problem_sensors)}")
        print(f"  - 修复建议数: {len(report.recommendations)}")

        if report.problem_sensors:
            print(f"\n  问题传感器排行:")
            for ps in report.problem_sensors:
                print(f"    #{ps.rank} {ps.sensor_id}: "
                      f"{ps.quality_score:.1f}分 ({ps.quality_level.value}) "
                      f"- 趋势: {ps.trend}")

        if report.recommendations:
            print(f"\n  修复建议:")
            for rec in report.recommendations[:3]:
                print(f"    [{rec.priority.value.upper()}] {rec.sensor_id}: "
                      f"{rec.problem_type} - 预计 {rec.estimated_effort}小时")

        print(f"\n  摘要: {report.summary}")

    def test_problem_sensor_ranking(self):
        """测试问题传感器排行"""
        scores = []
        for i in range(5):
            if i < 2:
                values, timestamps = generate_test_data(n_points=100)
            else:
                values, timestamps = generate_test_data(
                    n_points=100, add_missing=True, add_outliers=True
                )
            check, score = self.engine.evaluate_quality_only(
                f"sensor_{i:03d}", values, timestamps
            )
            scores.append(score)

        problem_sensors = self.report_service._generate_problem_sensor_ranking(
            scores, self.engine
        )

        self.assertIsInstance(problem_sensors, list)
        if problem_sensors:
            # 验证排序（评分升序）
            scores_list = [ps.quality_score for ps in problem_sensors]
            self.assertEqual(scores_list, sorted(scores_list))
            print(f"\n✓ 问题传感器排行: 共 {len(problem_sensors)} 个问题传感器")


class TestDataQualityEngine(unittest.TestCase):
    """测试数据质量引擎（集成测试）"""

    def setUp(self):
        self.engine = DataQualityEngine()

    def test_full_evaluation_pipeline(self):
        """测试完整评估流程"""
        values, timestamps = generate_test_data(
            n_points=200,
            add_missing=True,
            add_outliers=True,
        )

        result = self.engine.evaluate_sensor_data(
            sensor_id="integration_test",
            values=values,
            timestamps=timestamps,
            include_anomaly_classification=False,
        )

        self.assertIn('sensor_id', result)
        self.assertIn('quality_check', result)
        self.assertIn('quality_score', result)
        self.assertIn('filter_result', result)
        self.assertIn('evaluate_time', result)

        qc = result['quality_check']
        qs = result['quality_score']
        fr = result['filter_result']

        print(f"\n✓ 集成测试 - 完整评估流程:")
        print(f"  传感器: {result['sensor_id']}")
        print(f"  质量评分: {qc['overall_score']:.1f} → "
              f"{qs['overall_score']:.1f} ({qs['overall_level']})")
        print(f"  训练准入: {'是' if qs['valid_for_training'] else '否'}")
        print(f"  置信度调整: {qs['confidence_adjustment']:.3f}")
        original_count = len(fr.get('original_data', [])) if fr.get('original_data') is not None else fr.get('original_count', 0)
        filtered_count = len(fr.get('filtered_data', [])) if fr.get('filtered_data') is not None else fr.get('filtered_count', 0)
        print(f"  数据过滤: {original_count} → {filtered_count} "
              f"(移除 {original_count - filtered_count})")
        print(f"  置信度乘数: {fr['confidence_multiplier']:.3f}")

        if qc['violations']:
            print(f"  违规项:")
            for v in qc['violations'][:3]:
                print(f"    * {v.get('rule_type', 'unknown')}: {v.get('severity', 'unknown')}")

    def test_batch_evaluation(self):
        """测试批量评估"""
        sensor_data = {}
        for i in range(3):
            values, timestamps = generate_test_data(n_points=100)
            if i == 2:
                values, timestamps = generate_test_data(
                    n_points=100, add_missing=True
                )
            sensor_data[f"sensor_batch_{i}"] = (values, timestamps)

        results = self.engine.batch_evaluate(sensor_data)

        self.assertEqual(len(results), 3)
        print(f"\n✓ 批量评估: {len(results)} 个传感器")

        for sensor_id, result in results.items():
            if 'error' in result:
                print(f"  {sensor_id}: 错误 - {result['error']}")
            else:
                score = result['quality_score']['overall_score']
                level = result['quality_score']['overall_level']
                print(f"  {sensor_id}: {score:.1f}分 ({level})")

    def test_get_problem_sensors(self):
        """测试获取问题传感器列表"""
        # 添加一些传感器数据
        for i in range(5):
            if i < 2:
                values, timestamps = generate_test_data(n_points=80)
            else:
                values, timestamps = generate_test_data(
                    n_points=80, add_missing=True, add_outliers=True
                )
            self.engine.evaluate_quality_only(
                f"sensor_prob_{i}", values, timestamps
            )

        problem_sensors = self.engine.get_problem_sensors(
            sensor_ids=[f"sensor_prob_{i}" for i in range(5)],
            min_score=80.0,
        )

        self.assertIsInstance(problem_sensors, list)
        print(f"\n✓ 问题传感器列表: {len(problem_sensors)} 个 < 80分")
        for ps in problem_sensors:
            print(f"  {ps['sensor_id']}: {ps['score']:.1f}分 - {ps['level']}")

    def test_adjust_confidence(self):
        """测试置信度调整"""
        # 良好数据
        values_good, ts_good = generate_test_data(n_points=100)
        adj_good = self.engine.adjust_prediction_confidence(
            "sensor_good", 0.95, values_good, ts_good
        )

        # 较差数据
        values_poor, ts_poor = generate_test_data(
            n_points=100, add_missing=True, add_outliers=True, add_drift=True
        )
        adj_poor = self.engine.adjust_prediction_confidence(
            "sensor_poor", 0.95, values_poor, ts_poor
        )

        self.assertGreater(adj_good, 0.9)
        self.assertLess(adj_poor, 0.95)

        print(f"\n✓ 置信度调整:")
        print(f"  原始: 0.950")
        print(f"  良好数据: {adj_good:.3f}")
        print(f"  较差数据: {adj_poor:.3f}")


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("数据质量治理平台 - 单元测试")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestRulesEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestQualityScoring))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestAnomalyLinker))
    suite.addTests(loader.loadTestsFromTestCase(TestQualityReportService))
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityEngine))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    if result.failures:
        print("\n失败详情:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.splitlines()[-1]}")

    if result.errors:
        print("\n错误详情:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.splitlines()[-1]}")

    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 存在测试失败，请检查代码")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
