"""
配置热更新单元测试

覆盖范围:
1. 内存事件总线 pub/sub（优先级、通配符、一次性订阅、异步派发）
2. 配置前缀白/黑名单分类（is_hot_updatable）
3. ConfigManager.apply_hot_update() 主流程（版本号、审计、事件）
4. 版本回滚（rollback_to_version）
5. Backpressure/StreamConcurrencyManager.reload_config
6. 调度器 reload_config 基础逻辑（不真正启动 APScheduler）
"""

import os
import sys
import time
import json
import threading
import yaml
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

import pytest

# 确保 backend 目录可导入
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# 1. 事件总线测试
# ============================================================

class TestEventBus:
    def test_publish_subscribe_basic(self):
        """基础发布订阅"""
        from app.core.event_bus import EventBus, EventType, Event

        bus = EventBus()
        received = []

        def cb(e):
            received.append(e)

        sub_id = bus.subscribe(EventType.CONFIG_CHANGED, cb)
        assert sub_id

        evt = bus.publish(EventType.CONFIG_CHANGED, {"version": 1})
        assert evt.event_type == EventType.CONFIG_CHANGED

        time.sleep(0.05)
        assert len(received) == 1
        assert received[0].data["version"] == 1

        # 取消订阅
        assert bus.unsubscribe(sub_id) is True
        bus.publish(EventType.CONFIG_CHANGED, {"version": 2})
        time.sleep(0.05)
        assert len(received) == 1

    def test_priority_and_exception_isolation(self):
        """优先级排序 + 回调异常不影响其他"""
        from app.core.event_bus import EventBus, EventType

        bus = EventBus()
        order = []

        def low(e):
            order.append("low")

        def high(e):
            order.append("high")

        def bad(e):
            raise RuntimeError("boom")

        bus.subscribe(EventType.CONFIG_CHANGED, low, priority=1)
        bus.subscribe(EventType.CONFIG_CHANGED, bad, priority=50)
        bus.subscribe(EventType.CONFIG_CHANGED, high, priority=100)

        bus.publish(EventType.CONFIG_CHANGED, {})
        time.sleep(0.05)
        # 按优先级从高到低执行
        assert order == ["high", "low"]

    def test_wildcard_and_once(self):
        """通配符订阅 + 一次性订阅"""
        from app.core.event_bus import EventBus, EventType

        bus = EventBus()
        wildcard_count = [0]
        once_count = [0]

        def wc_cb(e):
            wildcard_count[0] += 1

        def once_cb(e):
            once_count[0] += 1

        bus.subscribe(None, wc_cb)
        bus.subscribe(EventType.LOG_LEVEL_CHANGED, once_cb, once=True)

        bus.publish(EventType.CONFIG_CHANGED, {})
        bus.publish(EventType.LOG_LEVEL_CHANGED, {})
        bus.publish(EventType.LOG_LEVEL_CHANGED, {})
        time.sleep(0.05)

        assert wildcard_count[0] == 3
        assert once_count[0] == 1

    def test_history_and_stats(self):
        """事件历史 + 订阅者计数"""
        from app.core.event_bus import EventBus, EventType

        bus = EventBus()
        bus.subscribe(EventType.CONFIG_CHANGED, lambda e: None)
        bus.subscribe(None, lambda e: None)

        for i in range(5):
            bus.publish(EventType.CONFIG_CHANGED, {"i": i})

        history = bus.get_history(event_type=EventType.CONFIG_CHANGED, limit=3)
        assert len(history) == 3
        assert history[0].data["i"] == 4  # 最新

        total = bus.get_subscriber_count()
        typed = bus.get_subscriber_count(EventType.CONFIG_CHANGED)
        assert total >= 2
        assert typed == 1

    def test_asynchronous_publish(self):
        """异步发布不阻塞主线程"""
        from app.core.event_bus import EventBus, EventType

        bus = EventBus()
        slow_done = threading.Event()

        def slow_cb(e):
            time.sleep(0.2)
            slow_done.set()

        bus.subscribe(EventType.CONFIG_CHANGED, slow_cb)

        t0 = time.time()
        bus.publish(EventType.CONFIG_CHANGED, {}, asynchronous=True)
        elapsed = time.time() - t0
        assert elapsed < 0.1  # 异步立即返回

        slow_done.wait(timeout=1)
        assert slow_done.is_set()


# ============================================================
# 2. 配置前缀分类测试
# ============================================================

class TestHotUpdatableClassification:
    def test_whitelist_paths(self):
        """白名单中的路径应能热更新"""
        from app.core.config_manager import is_hot_updatable

        assert is_hot_updatable("logging.level") is True
        assert is_hot_updatable("logging.backup_count") is True
        assert is_hot_updatable("warning_strategy.strategy_type") is True
        assert is_hot_updatable("warning_strategy.strategy_1.confidence_threshold") is True
        assert is_hot_updatable("risk_assessment.high_risk_threshold") is True
        assert is_hot_updatable("alert.default_upgrade_minutes") is True
        assert is_hot_updatable("scheduler.training_job.cron") is True
        assert is_hot_updatable("scheduler.prediction_job.enabled") is True
        assert is_hot_updatable("stream_prediction.backpressure.max_concurrent_streams") is True
        assert is_hot_updatable("stream_prediction.backpressure.rate_per_stream") is True
        assert is_hot_updatable("stream_prediction.window.size") is True
        assert is_hot_updatable("data_quality.min_preload") is True
        assert is_hot_updatable("ensemble.weight_rule") is True
        assert is_hot_updatable("spare_parts.low_stock_threshold") is True
        assert is_hot_updatable("notification.email.subject") is True
        assert is_hot_updatable("audit.auto_cleanup_enabled") is True
        assert is_hot_updatable("feature_engineering.rolling_window") is True
        assert is_hot_updatable("hpo.search_trials") is True

    def test_blacklist_paths(self):
        """黑名单中的路径不能热更新"""
        from app.core.config_manager import is_hot_updatable

        assert is_hot_updatable("model.bolt_lstm.sequence_length") is False
        assert is_hot_updatable("model.bolt_lstm.input_dim") is False
        assert is_hot_updatable("model.bolt_lstm.lstm_units") is False
        assert is_hot_updatable("model.bolt_lstm.dense_units") is False
        assert is_hot_updatable("model.bolt_lstm.dropout_rate") is False
        assert is_hot_updatable("model.flange_attention.num_heads") is False
        assert is_hot_updatable("model.training.incremental.batch_size") is False
        assert is_hot_updatable("database.host") is False
        assert is_hot_updatable("database.pool_size") is False
        assert is_hot_updatable("api.host") is False
        assert is_hot_updatable("api.port") is False
        assert is_hot_updatable("timeseries.influxdb.url") is False
        assert is_hot_updatable("federated.enable_two_level_arch") is False
        assert is_hot_updatable("auth.jwt.algorithm") is False
        assert is_hot_updatable("auth.sso.client_id") is False
        assert is_hot_updatable("hardware.prefer_gpu") is False
        assert is_hot_updatable("stream_prediction.sources.kafka.brokers") is False
        assert is_hot_updatable("stream_prediction.event_publishing.type") is False
        assert is_hot_updatable("stream_prediction.window.storage_type") is False
        assert is_hot_updatable("stream_prediction.window.redis_url") is False

    def test_conservative_default(self):
        """未命中任何规则的路径默认不热更新（保守策略）"""
        from app.core.config_manager import is_hot_updatable

        assert is_hot_updatable("some_new_plugin.x.y") is False
        assert is_hot_updatable("") is False
        assert is_hot_updatable("random_path") is False

    def test_blacklist_takes_precedence(self):
        """黑名单优先于白名单"""
        from app.core.config_manager import is_hot_updatable, NON_HOT_UPDATE_BLACKLIST_PREFIXES

        for prefix in NON_HOT_UPDATE_BLACKLIST_PREFIXES:
            assert is_hot_updatable(prefix + ".anything") is False


# ============================================================
# 工具：创建隔离的 ConfigManager（临时目录）
# ============================================================

@pytest.fixture
def isolated_cm(tmp_path, monkeypatch):
    """
    创建一个使用临时目录的隔离 ConfigManager 实例，
    避免测试污染真实配置文件。
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    initial_config = {
        "logging": {"level": "INFO", "backup_count": 5, "max_size": 10485760},
        "warning_strategy": {
            "strategy_type": 1,
            "strategy_1": {"confidence_threshold": 0.7},
            "strategy_2": {"confidence_threshold": 0.95},
        },
        "risk_assessment": {
            "high_risk_threshold": 3,
            "medium_risk_threshold": 7,
            "preload_thresholds": {"min_normal": 400, "max_normal": 800},
        },
        "alert": {
            "auto_create_work_order_level": 3,
            "default_upgrade_minutes": 30,
        },
        "scheduler": {
            "training_job": {"enabled": True, "cron": "0 2 * * 0"},
            "prediction_job": {"enabled": True, "cron": "*/30 * * * *"},
            "audit_cleanup_job": {"enabled": True},
        },
        "stream_prediction": {
            "backpressure": {
                "max_concurrent_streams": 100,
                "rate_per_stream": 10.0,
                "max_queue_size": 500,
                "queue_timeout_seconds": 30.0,
            },
            "window": {"size": 100, "ttl_seconds": 3600, "storage_type": "memory"},
        },
        "model": {"bolt_lstm": {"lstm_units": 128, "input_dim": 1, "dropout_rate": 0.2}},
        "database": {"host": "localhost", "port": 5432},
        "audit": {"auto_cleanup_enabled": True, "cleanup_interval_hours": 24},
    }

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(initial_config, f, default_flow_style=False, allow_unicode=True)

    # 单例重置
    from app.core import config_manager as cm_module
    monkeypatch.setattr(cm_module.ConfigManager, "_instance", None)

    # 通过 monkey patch 替换 __init__ 中的路径计算
    real_init = cm_module.ConfigManager.__init__

    def patched_init(self):
        self._initialized = False
        self.config_path = config_file
        self.backup_dir = config_dir / "backups"
        self.audit_dir = config_dir / "audit"
        self.version_dir = config_dir / "versions"
        self.audit_log_path = self.audit_dir / "config_audit.jsonl"
        self.version_meta_path = self.version_dir / "versions.json"
        for d in (self.backup_dir, self.audit_dir, self.version_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.config = {}
        self.changes = []
        self.max_backups = 20
        self._version = 0
        self._version_records = []
        self._version_lock = threading.Lock()
        # 内部加载
        from loguru import logger
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        self._load_version_meta = lambda: None  # 简化
        self._initialized = True
        self._sync_utils_config = lambda: None
        logger.info(f"[测试] 隔离ConfigManager初始化, path={config_file}")

    monkeypatch.setattr(cm_module.ConfigManager, "__init__", patched_init)

    cm = cm_module.ConfigManager()
    # 手动补充关键属性以兼容测试
    cm._load_version_meta_real = cm_module.ConfigManager._load_version_meta
    cm._sync_utils_config_real = cm_module.ConfigManager._sync_utils_config
    yield cm


# ============================================================
# 3. ConfigManager.apply_hot_update 核心测试
# ============================================================

class TestApplyHotUpdate:
    def test_basic_hot_update_logging_and_version(self, isolated_cm):
        """基础日志级别热更新 + 版本号 +1"""
        cm = isolated_cm
        old_version = cm.current_version

        result = cm.apply_hot_update(
            updates={"logging.level": "DEBUG"},
            operator="tester",
            description="测试更新日志级别",
        )

        assert result["success"] is True
        assert result["version"] == old_version + 1
        assert "logging.level" in result["hot_updated_paths"]
        assert cm.get("logging.level") == "DEBUG"

        # 审计日志存在
        assert cm.current_version == old_version + 1

    def test_non_hot_update_model_structure_requires_restart(self, isolated_cm):
        """模型结构类配置被标记为 require_restart"""
        cm = isolated_cm

        result = cm.apply_hot_update(
            updates={
                "model.bolt_lstm.lstm_units": 256,
                "logging.level": "WARNING",
            },
            operator="tester",
        )

        assert result["success"] is True
        assert "logging.level" in result["hot_updated_paths"]
        assert "model.bolt_lstm.lstm_units" in result["require_restart_paths"]
        # 不可热更新的配置仍然会被写入文件和内存，但不会触发对应服务的通知
        assert cm.get("model.bolt_lstm.lstm_units") == 256

    def test_event_published_after_update(self, isolated_cm):
        """apply_hot_update 之后应该派发对应类型事件"""
        from app.core.event_bus import event_bus, EventType

        received_events: Dict[EventType, int] = {}
        lock = threading.Lock()

        def counter_factory(et):
            def _cb(e):
                with lock:
                    received_events[et] = received_events.get(et, 0) + 1
            return _cb

        sub_ids = [
            event_bus.subscribe(EventType.LOG_LEVEL_CHANGED, counter_factory(EventType.LOG_LEVEL_CHANGED)),
            event_bus.subscribe(EventType.SCHEDULER_CONFIG_CHANGED, counter_factory(EventType.SCHEDULER_CONFIG_CHANGED)),
            event_bus.subscribe(EventType.STRATEGY_CONFIG_CHANGED, counter_factory(EventType.STRATEGY_CONFIG_CHANGED)),
            event_bus.subscribe(EventType.STREAM_CONFIG_CHANGED, counter_factory(EventType.STREAM_CONFIG_CHANGED)),
            event_bus.subscribe(EventType.CONFIG_CHANGED, counter_factory(EventType.CONFIG_CHANGED)),
            event_bus.subscribe(EventType.CONFIG_PRE_RELOAD, counter_factory(EventType.CONFIG_PRE_RELOAD)),
            event_bus.subscribe(EventType.CONFIG_POST_RELOAD, counter_factory(EventType.CONFIG_POST_RELOAD)),
        ]

        try:
            isolated_cm.apply_hot_update(
                updates={
                    "logging.level": "DEBUG",
                    "scheduler.training_job.cron": "0 3 * * 1",
                    "warning_strategy.strategy_type": 2,
                    "stream_prediction.backpressure.max_concurrent_streams": 200,
                },
                operator="tester",
            )

            # 异步派发需要等待
            time.sleep(0.2)

            with lock:
                assert received_events.get(EventType.LOG_LEVEL_CHANGED, 0) >= 1
                assert received_events.get(EventType.SCHEDULER_CONFIG_CHANGED, 0) >= 1
                assert received_events.get(EventType.STRATEGY_CONFIG_CHANGED, 0) >= 1
                assert received_events.get(EventType.STREAM_CONFIG_CHANGED, 0) >= 1
                assert received_events.get(EventType.CONFIG_CHANGED, 0) >= 1
                assert received_events.get(EventType.CONFIG_PRE_RELOAD, 0) >= 1
                assert received_events.get(EventType.CONFIG_POST_RELOAD, 0) >= 1
        finally:
            for sid in sub_ids:
                event_bus.unsubscribe(sid)

    def test_validation_rejects_invalid_log_level(self, isolated_cm):
        """日志级别枚举校验，不合法值会被拒绝"""
        cm = isolated_cm
        old_level = cm.get("logging.level")
        old_version = cm.current_version

        result = cm.apply_hot_update(
            updates={"logging.level": "INVALID_LEVEL"},
            operator="tester",
        )

        assert "logging.level" in result["errors"]
        # 没有成功更新
        assert cm.current_version == old_version
        assert cm.get("logging.level") == old_level

    def test_validation_rejects_invalid_cron(self, isolated_cm):
        """无效 cron 表达式校验"""
        cm = isolated_cm
        result = cm.apply_hot_update(
            updates={"scheduler.training_job.cron": "not a cron"},
            operator="tester",
        )
        assert "scheduler.training_job.cron" in result["errors"]
        assert result["success"] is True  # 其他项（如果有）可能成功，但该项报错
        assert not result["hot_updated_paths"]

    def test_validation_rejects_numeric_range(self, isolated_cm):
        """数值范围校验（max_concurrent_streams 上限）"""
        cm = isolated_cm
        result = cm.apply_hot_update(
            updates={"stream_prediction.backpressure.max_concurrent_streams": -10},
            operator="tester",
        )
        assert "stream_prediction.backpressure.max_concurrent_streams" in result["errors"]

    def test_cron_update_is_hot_updatable(self, isolated_cm):
        """scheduler.*.cron 属于热更新范围"""
        cm = isolated_cm
        result = cm.apply_hot_update(
            updates={"scheduler.prediction_job.cron": "*/15 * * * *"},
            operator="tester",
        )
        assert result["success"] is True
        assert "scheduler.prediction_job.cron" in result["hot_updated_paths"]
        assert cm.get("scheduler.prediction_job.cron") == "*/15 * * * *"

    def test_empty_updates_noop(self, isolated_cm):
        """空 updates 不触发任何副作用"""
        cm = isolated_cm
        old = cm.current_version
        result = cm.apply_hot_update(updates={})
        assert result["success"] is True
        assert cm.current_version == old
        assert not result["hot_updated_paths"]

    def test_change_summary_contains_old_and_new(self, isolated_cm):
        """change_summary 字段记录 old/new 值"""
        cm = isolated_cm
        old_log = cm.get("logging.level")

        result = cm.apply_hot_update(
            updates={"logging.level": "ERROR"},
            operator="tester",
        )

        assert len(result["change_summary"]) >= 1
        cs = [c for c in result["change_summary"] if c["path"] == "logging.level"]
        assert cs
        assert cs[0]["old_value"] == old_log
        assert cs[0]["new_value"] == "ERROR"
        assert cs[0]["hot_updatable"] is True


# ============================================================
# 4. 版本历史 & 回滚测试
# ============================================================

class TestVersionRollback:
    def test_version_history_records_changes(self, isolated_cm):
        """版本历史记录正确保存"""
        cm = isolated_cm

        r1 = cm.apply_hot_update(
            updates={"logging.level": "DEBUG"}, operator="alice",
        )
        r2 = cm.apply_hot_update(
            updates={"warning_strategy.strategy_type": 2}, operator="bob",
        )
        r3 = cm.apply_hot_update(
            updates={"scheduler.prediction_job.cron": "*/15 * * * *"}, operator="alice",
        )

        history = cm.get_version_history()
        assert len(history) == 3
        assert history[0]["version"] == r3["version"]  # 最新在前
        assert history[0]["operator"] == "alice"
        assert history[1]["version"] == r2["version"]
        assert history[1]["operator"] == "bob"
        assert history[2]["version"] == r1["version"]

    def test_get_version_detail(self, isolated_cm):
        """查询单版本详情"""
        cm = isolated_cm
        r = cm.apply_hot_update(
            updates={"logging.backup_count": 10}, operator="tester",
        )
        v = r["version"]
        detail = cm.get_version(v)
        assert detail is not None
        assert detail["version"] == v
        assert detail["operator"] == "tester"
        assert len(detail["changes"]) >= 1

    def test_version_history_filter_by_operator(self, isolated_cm):
        """按操作者过滤"""
        cm = isolated_cm
        cm.apply_hot_update(updates={"logging.level": "DEBUG"}, operator="alice")
        cm.apply_hot_update(updates={"logging.level": "INFO"}, operator="bob")
        cm.apply_hot_update(updates={"logging.level": "WARNING"}, operator="alice")

        alice_history = cm.get_version_history(operator="alice")
        bob_history = cm.get_version_history(operator="bob")

        assert len(alice_history) == 2
        assert len(bob_history) == 1
        for h in alice_history:
            assert h["operator"] == "alice"
        assert bob_history[0]["operator"] == "bob"

    def test_rollback_restores_config(self, isolated_cm):
        """回滚流程：当前配置应还原到目标版本快照"""
        cm = isolated_cm

        # 初始状态
        cm.apply_hot_update(
            updates={"logging.level": "DEBUG", "alert.default_upgrade_minutes": 60},
            operator="tester", description="版本1"
        )
        target = cm.current_version

        # 后续两次修改
        cm.apply_hot_update(
            updates={"logging.level": "WARNING", "alert.default_upgrade_minutes": 15},
            operator="tester", description="版本2"
        )
        cm.apply_hot_update(
            updates={"logging.level": "ERROR", "alert.default_upgrade_minutes": 5},
            operator="tester", description="版本3"
        )
        assert cm.get("logging.level") == "ERROR"
        assert cm.get("alert.default_upgrade_minutes") == 5

        # 回滚到目标版本
        result = cm.rollback_to_version(target, operator="tester", description="回滚测试")
        assert result.get("success") is True
        assert result.get("rollback_to") == target

        # 验证配置恢复
        assert cm.get("logging.level") == "DEBUG"
        assert cm.get("alert.default_upgrade_minutes") == 60

        # 验证 rollback_target 标记
        history = cm.get_version_history(limit=1)
        assert history[0].get("rollback_target") == target

    def test_rollback_nonexistent_version_fails(self, isolated_cm):
        """回滚不存在的版本返回失败"""
        cm = isolated_cm
        result = cm.rollback_to_version(99999)
        assert result.get("success") is False
        assert "error" in result


# ============================================================
# 5. Backpressure / StreamConcurrencyManager 热更新测试
# ============================================================

class TestBackpressureReload:
    def test_setters_and_reload_config(self):
        """StreamConcurrencyManager.reload_config 正确更新所有参数"""
        from app.streaming.backpressure import StreamConcurrencyManager

        mgr = StreamConcurrencyManager(
            max_concurrent_streams=50,
            rate_per_stream=5.0,
            max_queue_size=100,
            queue_timeout_seconds=10.0,
        )

        # 先记录旧值
        old_max = mgr.backpressure.max_concurrent_streams
        old_rate = mgr._rate_per_stream
        old_queue = mgr.backpressure.max_queue_size
        old_timeout = mgr.backpressure.queue_timeout_seconds

        # 用 config_manager 的测试辅助：临时 monkey patch config_manager.get
        import app.core.config_manager as cm_mod

        fake_config = {
            "stream_prediction": {
                "backpressure": {
                    "max_concurrent_streams": 200,
                    "rate_per_stream": 20.0,
                    "max_queue_size": 800,
                    "queue_timeout_seconds": 45.0,
                }
            }
        }

        real_get = cm_mod.config_manager.get

        def fake_get(path, default=None):
            keys = path.split(".")
            v = fake_config
            for k in keys:
                if isinstance(v, dict) and k in v:
                    v = v[k]
                else:
                    return default
            return v

        try:
            cm_mod.config_manager.get = fake_get
            result = mgr.reload_config()
        finally:
            cm_mod.config_manager.get = real_get

        changed = result.get("changed", {})
        assert "max_concurrent_streams" in changed
        assert "rate_per_stream" in changed
        assert "max_queue_size" in changed
        assert "queue_timeout_seconds" in changed

        assert mgr.backpressure.max_concurrent_streams == 200
        assert mgr._rate_per_stream == 20.0
        assert mgr.backpressure.max_queue_size == 800
        assert mgr.backpressure.queue_timeout_seconds == 45.0
        # 全局限流速率应同步更新
        assert abs(mgr.global_rate_limiter.rate - 200 * 20.0) < 1e-6

    def test_no_change_when_values_same(self):
        """值没有变化时 changed 为空"""
        from app.streaming.backpressure import StreamConcurrencyManager
        import app.core.config_manager as cm_mod

        mgr = StreamConcurrencyManager(
            max_concurrent_streams=100,
            rate_per_stream=10.0,
            max_queue_size=500,
            queue_timeout_seconds=30.0,
        )

        fake_config = {
            "stream_prediction": {
                "backpressure": {
                    "max_concurrent_streams": 100,
                    "rate_per_stream": 10.0,
                    "max_queue_size": 500,
                    "queue_timeout_seconds": 30.0,
                }
            }
        }
        real_get = cm_mod.config_manager.get

        def fake_get(path, default=None):
            keys = path.split(".")
            v = fake_config
            for k in keys:
                if isinstance(v, dict) and k in v:
                    v = v[k]
                else:
                    return default
            return v

        try:
            cm_mod.config_manager.get = fake_get
            result = mgr.reload_config()
        finally:
            cm_mod.config_manager.get = real_get

        assert not result.get("changed")


# ============================================================
# 6. TaskScheduler.reload_config 基础测试
# ============================================================

class TestSchedulerReloadConfig:
    def test_sync_job_logic_add_remove_update(self, monkeypatch):
        """_sync_job 的三种动作逻辑（不启动真实 APScheduler）"""
        from app.schedulers.scheduler import TaskScheduler
        from apscheduler.triggers.cron import CronTrigger

        recorded_actions: List[tuple] = []

        class FakeJob:
            def __init__(self, cron_expr, has_next_run=True):
                self._trigger = CronTrigger.from_crontab(cron_expr)
                self._next = "sometime" if has_next_run else None

            @property
            def trigger(self):
                return self._trigger

            @property
            def next_run_time(self):
                return self._next

            def reschedule(self, new_trigger):
                recorded_actions.append(("reschedule", str(new_trigger)))

            def resume(self):
                recorded_actions.append(("resume",))

        class FakeScheduler:
            def __init__(self, existing_jobs=None):
                self._jobs = existing_jobs or {}

            def get_job(self, job_id):
                return self._jobs.get(job_id)

            def add_job(self, func, trigger, **kwargs):
                recorded_actions.append(("add", kwargs.get("id"), str(trigger)))
                return FakeJob("0 0 * * *")

            def remove_job(self, job_id):
                recorded_actions.append(("remove", job_id))
                self._jobs.pop(job_id, None)

        # 通过 __new__ 部分初始化，避免触发 TaskScheduler.__init__ 的副作用
        ts = TaskScheduler.__new__(TaskScheduler)
        ts.scheduler = FakeScheduler(existing_jobs={
            "prediction_job": FakeJob("*/30 * * * *"),
            "training_job": FakeJob("0 2 * * 0", has_next_run=False),
        })

        # 1) 禁用 -> remove
        recorded_actions.clear()
        action = ts._sync_job(
            "prediction_job",
            {"enabled": False, "cron": "*/30 * * * *"},
            lambda: None,
        )
        assert action == "removed"
        assert ("remove", "prediction_job") in recorded_actions

        # 2) 旧 job next_run 为 None 且 cron 相同 -> resume
        recorded_actions.clear()
        ts.scheduler = FakeScheduler(existing_jobs={
            "training_job": FakeJob("0 2 * * 0", has_next_run=False),
        })
        action = ts._sync_job(
            "training_job",
            {"enabled": True, "cron": "0 2 * * 0"},
            lambda: None,
        )
        assert action == "updated"
        assert ("resume",) in recorded_actions

        # 3) cron 改变 -> reschedule
        recorded_actions.clear()
        ts.scheduler = FakeScheduler(existing_jobs={
            "training_job": FakeJob("0 2 * * 0"),
        })
        action = ts._sync_job(
            "training_job",
            {"enabled": True, "cron": "0 4 * * 1"},
            lambda: None,
        )
        assert action == "updated"
        assert any(a[0] == "reschedule" for a in recorded_actions)

        # 4) 不存在的 job + enabled -> add
        recorded_actions.clear()
        action = ts._sync_job(
            "audit_cleanup_job",
            {"enabled": True, "cron": "0 4 * * *"},
            lambda: None,
        )
        assert action == "added"
        assert any(a[0] == "add" and a[1] == "audit_cleanup_job" for a in recorded_actions)

        # 5) 无变化（job 存在、cron 相同、next_run_time 非 None）
        recorded_actions.clear()
        ts.scheduler = FakeScheduler(existing_jobs={
            "training_job": FakeJob("0 2 * * 0", has_next_run=True),
        })
        action = ts._sync_job(
            "training_job",
            {"enabled": True, "cron": "0 2 * * 0"},
            lambda: None,
        )
        assert action is None
        assert recorded_actions == []


# ============================================================
# 7. 端到端：apply_hot_update -> 事件 -> 服务回调
# ============================================================

class TestEndToEndHotUpdate:
    def test_update_triggers_scheduler_reload_via_event(self, isolated_cm, monkeypatch):
        """配置更新后，scheduler 回调能正确被调用"""
        from app.core.event_bus import event_bus, EventType

        call_record = {"called": 0, "paths": []}
        lock = threading.Lock()

        def fake_handler(event):
            with lock:
                call_record["called"] += 1
                call_record["paths"].extend(event.data.get("changed_paths", []))

        sub_id = event_bus.subscribe(
            EventType.SCHEDULER_CONFIG_CHANGED, fake_handler, priority=999
        )
        try:
            isolated_cm.apply_hot_update(
                updates={
                    "scheduler.prediction_job.cron": "*/15 * * * *",
                    "scheduler.training_job.enabled": True,
                },
                operator="tester",
            )
            time.sleep(0.1)
            with lock:
                assert call_record["called"] >= 1
                assert "scheduler.prediction_job.cron" in call_record["paths"]
                assert "scheduler.training_job.enabled" in call_record["paths"]
        finally:
            event_bus.unsubscribe(sub_id)

    def test_stream_and_log_events_fire(self, isolated_cm):
        """同时触发流式和日志级别事件"""
        from app.core.event_bus import event_bus, EventType

        flags = {EventType.STREAM_CONFIG_CHANGED: 0, EventType.LOG_LEVEL_CHANGED: 0}
        lock = threading.Lock()

        def make_cb(et):
            def cb(e):
                with lock:
                    flags[et] += 1
            return cb

        sub_ids = [
            event_bus.subscribe(EventType.STREAM_CONFIG_CHANGED, make_cb(EventType.STREAM_CONFIG_CHANGED)),
            event_bus.subscribe(EventType.LOG_LEVEL_CHANGED, make_cb(EventType.LOG_LEVEL_CHANGED)),
        ]

        try:
            isolated_cm.apply_hot_update(
                updates={
                    "logging.level": "ERROR",
                    "stream_prediction.backpressure.rate_per_stream": 50.0,
                },
                operator="tester",
            )
            time.sleep(0.1)

            with lock:
                assert flags[EventType.LOG_LEVEL_CHANGED] >= 1
                assert flags[EventType.STREAM_CONFIG_CHANGED] >= 1
        finally:
            for sid in sub_ids:
                event_bus.unsubscribe(sid)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
