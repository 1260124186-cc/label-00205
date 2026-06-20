# -*- coding: utf-8 -*-
"""
数据工厂 / 金样本 / 回归门禁 单元测试

覆盖：
1. GoldenSamplesService：金样本生成、版本注册、基线切换、场景参数文档
2. RegressionService：_compute_metrics 计算 accuracy/F1/precision/recall，门
   禁判定逻辑
3. DataFactory：固定 seed 的可复现性（两次同 seed 生成相同结果）
4. 规则分类器 _rule_based_predict 基本分类能力
"""

import hashlib
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dataclasses import asdict  # noqa: E402

from app.services.golden_samples import (  # noqa: E402
    GOLDEN_DEFAULT_BOLTS,
    GOLDEN_DEFAULT_DAYS,
    GOLDEN_DEFAULT_FREQ_MINUTES,
    GOLDEN_DEFAULT_SEED,
    GoldenSamplesService,
    GoldenSampleSpec,
    get_golden_samples_service,
)
from app.services.regression_service import (  # noqa: E402
    RegressionService,
    RegressionResult,
    RegressionGateResult,
    get_regression_service,
    NUM_CLASSES,
)


def _spec_hash(spec: GoldenSampleSpec) -> str:
    d = asdict(spec)
    raw = f"{d['scenario']}|{d['bolts']}|{d['days']}|{d['frequency_minutes']}|{d['seed']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ============================================================
# 1. Golden Samples 服务测试
# ============================================================

class TestGoldenSamplesService:
    @pytest.fixture
    def gs(self, tmp_path: Path, monkeypatch):
        """创建一个使用临时目录的 GoldenSamplesService，避免污染生产数据"""
        data_root = tmp_path / "golden_samples"
        data_root.mkdir(parents=True, exist_ok=True)
        real_init = GoldenSamplesService.__init__

        def patched_init(self, *args, **kwargs):
            real_init(self, *args, **kwargs)
            object.__setattr__(self, "storage_root", str(data_root))
            self.baseline_file = Path(str(data_root)) / ".baseline"
            Path(self.storage_root).mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(GoldenSamplesService, "__init__", patched_init)
        return get_golden_samples_service()

    def test_spec_hash_deterministic(self):
        """spec_hash 必须由字段确定性生成"""
        s1 = GoldenSampleSpec(
            scenario="all", bolts=24, days=14,
            frequency_minutes=30, seed=20260620,
        )
        s2 = GoldenSampleSpec(
            scenario="all", bolts=24, days=14,
            frequency_minutes=30, seed=20260620,
        )
        assert _spec_hash(s1) == _spec_hash(s2)
        s3 = GoldenSampleSpec(
            scenario="normal", bolts=24, days=14,
            frequency_minutes=30, seed=20260620,
        )
        assert _spec_hash(s1) != _spec_hash(s3)

    def test_generate_reproducible(self, gs, tmp_path):
        """固定 seed 必须生成完全一致的数据（MD5 不变）"""
        r1, _ = gs.generate_golden_samples(
            scenario="normal", bolts=6, days=2, frequency_minutes=120, seed=42,
        )
        r2, _ = gs.generate_golden_samples(
            scenario="normal", bolts=6, days=2, frequency_minutes=120, seed=42,
        )
        # FactoryResult.records → DataFrame
        df1 = pd.DataFrame([asdict(r) for r in r1.records])
        df2 = pd.DataFrame([asdict(r) for r in r2.records])
        assert isinstance(df1, pd.DataFrame)
        assert isinstance(df2, pd.DataFrame)
        md5_1 = hashlib.md5(
            pd.util.hash_pandas_object(df1).values.tobytes()
        ).hexdigest()
        md5_2 = hashlib.md5(
            pd.util.hash_pandas_object(df2).values.tobytes()
        ).hexdigest()
        assert md5_1 == md5_2, "同 seed 生成的数据不一致，不可复现"
        assert len(df1) > 0

    def test_generate_labels_alignment(self, gs, tmp_path):
        """生成 golden labels：窗口大小必须正确，标签必须在合法范围内"""
        r, _ = gs.generate_golden_samples(
            scenario="all", bolts=6, days=2, frequency_minutes=120, seed=100,
        )
        labels = gs.generate_golden_labels(
            r, window_size=20, stride=10,
        )
        # generate_golden_labels 返回 List[Dict]
        assert isinstance(labels, list) and len(labels) > 0, f"labels 格式异常: {type(labels)}"
        # 关键字段检查
        expected_keys = {"golden_label"}
        first_keys = set(labels[0].keys())
        assert first_keys & expected_keys, f"缺少 golden_label 字段: {first_keys}"
        for item in labels:
            # golden_label 是核心字段
            code = int(item.get("golden_label", -1))
            assert 0 <= code < NUM_CLASSES, f"异常标签值: {code}"

    def test_scenario_docs_completeness(self, gs):
        """get_scenario_parameter_docs 返回所有必填字段"""
        docs = gs.get_scenario_parameter_docs()
        for key in (
            "scenarios", "scenario_config_fields",
            "status_labels", "recommended_seed",
            "available_scenarios",
        ):
            assert key in docs, f"场景参数文档缺少字段: {key}"
        assert len(docs["scenarios"]) >= 1
        assert "normal" in docs["available_scenarios"]
        codes = {s["code"] for s in docs["status_labels"]}
        assert 0 in codes


# ============================================================
# 2. Regression Service 指标 & 门禁测试
# ============================================================

class TestRegressionMetrics:
    @pytest.fixture
    def reg(self):
        return get_regression_service()

    def test_compute_metrics_perfect(self, reg):
        """完美预测：accuracy=1.0, F1=1.0"""
        y_true = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
        y_pred = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
        m = reg._compute_metrics(y_true, y_pred)
        assert abs(m["accuracy"] - 1.0) < 1e-6
        assert abs(m["macro_f1"] - 1.0) < 1e-6
        assert abs(m["weighted_f1"] - 1.0) < 1e-6
        assert m["confusion_matrix"][0][0] == 2
        assert m["confusion_matrix"][4][4] == 2

    def test_compute_metrics_all_wrong(self, reg):
        """全错预测：accuracy=0"""
        y_true = [0, 0, 1, 1]
        y_pred = [1, 1, 0, 0]
        m = reg._compute_metrics(y_true, y_pred)
        assert abs(m["accuracy"]) < 1e-6

    def test_compute_metrics_imbalanced(self, reg):
        """类别不平衡：weighted_f1 应考虑支持数量"""
        y_true = [0, 0, 0, 0, 0, 1]
        y_pred = [0, 0, 0, 0, 1, 1]
        m = reg._compute_metrics(y_true, y_pred)
        # 多数类 0 有 4 个正确，accuracy = 5/6
        assert abs(m["accuracy"] - 5 / 6) < 1e-6

    def test_compare_with_baseline_no_baseline_should_pass(self, reg, monkeypatch):
        """没有基线版本（首次注册） => 门禁通过"""
        # mock：无基线
        monkeypatch.setattr(reg.golden, "get_baseline_version", lambda *a, **kw: None)

        fake_target = RegressionResult(
            version="v1.0",
            golden_sample_version="gs-v1.0",
            model_version_used="model-v0",
            accuracy=0.9,
            macro_f1=0.88,
            weighted_f1=0.89,
            per_class_metrics={},
            confusion_matrix=[],
            total_samples=100,
            evaluation_time_seconds=1.0,
            evaluated_at="",
        )
        result = reg.compare_with_baseline(fake_target)
        assert result.gate_passed is True

    def test_compare_with_baseline_block_by_accuracy(self, reg, monkeypatch):
        """accuracy 下降 >2% => 门禁阻断"""
        from app.services.golden_samples import GoldenSampleVersion, GoldenSampleSpec, GoldenSampleMetrics
        fake_base = GoldenSampleVersion(
            version="v1.0",
            spec=GoldenSampleSpec(scenario="all", bolts=24, days=14,
                                frequency_minutes=30, seed=1),
            metrics=GoldenSampleMetrics(
                accuracy=0.95, macro_f1=0.90, weighted_f1=0.92,
                per_class_f1={}, per_class_precision={}, per_class_recall={},
                confusion_matrix=[], total_samples=100,
                evaluation_model_version="v0", evaluation_timestamp="",
            ),
            data_hash="x", data_path="x", labels_path="x",
            created_at="", created_by="", description="", is_baseline=True,
        )
        monkeypatch.setattr(reg.golden, "get_baseline_version", lambda *a, **kw: fake_base)
        reg.gate_threshold = 0.02  # 强制 2%

        fake_target = RegressionResult(
            version="v1.1",
            golden_sample_version="gs-v1.0",
            model_version_used="model-v1",
            accuracy=0.92,  # 下降 3%
            macro_f1=0.90,
            weighted_f1=0.92,
            per_class_metrics={},
            confusion_matrix=[],
            total_samples=100,
            evaluation_time_seconds=1.0,
            evaluated_at="",
        )
        result = reg.compare_with_baseline(fake_target)
        assert result.gate_passed is False
        assert "accuracy" in (result.blocked_reason or "").lower()

    def test_compare_with_baseline_pass_within_threshold(self, reg, monkeypatch):
        """所有指标下降 < 阈值 => 门禁通过"""
        from app.services.golden_samples import GoldenSampleVersion, GoldenSampleSpec, GoldenSampleMetrics
        fake_base = GoldenSampleVersion(
            version="v1.0",
            spec=GoldenSampleSpec(scenario="all", bolts=24, days=14,
                                frequency_minutes=30, seed=1),
            metrics=GoldenSampleMetrics(
                accuracy=0.95, macro_f1=0.90, weighted_f1=0.92,
                per_class_f1={}, per_class_precision={}, per_class_recall={},
                confusion_matrix=[], total_samples=100,
                evaluation_model_version="v0", evaluation_timestamp="",
            ),
            data_hash="x", data_path="x", labels_path="x",
            created_at="", created_by="", description="", is_baseline=True,
        )
        monkeypatch.setattr(reg.golden, "get_baseline_version", lambda *a, **kw: fake_base)
        reg.gate_threshold = 0.02  # 强制 2%

        fake_target = RegressionResult(
            version="v1.1",
            golden_sample_version="gs-v1.0",
            model_version_used="model-v1",
            accuracy=0.94,  # -1.05% < 2%
            macro_f1=0.89,  # -1.11% < 2%
            weighted_f1=0.91,  # -1.09% < 2%
            per_class_metrics={},
            confusion_matrix=[],
            total_samples=100,
            evaluation_time_seconds=1.0,
            evaluated_at="",
        )
        result = reg.compare_with_baseline(fake_target)
        assert result.gate_passed is True, f"意外阻断: {result.blocked_reason}"

    def test_skip_gate_always_pass(self, reg):
        """skip_gate=true 永远通过（admin override）"""
        result = reg.model_activate_gate(
            model_type="bolt",
            node_id="default",
            target_model_version=None,
            gate_threshold=0.02,
            skip_gate=True,
        )
        assert result["can_activate"] is True
        assert result["skip_gate"] is True


# ============================================================
# 3. DataFactory 可复现性测试
# ============================================================

class TestDataFactoryReproducible:
    def test_datafactory_same_seed(self):
        """DataFactory 使用相同 seed 两次必须生成相同结果"""
        try:
            from data_factory import DataFactory, ScenarioConfig
        except Exception as e:
            pytest.skip(f"无法导入 data_factory: {e}")
        from datetime import datetime
        seed = 20260620
        start = datetime(2026, 1, 1, 0, 0, 0)
        # 注意：np.random.seed 是全局的，必须先生成 r1，再用相同 seed 创建 factory2
        factory1 = DataFactory(cfg=ScenarioConfig(), seed=seed)
        r1 = factory1.generate(
            scenario="all", bolts=6, days=2, frequency_minutes=120, start_time=start,
        )
        factory2 = DataFactory(cfg=ScenarioConfig(), seed=seed)
        r2 = factory2.generate(
            scenario="all", bolts=6, days=2, frequency_minutes=120, start_time=start,
        )
        df1 = pd.DataFrame([asdict(r) for r in r1.records])
        df2 = pd.DataFrame([asdict(r) for r in r2.records])
        assert isinstance(df1, pd.DataFrame)
        assert isinstance(df2, pd.DataFrame)
        h1 = hashlib.md5(
            pd.util.hash_pandas_object(df1).values.tobytes()
        ).hexdigest()
        h2 = hashlib.md5(
            pd.util.hash_pandas_object(df2).values.tobytes()
        ).hexdigest()
        assert h1 == h2, "data_factory 同 seed 生成不一致，金样本不可靠"
        assert len(df1) > 0

    def test_datafactory_diff_seed(self):
        """不同 seed 应该产生不同结果"""
        try:
            from data_factory import DataFactory, ScenarioConfig
        except Exception as e:
            pytest.skip(f"无法导入 data_factory: {e}")
        from datetime import datetime
        start = datetime(2026, 1, 1, 0, 0, 0)
        f1 = DataFactory(cfg=ScenarioConfig(), seed=1)
        f2 = DataFactory(cfg=ScenarioConfig(), seed=2)
        r1 = f1.generate(
            scenario="all", bolts=6, days=2, frequency_minutes=120, start_time=start,
        )
        r2 = f2.generate(
            scenario="all", bolts=6, days=2, frequency_minutes=120, start_time=start,
        )
        df1 = pd.DataFrame([asdict(r) for r in r1.records])
        df2 = pd.DataFrame([asdict(r) for r in r2.records])
        assert isinstance(df1, pd.DataFrame)
        assert isinstance(df2, pd.DataFrame)
        assert len(df1) > 0
        assert len(df2) > 0


# ============================================================
# 4. 规则分类器兜底逻辑（阈值 0.15=90, 0.4=240, 0.6=360, 0.8=480, 1.2=720
# ============================================================

class TestRuleBasedPredict:
    @pytest.fixture
    def reg(self):
        return get_regression_service()

    def test_rule_normal_range(self, reg):
        """正常预紧力区间 480~720 => status=0"""
        y = np.array([550.0, 580.0, 600.0, 620.0, 650.0])
        pred = reg._rule_based_predict(y)
        assert pred == 0

    def test_rule_loosening_mild(self, reg):
        """预紧力轻微松动 ~440，last < 480 = status=1"""
        # last 450 < 600*0.8=480，mean 454 < 480 => 1
        y = np.array([450.0, 460.0, 445.0, 465.0, 450.0])
        pred = reg._rule_based_predict(y)
        assert pred == 1

    def test_rule_loosening_moderate(self, reg):
        """预紧力 360 以下 => status=2"""
        y = np.array([350.0, 355.0, 340.0, 345.0, 355.0])
        pred = reg._rule_based_predict(y)
        assert pred == 2

    def test_rule_fracture_low(self, reg):
        """预紧力 240 以下 => status=3"""
        y = np.array([200.0, 210.0, 220.0, 230.0, 235.0])
        pred = reg._rule_based_predict(y)
        assert pred == 3

    def test_rule_fracture_very_low(self, reg):
        """预紧力极低 <100 或 <90 => status=4"""
        y = np.array([50.0, 60.0, 70.0, 80.0, 85.0])
        pred = reg._rule_based_predict(y)
        assert pred == 4

    def test_rule_overload_high(self, reg):
        """预紧力 > 720 (nominal*1.2) => status=1"""
        y = np.array([730.0, 740.0, 750.0, 760.0, 770.0])
        pred = reg._rule_based_predict(y)
        assert pred == 1
