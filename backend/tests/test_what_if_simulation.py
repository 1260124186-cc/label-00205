"""
What-if 情景仿真引擎单元测试

测试内容:
1. TestRiskScoreCalibration - 风险评分口径校准（核心修复验证）
   - HI → risk_score 映射公式正确性（1-10分，与BayesianRiskModel一致）
   - 风险等级划分正确性（高/中/低，中文）
   - 与现有 /risk/assess 接口的口径一致性验证
   - 边界值测试

2. TestWhatIfSimulatorCore - 仿真引擎核心功能测试
   - 历史数据解析
   - 劣化模型拟合（linear/exponential/polynomial）
   - 轨迹构建
   - 首次触阈计算
   - 风险等级时间线
   - 干预推荐

3. TestScenarioSimulation - 情景仿真功能测试
   - 斜率调整
   - 阶跃变化
   - 噪声注入
   - 环境场景（温度/湿度/振动）
   - 维护策略（正常/延迟）

4. TestScenarioComparison - 批量情景对比测试
   - 多情景对比指标
   - 综合评分排名
   - 与基线差值计算

5. TestEdgeCases - 边界条件与异常处理测试
   - 极少历史数据点
   - 已低于阈值的历史数据
   - 极端参数输入
   - 无效历史数据
"""

import pytest
import sys
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


DEFAULT_THRESHOLDS = {
    "failure_threshold": 30.0,
    "warning_threshold": 50.0,
    "intervention_threshold": 60.0,
    "excellent_threshold": 90.0,
    "good_threshold": 70.0,
    "fair_threshold": 50.0,
    "poor_threshold": 30.0,
}


class TestRiskScoreCalibration:
    """
    风险评分口径校准测试（核心修复验证）

    与 BayesianRiskModel (/risk/assess) 口径对齐:
    - risk_score 范围: 1-10 分，越高越安全
    - 等级划分:
        - 高风险 ("高"): score ≤ 3
        - 中风险 ("中"): 3 < score ≤ 7
        - 低风险 ("低"): score > 7
    - 映射公式: risk_score = 1 + HI * 0.09
    """

    def test_hi_to_risk_score_mapping_formula(self):
        """测试 HI → risk_score 映射公式正确性

        映射公式: risk_score = 1 + HI * 0.09
        """
        from app.services.what_if_simulation import WhatIfSimulator

        test_cases = [
            (100.0, 10.0),
            (90.0, 9.1),
            (80.0, 8.2),
            (70.0, 7.3),
            (60.0, 6.4),
            (50.0, 5.5),
            (40.0, 4.6),
            (30.0, 3.7),
            (20.0, 2.8),
            (10.0, 1.9),
            (0.0, 1.0),
        ]

        for hi, expected_score in test_cases:
            score = WhatIfSimulator._hi_to_risk_score(hi, DEFAULT_THRESHOLDS)
            assert abs(score - expected_score) < 0.001, (
                f"HI={hi}: expected score={expected_score}, got {score}"
            )

    def test_risk_score_range_clipping(self):
        """测试风险评分范围裁剪（必须在 1-10 之间）"""
        from app.services.what_if_simulation import WhatIfSimulator

        score_high = WhatIfSimulator._hi_to_risk_score(120.0, DEFAULT_THRESHOLDS)
        assert score_high == 10.0, f"HI=120 should clip to 10.0, got {score_high}"

        score_low = WhatIfSimulator._hi_to_risk_score(-10.0, DEFAULT_THRESHOLDS)
        assert score_low == 1.0, f"HI=-10 should clip to 1.0, got {score_low}"

    def test_risk_score_to_level_mapping(self):
        """测试风险评分 → 等级映射正确性

        等级划分（与BayesianRiskModel完全一致）:
        - 高风险 ("高"): score ≤ 3
        - 中风险 ("中"): 3 < score ≤ 7
        - 低风险 ("低"): score > 7
        """
        from app.services.what_if_simulation import WhatIfSimulator

        test_cases = [
            (1.0, "高"),
            (2.5, "高"),
            (3.0, "高"),
            (3.1, "中"),
            (5.0, "中"),
            (7.0, "中"),
            (7.1, "低"),
            (8.5, "低"),
            (10.0, "低"),
        ]

        for score, expected_level in test_cases:
            level = WhatIfSimulator._risk_score_to_level(score)
            assert level == expected_level, (
                f"score={score}: expected level='{expected_level}', got '{level}'"
            )

    def test_risk_level_uses_chinese_characters(self):
        """测试风险等级使用中文（与BayesianRiskModel一致）"""
        from app.services.what_if_simulation import WhatIfSimulator

        for score in [1.0, 5.0, 9.0]:
            level = WhatIfSimulator._risk_score_to_level(score)
            assert level in {"高", "中", "低"}, (
                f"Risk level should be Chinese, got '{level}'"
            )
            assert level not in {"low", "medium", "high", "critical"}, (
                f"Risk level should not be English, got '{level}'"
            )

    def test_end_to_end_trajectory_risk_scores(self):
        """测试端到端仿真轨迹中的风险评分口径正确"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 85.0],
            ["2024-01-05", 84.0],
            ["2024-01-10", 83.0],
            ["2024-01-15", 82.0],
            ["2024-01-20", 81.0],
            ["2024-01-25", 80.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "degradation_model": "linear",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试情景",
                "hypothesis": {},
                "forecast_days": 30,
                "seed": 42,
            }],
        }

        result = sim.run_simulation(request)

        trajectory = result["scenarios"][0]["trajectory"]
        for point in trajectory:
            risk_score = point["risk_score"]
            risk_level = point["risk_level"]

            assert 1.0 <= risk_score <= 10.0, (
                f"risk_score must be 1-10, got {risk_score}"
            )
            assert risk_level in {"高", "中", "低"}, (
                f"risk_level must be 高/中/低, got {risk_level}"
            )

            hi = point["predicted_hi"]
            expected_score = np.clip(1.0 + hi * 0.09, 1.0, 10.0)
            assert abs(risk_score - expected_score) < 0.01, (
                f"HI={hi}: expected risk_score≈{expected_score:.2f}, got {risk_score}"
            )

    def test_consistency_with_bayesian_risk_model_levels(self):
        """测试与 BayesianRiskModel 等级划分一致性

        BayesianRiskModel:
        - score ≤ 3 → RiskLevel.HIGH ("高")
        - 3 < score ≤ 7 → RiskLevel.MEDIUM ("中")
        - score > 7 → RiskLevel.LOW ("低")
        """
        from app.services.what_if_simulation import WhatIfSimulator
        from app.models.risk_model import RiskLevel as BayesRiskLevel

        test_scores = [1.0, 2.0, 3.0, 3.1, 5.0, 7.0, 7.1, 9.0, 10.0]

        for score in test_scores:
            whatif_level = WhatIfSimulator._risk_score_to_level(score)

            if score <= 3:
                bayes_level = BayesRiskLevel.HIGH.value
            elif score <= 7:
                bayes_level = BayesRiskLevel.MEDIUM.value
            else:
                bayes_level = BayesRiskLevel.LOW.value

            assert whatif_level == bayes_level, (
                f"score={score}: WhatIf='{whatif_level}' != Bayesian='{bayes_level}'"
            )

    def test_current_risk_in_response(self):
        """测试响应中 current_risk_score 和 current_risk_level 口径正确"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 70.0],
            ["2024-01-10", 68.0],
            ["2024-01-20", 66.0],
            ["2024-02-01", 64.0],
            ["2024-02-10", 62.0],
            ["2024-02-20", 60.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 10,
            }],
        }

        result = sim.run_simulation(request)

        assert result["current_hi"] == 60.0
        expected_risk_score = 1.0 + 60.0 * 0.09
        assert abs(result["current_risk_score"] - expected_risk_score) < 0.01

        expected_level = WhatIfSimulator._risk_score_to_level(expected_risk_score)
        assert result["current_risk_level"] == expected_level

    def test_high_risk_days_calculation(self):
        """测试高风险天数计算（使用中文"高"判断）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 30.0],
            ["2024-01-10", 28.0],
            ["2024-01-20", 25.0],
            ["2024-02-01", 22.0],
            ["2024-02-10", 20.0],
            ["2024-02-20", 18.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "高风险测试",
                "hypothesis": {"slope_adjustment": 1.5},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)
        summary = result["scenarios"][0]["summary"]
        high_risk_days = summary["high_risk_days"]

        trajectory = result["scenarios"][0]["trajectory"]
        manual_high_risk = sum(1 for p in trajectory if p["risk_level"] == "高")

        assert high_risk_days == manual_high_risk, (
            f"high_risk_days mismatch: {high_risk_days} != {manual_high_risk}"
        )

    def test_total_risk_exposure_calculation(self):
        """测试总风险暴露量计算（Σ(11 - risk_score)，越高越危险）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 80.0],
            ["2024-01-10", 79.0],
            ["2024-01-20", 78.0],
            ["2024-02-01", 77.0],
            ["2024-02-10", 76.0],
            ["2024-02-20", 75.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 10,
            }],
        }

        result = sim.run_simulation(request)
        summary = result["scenarios"][0]["summary"]
        total_risk = summary["total_risk_exposure"]

        trajectory = result["scenarios"][0]["trajectory"]
        manual_total = sum(11.0 - p["risk_score"] for p in trajectory)

        assert abs(total_risk - manual_total) < 0.01, (
            f"total_risk_exposure mismatch: {total_risk} != {manual_total}"
        )

    def test_risk_score_higher_is_safer(self):
        """验证风险评分越高越安全（与BayesianRiskModel一致）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()

        safe_history = [
            ["2024-01-01", 95.0], ["2024-01-10", 94.0], ["2024-01-20", 93.0],
            ["2024-02-01", 92.0], ["2024-02-10", 91.0], ["2024-02-20", 90.0],
        ]

        risky_history = [
            ["2024-01-01", 40.0], ["2024-01-10", 38.0], ["2024-01-20", 36.0],
            ["2024-02-01", 34.0], ["2024-02-10", 32.0], ["2024-02-20", 30.0],
        ]

        request_safe = {
            "node_id": "bolt_safe",
            "node_type": "bolt",
            "history_sequence": safe_history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "s1",
                "scenario_name": "安全情景",
                "hypothesis": {},
                "forecast_days": 10,
            }],
        }

        request_risky = {
            "node_id": "bolt_risky",
            "node_type": "bolt",
            "history_sequence": risky_history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "s1",
                "scenario_name": "危险情景",
                "hypothesis": {},
                "forecast_days": 10,
            }],
        }

        result_safe = sim.run_simulation(request_safe)
        result_risky = sim.run_simulation(request_risky)

        assert result_safe["current_risk_score"] > result_risky["current_risk_score"], (
            "Safe scenario should have higher risk_score (more safe)"
        )

        safe_summary = result_safe["scenarios"][0]["summary"]
        risky_summary = result_risky["scenarios"][0]["summary"]
        assert safe_summary["total_risk_exposure"] < risky_summary["total_risk_exposure"], (
            "Safe scenario should have lower total_risk_exposure"
        )

    def test_risk_score_10_to_100_conversion_formula(self):
        """验证 1-10 ↔ 0-100 双向转换公式正确性"""
        from app.services.what_if_simulation import WhatIfSimulator

        test_cases = [
            (10.0, 0.0),
            (7.0, 33.3333),
            (5.5, 50.0),
            (3.0, 77.7778),
            (1.0, 100.0),
        ]

        for score_10, expected_100 in test_cases:
            actual_100 = WhatIfSimulator._risk_score_10_to_100(score_10)
            assert abs(actual_100 - expected_100) < 0.01, (
                f"10→100: score_10={score_10}, expected {expected_100}, got {actual_100}"
            )

            roundtrip = WhatIfSimulator._risk_score_100_to_10(actual_100)
            assert abs(roundtrip - score_10) < 0.01, (
                f"100→10 roundtrip: score_10={score_10}, got {roundtrip}"
            )

    def test_risk_score_100_range_clipping(self):
        """验证 0-100 分范围裁剪"""
        from app.services.what_if_simulation import WhatIfSimulator

        assert WhatIfSimulator._risk_score_10_to_100(11.0) == 0.0
        assert WhatIfSimulator._risk_score_10_to_100(0.0) == 100.0
        assert WhatIfSimulator._risk_score_100_to_10(110.0) == 1.0
        assert WhatIfSimulator._risk_score_100_to_10(-10.0) == 10.0

    def test_risk_level_to_status_mapping(self):
        """验证中文等级 → 英文状态映射正确性"""
        from app.services.what_if_simulation import WhatIfSimulator

        assert WhatIfSimulator._risk_level_to_status("低") == "normal"
        assert WhatIfSimulator._risk_level_to_status("中") == "warning"
        assert WhatIfSimulator._risk_level_to_status("高") == "critical"

    def test_risk_status_to_level_mapping(self):
        """验证英文状态 → 中文等级映射正确性"""
        from app.services.what_if_simulation import WhatIfSimulator

        assert WhatIfSimulator._risk_status_to_level("normal") == "低"
        assert WhatIfSimulator._risk_status_to_level("warning") == "中"
        assert WhatIfSimulator._risk_status_to_level("critical") == "高"

    def test_risk_score_100_to_status_thresholds(self):
        """验证 0-100 分 → normal/warning/critical 阈值划分（与retest_service完全一致）"""
        from app.services.what_if_simulation import WhatIfSimulator

        assert WhatIfSimulator._risk_score_100_to_status(39.9) == "normal"
        assert WhatIfSimulator._risk_score_100_to_status(40.0) == "warning"
        assert WhatIfSimulator._risk_score_100_to_status(69.9) == "warning"
        assert WhatIfSimulator._risk_score_100_to_status(70.0) == "critical"
        assert WhatIfSimulator._risk_score_100_to_status(100.0) == "critical"

    def test_dual_system_consistency_end_to_end(self):
        """端到端验证：轨迹中每个点的两套体系完全一致"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 95.0], ["2024-01-10", 85.0], ["2024-01-20", 75.0],
            ["2024-02-01", 65.0], ["2024-02-10", 55.0], ["2024-02-20", 45.0],
        ]
        request = {
            "node_id": "bolt_dual",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "s1",
                "scenario_name": "dual_test",
                "hypothesis": {},
                "forecast_days": 10,
            }],
        }
        result = sim.run_simulation(request)

        for point in result["scenarios"][0]["trajectory"]:
            rs10 = point["risk_score"]
            rs100 = point["risk_score_100"]
            rl = point["risk_level"]
            rs = point["risk_status"]

            assert abs(WhatIfSimulator._risk_score_10_to_100(rs10) - rs100) < 0.1, (
                f"Point {point['day_offset']}: risk_score={rs10}→{rs100} mismatch"
            )
            assert WhatIfSimulator._risk_level_to_status(rl) == rs, (
                f"Point {point['day_offset']}: risk_level={rl}→{rs} mismatch"
            )

    def test_dual_system_current_state(self):
        """验证当前状态的双口径字段都存在且一致"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 60.0], ["2024-01-10", 60.0], ["2024-01-20", 60.0],
            ["2024-02-01", 60.0], ["2024-02-10", 60.0], ["2024-02-20", 60.0],
        ]
        request = {
            "node_id": "bolt_curr",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "s1",
                "scenario_name": "current_test",
                "hypothesis": {},
                "forecast_days": 5,
            }],
        }
        result = sim.run_simulation(request)

        assert "current_risk_score" in result
        assert "current_risk_score_100" in result
        assert "current_risk_level" in result
        assert "current_risk_status" in result

        rs10 = result["current_risk_score"]
        rs100 = result["current_risk_score_100"]
        rl = result["current_risk_level"]
        rs = result["current_risk_status"]

        assert abs(WhatIfSimulator._risk_score_10_to_100(rs10) - rs100) < 0.1
        assert WhatIfSimulator._risk_level_to_status(rl) == rs

    def test_dual_system_summary_metrics(self):
        """验证情景汇总的双口径统计指标"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 80.0], ["2024-01-10", 78.0], ["2024-01-20", 76.0],
            ["2024-02-01", 74.0], ["2024-02-10", 72.0], ["2024-02-20", 70.0],
        ]
        request = {
            "node_id": "bolt_sum",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "s1",
                "scenario_name": "summary_test",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }
        result = sim.run_simulation(request)
        summary = result["scenarios"][0]["summary"]
        trajectory = result["scenarios"][0]["trajectory"]

        assert "total_risk_exposure_100" in summary
        assert "critical_days" in summary
        assert "warning_days" in summary

        expected_total_100 = round(sum(p["risk_score_100"] for p in trajectory), 2)
        assert summary["total_risk_exposure_100"] == expected_total_100

        expected_critical = sum(1 for p in trajectory if p["risk_status"] == "critical")
        assert summary["critical_days"] == expected_critical

        expected_warning = sum(1 for p in trajectory if p["risk_status"] == "warning")
        assert summary["warning_days"] == expected_warning

    def test_dual_system_risk_timeline(self):
        """验证风险等级时间线包含双口径字段"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 80.0], ["2024-01-20", 70.0],
            ["2024-02-01", 60.0], ["2024-02-10", 50.0], ["2024-02-20", 40.0],
        ]
        request = {
            "node_id": "bolt_tl",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "s1",
                "scenario_name": "timeline_test",
                "hypothesis": {},
                "forecast_days": 15,
            }],
        }
        result = sim.run_simulation(request)
        timeline = result["scenarios"][0]["risk_timeline"]

        assert len(timeline) > 0
        for item in timeline:
            assert "risk_level" in item
            assert "risk_status" in item
            assert WhatIfSimulator._risk_level_to_status(item["risk_level"]) == item["risk_status"]

    def test_consistency_with_retest_service_thresholds(self):
        """验证与 retest_service._risk_to_status 阈值完全一致"""
        from app.services.what_if_simulation import WhatIfSimulator
        from app.services.alert.retest_service import RetestService

        rs = RetestService()

        test_scores = [0.0, 39.9, 40.0, 55.0, 69.9, 70.0, 85.0, 100.0]
        for score_100 in test_scores:
            sim_status = WhatIfSimulator._risk_score_100_to_status(score_100)
            retest_status = rs._risk_to_status(score_100)
            assert sim_status == retest_status, (
                f"score_100={score_100}: sim={sim_status} vs retest={retest_status}"
            )


class TestWhatIfSimulatorCore:
    """仿真引擎核心功能测试"""

    def test_simulator_instantiation(self):
        """测试仿真引擎实例化"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        assert sim is not None
        assert hasattr(sim, "run_simulation")

    def test_hi_to_level_mapping(self):
        """测试 HI → 健康等级映射"""
        from app.services.what_if_simulation import WhatIfSimulator

        test_cases = [
            (95.0, "excellent"),
            (90.0, "excellent"),
            (80.0, "good"),
            (70.0, "good"),
            (60.0, "fair"),
            (50.0, "fair"),
            (40.0, "poor"),
            (30.0, "poor"),
            (20.0, "critical"),
            (0.0, "critical"),
        ]

        for hi, expected_level in test_cases:
            level = WhatIfSimulator._hi_to_level(hi, DEFAULT_THRESHOLDS)
            assert level == expected_level, (
                f"HI={hi}: expected '{expected_level}', got '{level}'"
            )

    def test_timestamp_parsing(self):
        """测试多种时间戳格式解析"""
        from app.services.what_if_simulation import WhatIfSimulator

        test_cases = [
            ("2024-01-15", datetime(2024, 1, 15)),
            ("20240115", datetime(2024, 1, 15)),
            ("2024-01-15 14:30:00", datetime(2024, 1, 15, 14, 30, 0)),
            ("20240115 14:30:00", datetime(2024, 1, 15, 14, 30, 0)),
            ("2024/01/15 14:30:00", datetime(2024, 1, 15, 14, 30, 0)),
            ("2024-01-15T14:30:00", datetime(2024, 1, 15, 14, 30, 0)),
        ]

        for ts_str, expected in test_cases:
            result = WhatIfSimulator._parse_timestamp(ts_str)
            assert result == expected, f"'{ts_str}': expected {expected}, got {result}"

    def test_preload_to_hi_conversion(self):
        """测试预紧力 → HI 转换"""
        from app.services.what_if_simulation import WhatIfSimulator

        nominal = 600.0

        test_cases = [
            (600.0, 100.0),
            (610.0, 100.0),
            (590.0, 100.0),
            (631.0, 79.33),
            (569.0, 79.33),
            (661.0, 59.5),
            (539.0, 59.5),
            (721.0, 29.67),
            (479.0, 29.67),
        ]

        for preload, expected_hi in test_cases:
            hi = WhatIfSimulator._preload_to_hi(np.array([preload]), nominal)
            assert abs(hi[0] - expected_hi) < 0.01, (
                f"preload={preload}: expected HI={expected_hi}, got {hi[0]}"
            )

    def test_basic_simulation_run(self):
        """测试基本仿真运行"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0],
            ["2024-01-05", 89.0],
            ["2024-01-10", 88.0],
            ["2024-01-15", 87.0],
            ["2024-01-20", 86.0],
            ["2024-01-25", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "degradation_model": "linear",
            "thresholds": DEFAULT_THRESHOLDS,
            "scenarios": [{
                "scenario_id": "baseline",
                "scenario_name": "基线情景",
                "hypothesis": {},
                "forecast_days": 90,
                "seed": 42,
            }],
        }

        result = sim.run_simulation(request)

        assert result["node_id"] == "bolt_001"
        assert result["node_type"] == "bolt"
        assert len(result["scenarios"]) == 1

        scen = result["scenarios"][0]
        assert scen["scenario_id"] == "baseline"
        assert "trajectory" in scen
        assert "first_crossings" in scen
        assert "risk_timeline" in scen
        assert "recommended_interventions" in scen
        assert "summary" in scen

        assert len(scen["trajectory"]) == len(history) + 90

    def test_model_fitting_linear(self):
        """测试线性模型拟合"""
        from app.services.what_if_simulation import WhatIfSimulator, ParsedHistory

        sim = WhatIfSimulator()

        dates = [datetime(2024, 1, 1) + timedelta(days=i * 5) for i in range(10)]
        day_offsets = np.arange(0, 50, 5, dtype=np.float64)
        hi_values = 90.0 - 0.2 * day_offsets

        parsed = ParsedHistory(
            dates=dates,
            day_offsets=day_offsets,
            hi_values=hi_values,
            base_date=dates[-1],
            current_hi=float(hi_values[-1]),
        )

        model = sim._select_and_fit_model(parsed, "linear")

        assert model.model_type == "linear"
        assert abs(model.params["slope"] - (-0.2)) < 0.01
        assert abs(model.params["intercept"] - 90.0) < 0.5

    def test_model_selection_auto(self):
        """测试自动模型选择（选R²最优）"""
        from app.services.what_if_simulation import WhatIfSimulator, ParsedHistory

        sim = WhatIfSimulator()

        dates = [datetime(2024, 1, 1) + timedelta(days=i * 3) for i in range(15)]
        day_offsets = np.arange(0, 45, 3, dtype=np.float64)
        hi_values = 95.0 - 0.01 * day_offsets ** 2

        parsed = ParsedHistory(
            dates=dates,
            day_offsets=day_offsets,
            hi_values=hi_values,
            base_date=dates[-1],
            current_hi=float(hi_values[-1]),
        )

        model = sim._select_and_fit_model(parsed, None)

        assert model.model_type in {"linear", "exponential", "polynomial"}
        assert model.r_squared is not None
        assert model.r_squared > 0.8

    def test_first_crossings_calculation(self):
        """测试首次触阈计算"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = []
        base_date = datetime(2024, 1, 1)
        for i in range(10):
            hi = 85.0 - i * 2.0
            history.append([(base_date + timedelta(days=i)).strftime("%Y-%m-%d"), hi])

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "degradation_model": "linear",
            "thresholds": DEFAULT_THRESHOLDS,
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {"slope_adjustment": 2.0},
                "forecast_days": 60,
            }],
        }

        result = sim.run_simulation(request)
        crossings = result["scenarios"][0]["first_crossings"]

        for thr_name in ["intervention", "warning", "failure"]:
            assert thr_name in crossings
            c = crossings[thr_name]
            assert "crossing_date" in c
            assert "crossing_day_offset" in c
            assert "threshold_value" in c
            assert "confidence" in c
            assert "was_already_below" in c

    def test_was_already_below_detection(self):
        """测试已低于阈值的检测"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 25.0],
            ["2024-01-10", 24.0],
            ["2024-01-20", 23.0],
            ["2024-02-01", 22.0],
            ["2024-02-10", 21.0],
            ["2024-02-20", 20.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)
        crossings = result["scenarios"][0]["first_crossings"]

        assert crossings["failure"]["was_already_below"] is True
        assert crossings["warning"]["was_already_below"] is True
        assert crossings["intervention"]["was_already_below"] is True


class TestScenarioSimulation:
    """情景仿真功能测试"""

    def test_slope_adjustment(self):
        """测试斜率调整参数效果"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "degradation_model": "linear",
            "scenarios": [
                {
                    "scenario_id": "normal",
                    "scenario_name": "正常劣化",
                    "hypothesis": {"slope_adjustment": 1.0},
                    "forecast_days": 100,
                    "seed": 42,
                },
                {
                    "scenario_id": "accelerated",
                    "scenario_name": "加速劣化",
                    "hypothesis": {"slope_adjustment": 2.0},
                    "forecast_days": 100,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        scen_normal = result["scenarios"][0]
        scen_accel = result["scenarios"][1]

        traj_normal = scen_normal["trajectory"]
        traj_accel = scen_accel["trajectory"]

        last_idx = -1
        hi_normal = traj_normal[last_idx]["predicted_hi"]
        hi_accel = traj_accel[last_idx]["predicted_hi"]

        assert hi_accel < hi_normal, (
            f"加速劣化情景期末HI应更低: {hi_accel} < {hi_normal}"
        )

    def test_step_changes(self):
        """测试阶跃变化参数效果"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.5], ["2024-01-20", 89.0],
            ["2024-02-01", 88.5], ["2024-02-10", 88.0], ["2024-02-20", 87.5],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [
                {
                    "scenario_id": "no_step",
                    "scenario_name": "无阶跃",
                    "hypothesis": {"step_changes": []},
                    "forecast_days": 30,
                    "seed": 42,
                },
                {
                    "scenario_id": "with_step",
                    "scenario_name": "有阶跃",
                    "hypothesis": {
                        "step_changes": [{"day_offset": 10, "hi_delta": -15.0}]
                    },
                    "forecast_days": 30,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        scen_no_step = result["scenarios"][0]
        scen_step = result["scenarios"][1]

        future_no_step = [p for p in scen_no_step["trajectory"] if p["day_offset"] >= 10]
        future_step = [p for p in scen_step["trajectory"] if p["day_offset"] >= 10]

        for p1, p2 in zip(future_no_step, future_step):
            assert abs(p2["predicted_hi"] - (p1["predicted_hi"] - 15.0)) < 2.0, (
                f"Day {p1['day_offset']}: expected step of ~15, "
                f"got {p1['predicted_hi']} → {p2['predicted_hi']}"
            )

    def test_noise_level(self):
        """测试噪声水平参数效果"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 90.0], ["2024-01-20", 90.0],
            ["2024-02-01", 90.0], ["2024-02-10", 90.0], ["2024-02-20", 90.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [
                {
                    "scenario_id": "no_noise",
                    "scenario_name": "无噪声",
                    "hypothesis": {"noise_level": 0.0},
                    "forecast_days": 30,
                    "seed": 42,
                },
                {
                    "scenario_id": "high_noise",
                    "scenario_name": "高噪声",
                    "hypothesis": {"noise_level": 10.0},
                    "forecast_days": 30,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        traj_no_noise = [p["predicted_hi"] for p in result["scenarios"][0]["trajectory"] if p["is_prediction"]]
        traj_high_noise = [p["predicted_hi"] for p in result["scenarios"][1]["trajectory"] if p["is_prediction"]]

        std_no_noise = np.std(traj_no_noise)
        std_high_noise = np.std(traj_high_noise)

        assert std_high_noise > std_no_noise, (
            f"高噪声情景应有更高的标准差: {std_high_noise} > {std_no_noise}"
        )

    def test_temperature_scenario(self):
        """测试温度场景参数效果"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.5], ["2024-01-20", 89.0],
            ["2024-02-01", 88.5], ["2024-02-10", 88.0], ["2024-02-20", 87.5],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [
                {
                    "scenario_id": "normal_temp",
                    "scenario_name": "常温",
                    "hypothesis": {"temperature_scenario": "normal"},
                    "forecast_days": 60,
                    "seed": 42,
                },
                {
                    "scenario_id": "high_temp",
                    "scenario_name": "高温",
                    "hypothesis": {"temperature_scenario": "high"},
                    "forecast_days": 60,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        scen_normal = result["scenarios"][0]
        scen_high = result["scenarios"][1]

        hi_normal = scen_normal["trajectory"][-1]["predicted_hi"]
        hi_high = scen_high["trajectory"][-1]["predicted_hi"]

        assert hi_high < hi_normal, (
            f"高温情景HI应更低: {hi_high} < {hi_normal}"
        )

    def test_maintenance_strategy(self):
        """测试维护策略（正常维护 vs 延迟维护）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = []
        for i in range(20):
            hi = 85.0 - i * 1.0
            history.append([
                (datetime(2024, 1, 1) + timedelta(days=i * 5)).strftime("%Y-%m-%d"),
                hi,
            ])

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "thresholds": DEFAULT_THRESHOLDS,
            "scenarios": [
                {
                    "scenario_id": "normal_maint",
                    "scenario_name": "正常维护",
                    "hypothesis": {
                        "maintenance_delay_days": 0,
                        "maintenance_recovery_hi": 20.0,
                    },
                    "forecast_days": 120,
                    "seed": 42,
                },
                {
                    "scenario_id": "delayed_maint",
                    "scenario_name": "延迟维护",
                    "hypothesis": {
                        "maintenance_delay_days": 30,
                        "maintenance_recovery_hi": 15.0,
                    },
                    "forecast_days": 120,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        assert len(result["scenarios"]) == 2

        scen_normal = result["scenarios"][0]
        scen_delayed = result["scenarios"][1]

        summ_normal = scen_normal["summary"]
        summ_delayed = scen_delayed["summary"]

        assert summ_normal["maintenance_count"] >= 0
        assert summ_delayed["maintenance_count"] >= 0
        assert summ_normal["final_hi"] >= summ_delayed["final_hi"]

    def test_preload_history_type(self):
        """测试预紧力类型的历史数据输入"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history_preload = [
            ["2024-01-01", 600.0],
            ["2024-01-10", 590.0],
            ["2024-01-20", 580.0],
            ["2024-02-01", 570.0],
            ["2024-02-10", 560.0],
            ["2024-02-20", 550.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history_preload,
            "history_type": "preload",
            "nominal_preload": 600.0,
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试预紧力",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)

        assert result["current_hi"] > 0
        assert result["current_hi"] <= 100

        trajectory = result["scenarios"][0]["trajectory"]
        for point in trajectory:
            assert 0 <= point["predicted_hi"] <= 100


class TestScenarioComparison:
    """批量情景对比测试"""

    def test_multi_scenario_comparison(self):
        """测试多情景对比功能"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [
                {
                    "scenario_id": "baseline",
                    "scenario_name": "基线",
                    "hypothesis": {},
                    "forecast_days": 90,
                    "seed": 42,
                },
                {
                    "scenario_id": "conservative",
                    "scenario_name": "保守维护",
                    "hypothesis": {"slope_adjustment": 0.8, "maintenance_recovery_hi": 25.0},
                    "forecast_days": 90,
                    "seed": 42,
                },
                {
                    "scenario_id": "aggressive",
                    "scenario_name": "激进延迟",
                    "hypothesis": {"slope_adjustment": 1.5, "maintenance_delay_days": 60},
                    "forecast_days": 90,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)

        assert result["comparison"] is not None
        comp = result["comparison"]

        assert comp["baseline_scenario_id"] == "baseline"
        assert len(comp["comparison_metrics"]) == 9
        assert len(comp["ranked_scenarios"]) == 3

        for metric in comp["comparison_metrics"]:
            assert "metric_code" in metric
            assert "metric_name" in metric
            assert "scenario_values" in metric
            assert "best_scenario_id" in metric
            assert "delta_vs_baseline" in metric

        ranks = [r["rank"] for r in comp["ranked_scenarios"]]
        assert ranks == [1, 2, 3]

        assert "recommendation_summary" in comp
        assert len(comp["recommendation_summary"]) > 0

    def test_delta_vs_baseline_calculation(self):
        """测试与基线差值计算"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [
                {
                    "scenario_id": "baseline",
                    "scenario_name": "基线",
                    "hypothesis": {},
                    "forecast_days": 90,
                    "seed": 42,
                },
                {
                    "scenario_id": "worse",
                    "scenario_name": "更差",
                    "hypothesis": {"slope_adjustment": 2.0},
                    "forecast_days": 90,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        comp = result["comparison"]

        summ_baseline = result["scenarios"][0]["summary"]
        summ_worse = result["scenarios"][1]["summary"]

        for metric in comp["comparison_metrics"]:
            if metric["metric_code"] == "final_hi":
                delta = metric["delta_vs_baseline"]["worse"]
                expected_delta = summ_worse["final_hi"] - summ_baseline["final_hi"]
                assert abs(delta - expected_delta) < 0.01

    def test_best_scenario_selection(self):
        """测试最优情景选择逻辑"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [
                {
                    "scenario_id": "s1",
                    "scenario_name": "快速劣化",
                    "hypothesis": {"slope_adjustment": 3.0},
                    "forecast_days": 90,
                    "seed": 42,
                },
                {
                    "scenario_id": "s2",
                    "scenario_name": "慢速劣化",
                    "hypothesis": {"slope_adjustment": 0.5},
                    "forecast_days": 90,
                    "seed": 42,
                },
            ],
        }

        result = sim.run_simulation(request)
        comp = result["comparison"]

        for metric in comp["comparison_metrics"]:
            if metric["metric_code"] == "final_hi":
                assert metric["best_scenario_id"] == "s2"
            elif metric["metric_code"] == "total_risk":
                assert metric["best_scenario_id"] == "s2"


class TestEdgeCases:
    """边界条件与异常处理测试"""

    def test_minimal_history_points(self):
        """测试极少历史数据点（<5个）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0],
            ["2024-01-10", 89.0],
            ["2024-01-20", 88.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)

        assert result["data_quality_note"] is not None
        assert "数据点较少" in result["data_quality_note"]

    def test_empty_history_raises_error(self):
        """测试空历史数据应抛出错误"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": [],
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        with pytest.raises(ValueError, match="历史数据为空或解析失败"):
            sim.run_simulation(request)

    def test_invalid_history_data(self):
        """测试无效历史数据（非数字）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", "invalid"],
            ["2024-01-10", None],
            ["2024-01-20", "abc"],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        with pytest.raises(ValueError, match="历史数据为空或解析失败"):
            sim.run_simulation(request)

    def test_partially_invalid_history(self):
        """测试部分无效历史数据（部分有效）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0],
            ["2024-01-05", "invalid"],
            ["2024-01-10", 89.0],
            ["2024-01-15", None],
            ["2024-01-20", 88.0],
            ["2024-01-25", "bad"],
            ["2024-02-01", 87.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)

        assert len(result["scenarios"][0]["trajectory"]) >= 4 + 30

    def test_very_short_forecast(self):
        """测试极短预测期（1天）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 1,
            }],
        }

        result = sim.run_simulation(request)
        trajectory = result["scenarios"][0]["trajectory"]

        assert len(trajectory) == 6 + 1

    def test_zero_forecast_days(self):
        """测试零预测天数（仅历史拟合）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 0,
            }],
        }

        result = sim.run_simulation(request)
        trajectory = result["scenarios"][0]["trajectory"]

        assert len(trajectory) == 6
        for point in trajectory:
            assert point["is_prediction"] is False

    def test_hi_bounds_clamping(self):
        """测试HI值边界裁剪（0-100）"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 100.0], ["2024-01-10", 99.0], ["2024-01-20", 98.0],
            ["2024-02-01", 97.0], ["2024-02-10", 96.0], ["2024-02-20", 95.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {
                    "step_changes": [{"day_offset": 1, "hi_delta": 20.0}]
                },
                "forecast_days": 10,
            }],
        }

        result = sim.run_simulation(request)
        trajectory = result["scenarios"][0]["trajectory"]

        for point in trajectory:
            assert 0 <= point["predicted_hi"] <= 100, (
                f"HI超出范围: {point['predicted_hi']}"
            )
            assert 0 <= point["lower_bound"] <= 100
            assert 0 <= point["upper_bound"] <= 100

    def test_unix_timestamp_history(self):
        """测试Unix时间戳格式的历史数据"""
        from app.services.what_if_simulation import WhatIfSimulator
        import time

        sim = WhatIfSimulator()
        base_ts = int(time.mktime(datetime(2024, 1, 1).timetuple()))

        history = [
            [base_ts, 90.0],
            [base_ts + 86400 * 10, 89.0],
            [base_ts + 86400 * 20, 88.0],
            [base_ts + 86400 * 30, 87.0],
            [base_ts + 86400 * 40, 86.0],
            [base_ts + 86400 * 50, 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 10,
            }],
        }

        result = sim.run_simulation(request)
        assert result["base_date"] is not None
        assert len(result["scenarios"][0]["trajectory"]) == 6 + 10

    def test_single_scenario_no_comparison(self):
        """测试单情景时不生成对比分析"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "bolt_001",
            "node_type": "bolt",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "single",
                "scenario_name": "单情景",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)
        assert result["comparison"] is None

    def test_flange_node_type(self):
        """测试法兰节点类型"""
        from app.services.what_if_simulation import WhatIfSimulator

        sim = WhatIfSimulator()
        history = [
            ["2024-01-01", 90.0], ["2024-01-10", 89.0], ["2024-01-20", 88.0],
            ["2024-02-01", 87.0], ["2024-02-10", 86.0], ["2024-02-20", 85.0],
        ]

        request = {
            "node_id": "flange_001",
            "node_type": "flange",
            "history_sequence": history,
            "history_type": "hi",
            "scenarios": [{
                "scenario_id": "test",
                "scenario_name": "测试",
                "hypothesis": {},
                "forecast_days": 30,
            }],
        }

        result = sim.run_simulation(request)

        assert result["node_id"] == "flange_001"
        assert result["node_type"] == "flange"
        assert len(result["scenarios"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
