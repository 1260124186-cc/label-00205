"""
配置持久化管理模块（支持热更新）

提供配置的动态修改、版本管理、热更新通知、审计和回滚功能。

核心能力:
1. 配置动态更新 + 持久化（文件 + 版本）
2. 热更新范围过滤（日志级别、策略阈值、调度cron、流式并发；模型结构类不热更新）
3. 内存 pub/sub 消息通知（event_bus）+ 各服务 reload_config()
4. 多实例部署通过 Redis 广播配置版本号（config_sync）
5. 变更审计（内存 + JSON 日志文件）
6. 版本回滚（一键回滚到历史版本）
7. 与 /config/center API 统一

热更新配置前缀（白名单）:
    logging.level                   -> 日志级别
    warning_strategy.*              -> 策略阈值
    risk_assessment.*               -> 风险阈值
    alert.*                         -> 告警阈值
    scheduler.*.cron                -> 调度 cron
    scheduler.*.enabled             -> 调度启停
    stream_prediction.backpressure.*-> 流式并发/背压
    stream_prediction.window.size   -> 滑动窗口大小
    data_quality.*                  -> 数据质量阈值
    ensemble.*                      -> 集成学习权重/阈值
    spare_parts.*                   -> 备件阈值

不热更新（黑名单，需重启）:
    model.*.sequence_length         -> 模型输入维度
    model.*.lstm_units              -> LSTM 单元数
    model.*.dense_units             -> 全连接层维度
    model.*.input_dim               -> 输入维度
    model.*.output_classes          -> 输出类别数
    database.*                      -> 数据库连接
    api.*                           -> API端口/地址
    timeseries.*                    -> 时序库连接
    federated.*                     -> 联邦架构参数

使用示例:
    from app.core.config_manager import ConfigManager, config_manager

    # 批量热更新（自动通知 + Redis广播 + 审计 + 版本）
    result = config_manager.apply_hot_update(
        updates={
            'logging.level': 'DEBUG',
            'scheduler.prediction_job.cron': '*/15 * * * *',
            'stream_prediction.backpressure.max_concurrent_streams': 200,
        },
        operator='admin-user',
        description='调试期间调整日志与调度',
    )

    # 回滚到指定版本
    config_manager.rollback_to_version(version=5, operator='admin')
"""

import os
import yaml
import json
import copy
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field, asdict
from threading import Lock
from loguru import logger

from app.core.event_bus import event_bus, EventType
from app.core.redis_broadcast import config_sync


HOT_UPDATE_WHITELIST_PREFIXES: Tuple[str, ...] = (
    'logging.level',
    'logging.backup_count',
    'logging.max_size',
    'warning_strategy.',
    'risk_assessment.',
    'alert.',
    'scheduler.',
    'stream_prediction.backpressure.',
    'stream_prediction.window.size',
    'stream_prediction.window.ttl_seconds',
    'data_quality.',
    'ensemble.',
    'spare_parts.',
    'notification.',
    'work_order.',
    'audit.',
    'feature_engineering.',
    'hpo.',
)

NON_HOT_UPDATE_BLACKLIST_PREFIXES: Tuple[str, ...] = (
    'model.bolt_lstm.sequence_length',
    'model.bolt_lstm.input_dim',
    'model.bolt_lstm.lstm_units',
    'model.bolt_lstm.dense_units',
    'model.bolt_lstm.output_classes',
    'model.bolt_lstm.dropout_rate',
    'model.flange_attention.',
    'model.training.incremental.',
    'database.',
    'api.',
    'timeseries.',
    'federated.enable_two_level_arch',
    'federated.client_config.fine_tune_layers',
    'auth.jwt.algorithm',
    'auth.sso.',
    'hardware.prefer_gpu',
    'stream_prediction.sources.',
    'stream_prediction.event_publishing.type',
    'stream_prediction.window.storage_type',
    'stream_prediction.window.redis_url',
)


@dataclass
class ConfigChange:
    path: str
    old_value: Any
    new_value: Any
    timestamp: str
    user: str = "system"
    hot_updatable: bool = True


@dataclass
class ConfigVersionRecord:
    """
    配置版本记录（用于审计 + 回滚）

    Attributes:
        version: 单调递增版本号
        timestamp: 变更时间（ISO格式）
        operator: 操作者
        description: 变更说明
        changes: 变更明细列表
        snapshot_before: 变更前配置快照路径
        snapshot_after: 变更后配置快照路径
        rollback_target: 回滚到的目标版本号（回滚操作时记录）
    """
    version: int
    timestamp: str
    operator: str
    description: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    snapshot_before: str = ""
    snapshot_after: str = ""
    rollback_target: Optional[int] = None


class ConfigValidator:
    """
    配置验证器（扩展原有规则）
    """

    RULES = {
        'database.pool_size': {'type': int, 'min': 1, 'max': 500},
        'database.max_overflow': {'type': int, 'min': 0, 'max': 500},
        'model.bolt_lstm.epochs': {'type': int, 'min': 1, 'max': 10000},
        'model.bolt_lstm.learning_rate': {'type': float, 'min': 1e-8, 'max': 1.0},
        'model.training.batch_size': {'type': int, 'min': 1, 'max': 4096},
        'logging.level': {'type': str, 'allowed': ['TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
        'stream_prediction.backpressure.max_concurrent_streams': {'type': int, 'min': 1, 'max': 100000},
        'stream_prediction.backpressure.rate_per_stream': {'type': float, 'min': 0.01, 'max': 100000.0},
        'stream_prediction.backpressure.max_queue_size': {'type': int, 'min': 0, 'max': 1000000},
        'stream_prediction.backpressure.queue_timeout_seconds': {'type': float, 'min': 0.1, 'max': 3600.0},
        'warning_strategy.strategy_type': {'type': int, 'allowed': [1, 2]},
        'risk_assessment.high_risk_threshold': {'type': int, 'min': 1, 'max': 10},
        'risk_assessment.medium_risk_threshold': {'type': int, 'min': 1, 'max': 10},
        'alert.auto_create_work_order_level': {'type': int, 'min': 1, 'max': 4},
        'alert.default_upgrade_minutes': {'type': int, 'min': 1, 'max': 10080},
        'scheduler.training_job.enabled': {'type': bool},
        'scheduler.prediction_job.enabled': {'type': bool},
        'scheduler.monthly_prediction_job.enabled': {'type': bool},
        'scheduler.alert_upgrade_job.enabled': {'type': bool},
        'scheduler.audit_cleanup_job.enabled': {'type': bool},
    }

    @classmethod
    def validate(cls, path: str, value: Any) -> Tuple[bool, Optional[str]]:
        if path not in cls.RULES:
            return True, None
        rule = cls.RULES[path]
        expected_type = rule.get('type')
        if expected_type and not isinstance(value, expected_type):
            try:
                if expected_type == bool and isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes')
                else:
                    value = expected_type(value)
            except (ValueError, TypeError):
                return False, f"类型错误，期望 {expected_type.__name__}"
        if 'min' in rule and expected_type in (int, float) and value < rule['min']:
            return False, f"值太小，最小值为 {rule['min']}"
        if 'max' in rule and expected_type in (int, float) and value > rule['max']:
            return False, f"值太大，最大值为 {rule['max']}"
        if 'allowed' in rule and value not in rule['allowed']:
            return False, f"无效值，允许的值为 {rule['allowed']}"
        return True, None

    @classmethod
    def validate_cron(cls, cron_expr: str) -> Tuple[bool, Optional[str]]:
        """简化版 cron 表达式校验（仅字段数量 + 基本范围）"""
        try:
            fields = cron_expr.strip().split()
            if len(fields) != 5:
                return False, "cron表达式必须包含5个字段（分 时 日 月 周）"
            ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
            for field, (lo, hi) in zip(fields, ranges):
                if field in ('*', '?'):
                    continue
                for part in field.split(','):
                    token = part.split('/')[0]
                    if '-' in token:
                        a, b = token.split('-')
                        if not (lo <= int(a) <= hi and lo <= int(b) <= hi):
                            return False, f"字段值超出范围 [{lo},{hi}]: {part}"
                    elif token.isdigit():
                        if not (lo <= int(token) <= hi):
                            return False, f"字段值超出范围 [{lo},{hi}]: {part}"
            return True, None
        except Exception as e:
            return False, f"cron表达式解析失败: {e}"


def is_hot_updatable(path: str) -> bool:
    """
    判断配置路径是否可热更新
    - 白名单前缀命中 -> 可热更新
    - 黑名单前缀命中 -> 不可热更新
    - 否则默认不可热更新（保守策略，避免误热更新模型结构类配置）
    """
    for bl in NON_HOT_UPDATE_BLACKLIST_PREFIXES:
        if path.startswith(bl):
            return False
    for wl in HOT_UPDATE_WHITELIST_PREFIXES:
        if path.startswith(wl):
            return True
    return False


class ConfigManager:
    """
    增强型配置管理器（支持热更新）

    单例模式，线程安全。
    新增能力：版本号、事件通知、Redis广播、审计、回滚。
    """

    _instance: Optional['ConfigManager'] = None
    _lock = Lock()

    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return

        self.config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
        self.backup_dir = self.config_path.parent / 'backups'
        self.audit_dir = self.config_path.parent / 'audit'
        self.version_dir = self.config_path.parent / 'versions'
        self.audit_log_path = self.audit_dir / 'config_audit.jsonl'
        self.version_meta_path = self.version_dir / 'versions.json'

        for d in (self.backup_dir, self.audit_dir, self.version_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.config: Dict[str, Any] = {}
        self.changes: List[ConfigChange] = []
        self.max_backups = 20

        self._version: int = 0
        self._version_records: List[ConfigVersionRecord] = []
        self._version_lock = Lock()

        self._load()
        self._load_version_meta()
        self._initialized = True

        self._sync_utils_config()

        logger.info(
            f"配置管理器初始化完成: path={self.config_path}, "
            f"version=v{self._version}, redis_sync={config_sync.is_enabled}"
        )

    # ============================================================
    # 内部工具方法
    # ============================================================

    def _load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}

    def _sync_utils_config(self) -> None:
        """同步到 app.utils.config.Config 单例，保持兼容"""
        try:
            from app.utils.config import Config
            cfg = Config()
            cfg._config = copy.deepcopy(self.config)
            cfg._apply_env_overrides()
        except Exception as e:
            logger.warning(f"同步到 utils.config 失败（非关键路径）: {e}")

    def _load_version_meta(self) -> None:
        """加载版本元数据与审计日志"""
        if self.version_meta_path.exists():
            try:
                with open(self.version_meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._version = int(data.get('current_version', 0))
                    for rec in data.get('records', []):
                        self._version_records.append(ConfigVersionRecord(**rec))
                logger.debug(f"加载版本元数据: current_version=v{self._version}, records={len(self._version_records)}")
            except Exception as e:
                logger.warning(f"加载版本元数据失败，将重置: {e}")

        if self.audit_log_path.exists():
            extra = 0
            try:
                with open(self.audit_log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if obj.get('type') == 'config_change' and obj.get('version') > self._version:
                                extra += 1
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"解析审计日志失败: {e}")
            if extra > 0:
                logger.debug(f"审计日志中发现额外记录: {extra}条")

    def _persist_version_meta(self) -> None:
        """持久化版本元数据"""
        try:
            payload = {
                'current_version': self._version,
                'records': [asdict(r) for r in self._version_records[-200:]],
                'updated_at': datetime.now().isoformat(),
            }
            tmp = self.version_meta_path.with_suffix('.jsonl.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            tmp.replace(self.version_meta_path)
        except Exception as e:
            logger.warning(f"持久化版本元数据失败: {e}")

    def _append_audit_log(self, record: Dict[str, Any]) -> None:
        """追加 JSONL 审计日志"""
        try:
            with open(self.audit_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')
        except Exception as e:
            logger.warning(f"写入审计日志失败: {e}")

    def _snapshot_config(self, label: str) -> str:
        """创建当前配置的快照（版本目录），返回快照文件路径"""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        snap = self.version_dir / f"v{self._version}_{label}_{ts}.yaml"
        try:
            with open(snap, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return str(snap)
        except Exception as e:
            logger.warning(f"创建配置快照失败: {e}")
            return ""

    def _create_backup(self) -> None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"config_{timestamp}.yaml"
        shutil.copy2(self.config_path, backup_path)
        self._cleanup_backups()

    def _cleanup_backups(self) -> None:
        backups = sorted(
            self.backup_dir.glob("config_*.yaml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for backup in backups[self.max_backups:]:
            backup.unlink()

    # ============================================================
    # 基础 API（get/set/batch_update）保持兼容
    # ============================================================

    def get(self, path: str, default: Any = None) -> Any:
        keys = path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_all(self) -> Dict[str, Any]:
        return copy.deepcopy(self.config)

    @property
    def current_version(self) -> int:
        return self._version

    def set(self, path: str, value: Any, validate: bool = True) -> Tuple[bool, Optional[str]]:
        if validate:
            if path.endswith('.cron') and isinstance(value, str):
                ok, err = ConfigValidator.validate_cron(value)
                if not ok:
                    return False, err
            is_valid, error = ConfigValidator.validate(path, value)
            if not is_valid:
                return False, error

        old_value = self.get(path)
        keys = path.split('.')
        cfg = self.config
        for key in keys[:-1]:
            if key not in cfg:
                cfg[key] = {}
            cfg = cfg[key]
        cfg[keys[-1]] = value

        self.changes.append(ConfigChange(
            path=path,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.now().isoformat(),
            hot_updatable=is_hot_updatable(path),
        ))
        logger.debug(f"配置已更新（内存）: {path} = {value}, hot={is_hot_updatable(path)}")
        return True, None

    def update(self, path: str, value: Any) -> Tuple[bool, Optional[str]]:
        return self.set(path, value)

    def batch_update(self, updates: Dict[str, Any]) -> Dict[str, Tuple[bool, Optional[str]]]:
        results = {}
        for path, value in updates.items():
            results[path] = self.set(path, value)
        return results

    def save(self, create_backup: bool = True) -> bool:
        """
        保存到文件（不触发热更新通知）。
        推荐使用 apply_hot_update() 替代以获得完整能力。
        """
        try:
            if create_backup and self.config_path.exists():
                self._create_backup()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self.config, f,
                    default_flow_style=False, allow_unicode=True, sort_keys=False
                )
            self.changes.clear()
            self._sync_utils_config()
            logger.info("配置已保存到文件")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    # ============================================================
    # 热更新核心 API
    # ============================================================

    def classify_changes(self, paths: List[str]) -> Tuple[List[str], List[str]]:
        """
        将变更路径分类为 (可热更新路径, 不可热更新路径)
        """
        hot, non_hot = [], []
        for p in paths:
            (hot if is_hot_updatable(p) else non_hot).append(p)
        return hot, non_hot

    def apply_hot_update(
        self,
        updates: Dict[str, Any],
        *,
        operator: str = "system",
        description: str = "",
        require_restart_paths: Optional[List[str]] = None,
        broadcast_redis: bool = True,
        notify_local: bool = True,
    ) -> Dict[str, Any]:
        """
        执行配置热更新（统一入口）

        Args:
            updates: {config_path: new_value}
            operator: 操作者标识
            description: 变更说明
            require_restart_paths: 显式声明需重启的路径（可选）
            broadcast_redis: 是否通过Redis广播（多实例）
            notify_local: 是否发布本地事件通知

        Returns:
            {
                "success": bool,
                "version": int,
                "hot_updated_paths": [...],
                "require_restart_paths": [...],
                "skipped_paths": [...],
                "errors": {path: reason},
                "change_summary": [...],
            }
        """
        result: Dict[str, Any] = {
            "success": False,
            "version": self._version,
            "hot_updated_paths": [],
            "require_restart_paths": [],
            "skipped_paths": [],
            "errors": {},
            "change_summary": [],
        }

        with self._version_lock:
            if not updates:
                result["success"] = True
                return result

            if not config_sync.acquire_update_lock(timeout_seconds=10):
                result["errors"]["__lock__"] = "获取配置更新分布式锁失败，请稍后重试"
                return result

            try:
                # 1. 校验 + 分类
                validated: Dict[str, Any] = {}
                for path, value in updates.items():
                    # cron 特殊校验
                    if path.endswith('.cron') and isinstance(value, str):
                        ok, err = ConfigValidator.validate_cron(value)
                        if not ok:
                            result["errors"][path] = err
                            continue
                    ok, err = ConfigValidator.validate(path, value)
                    if not ok:
                        result["errors"][path] = err
                        continue
                    validated[path] = value

                if result["errors"]:
                    logger.warning(f"配置校验发现 {len(result['errors'])} 项错误，将跳过这些项")

                if not validated:
                    logger.info("没有通过校验的配置项，提前结束热更新")
                    result["success"] = True
                    return result

                hot_paths, non_hot_paths = self.classify_changes(list(validated.keys()))
                explicit_restart = set(require_restart_paths or [])
                require_restart = sorted(set(non_hot_paths) | explicit_restart)
                hot_paths = [p for p in hot_paths if p not in require_restart]

                # 2. 快照（before）
                snapshot_before = self._snapshot_config("before")

                # 3. 应用（只应用通过校验的）
                applied: List[ConfigChange] = []
                for path, value in validated.items():
                    old_value = self.get(path)
                    ok, err = self.set(path, value, validate=False)
                    if not ok:
                        result["errors"][path] = err or "未知错误"
                        continue
                    # 修正 last change 的 timestamp/user
                    if self.changes and self.changes[-1].path == path:
                        self.changes[-1].user = operator
                    applied.append(ConfigChange(
                        path=path,
                        old_value=old_value,
                        new_value=value,
                        timestamp=datetime.now().isoformat(),
                        user=operator,
                        hot_updatable=is_hot_updatable(path) and path not in require_restart,
                    ))

                # 4. 持久化到文件
                saved = self.save(create_backup=True)
                if not saved:
                    result["errors"]["__save__"] = "保存配置文件失败"
                    return result

                # 5. 版本号 +1，写入审计/元数据
                self._version += 1
                version = self._version
                snapshot_after = self._snapshot_config("after")

                changes_detail = [
                    {
                        "path": c.path,
                        "old_value": c.old_value,
                        "new_value": c.new_value,
                        "hot_updatable": c.hot_updatable,
                    }
                    for c in applied
                ]

                record = ConfigVersionRecord(
                    version=version,
                    timestamp=datetime.now().isoformat(),
                    operator=operator,
                    description=description or f"配置热更新 v{version}",
                    changes=changes_detail,
                    snapshot_before=snapshot_before,
                    snapshot_after=snapshot_after,
                    rollback_target=None,
                )
                self._version_records.append(record)
                self._persist_version_meta()

                self._append_audit_log({
                    "type": "config_change",
                    "version": version,
                    "timestamp": record.timestamp,
                    "operator": operator,
                    "description": record.description,
                    "changes": changes_detail,
                    "hot_updated_paths": hot_paths,
                    "require_restart_paths": require_restart,
                    "errors": result["errors"],
                    "instance_id": event_bus.instance_id,
                })

                # 6. 本地事件通知（内存 pub/sub）
                if notify_local and (hot_paths or require_restart):
                    self._publish_local_events(
                        version=version,
                        hot_paths=hot_paths,
                        require_restart=require_restart,
                        operator=operator,
                        description=record.description,
                    )

                # 7. Redis 广播（多实例）
                if broadcast_redis and config_sync.is_enabled:
                    changed_all = sorted(set(hot_paths) | set(require_restart))
                    config_sync.broadcast_version(
                        version=version,
                        changed_paths=changed_all,
                        operator=operator,
                        config_dict=self.config,
                    )

                # 8. 组装返回
                result["success"] = True
                result["version"] = version
                result["hot_updated_paths"] = hot_paths
                result["require_restart_paths"] = require_restart
                result["skipped_paths"] = sorted(set(explicit_restart) - set(validated.keys()))
                result["change_summary"] = changes_detail

                logger.info(
                    f"配置热更新完成: v{version}, "
                    f"hot={len(hot_paths)}, require_restart={len(require_restart)}, "
                    f"errors={len(result['errors'])}, operator={operator}"
                )
                return result

            finally:
                config_sync.release_update_lock()

    def _publish_local_events(
        self,
        version: int,
        hot_paths: List[str],
        require_restart: List[str],
        operator: str,
        description: str,
    ) -> None:
        """发布本地内存事件（细分类型，便于各服务按需订阅）"""
        common_data = {
            "version": version,
            "operator": operator,
            "description": description,
            "hot_paths": hot_paths,
            "require_restart_paths": require_restart,
            "timestamp": datetime.now().isoformat(),
        }

        event_bus.publish(EventType.CONFIG_PRE_RELOAD, data=dict(common_data), asynchronous=True)

        # 日志级别
        log_paths = [p for p in hot_paths if p.startswith('logging.')]
        if log_paths:
            event_bus.publish(
                EventType.LOG_LEVEL_CHANGED,
                data=dict(common_data, changed_paths=log_paths),
                asynchronous=True,
            )

        # 策略阈值
        strategy_paths = [
            p for p in hot_paths
            if p.startswith('warning_strategy.')
            or p.startswith('risk_assessment.')
            or p.startswith('alert.')
            or p.startswith('ensemble.')
        ]
        if strategy_paths:
            event_bus.publish(
                EventType.STRATEGY_CONFIG_CHANGED,
                data=dict(common_data, changed_paths=strategy_paths),
                asynchronous=True,
            )

        # 调度 cron
        sched_paths = [p for p in hot_paths if p.startswith('scheduler.')]
        if sched_paths:
            event_bus.publish(
                EventType.SCHEDULER_CONFIG_CHANGED,
                data=dict(common_data, changed_paths=sched_paths),
                asynchronous=True,
            )

        # 流式并发
        stream_paths = [
            p for p in hot_paths
            if p.startswith('stream_prediction.') or p.startswith('data_quality.')
        ]
        if stream_paths:
            event_bus.publish(
                EventType.STREAM_CONFIG_CHANGED,
                data=dict(common_data, changed_paths=stream_paths),
                asynchronous=True,
            )

        # 总事件
        event_bus.publish(
            EventType.CONFIG_CHANGED,
            data=dict(common_data, changed_paths=list(hot_paths)),
            asynchronous=True,
        )

        event_bus.publish(EventType.CONFIG_POST_RELOAD, data=dict(common_data), asynchronous=True)

    # ============================================================
    # 跨实例 Redis 广播同步入口
    # ============================================================

    def reload_from_disk(self, target_version: Optional[int] = None) -> bool:
        """
        从磁盘重新加载 config.yaml + 版本元数据（用于跨实例 Redis 广播同步）

        Args:
            target_version: 期望的版本号（来自 Redis 广播）。若磁盘版本落后会再次尝试读取
                            （等待 NFS/共享存储延迟），最终仍以磁盘 versions.json 为准。

        Returns:
            是否实际发生了重载（内存配置有变化）
        """
        from datetime import datetime

        old_config_snapshot = json.dumps(self.config, sort_keys=True, ensure_ascii=False, default=str)

        try:
            self._load()
            self._load_version_meta()
            self._sync_utils_config()
        except Exception as e:
            logger.exception(f"从磁盘重载配置失败: {e}")
            return False

        new_config_snapshot = json.dumps(self.config, sort_keys=True, ensure_ascii=False, default=str)
        changed = new_config_snapshot != old_config_snapshot

        if changed:
            logger.info(
                f"从磁盘重载配置完成: version=v{self._version}, "
                f"target_version=v{target_version}, changed={changed}"
            )
        else:
            logger.debug(
                f"从磁盘重载配置完成，但内容无变化: version=v{self._version}"
            )
        return changed

    def dispatch_events_from_paths(
        self,
        changed_paths: List[str],
        *,
        version: Optional[int] = None,
        operator: str = "redis-sync",
        description: str = "跨实例 Redis 配置同步",
        source: str = "redis",
    ) -> None:
        """
        按 changed_paths 分类派发细分事件（用于 Redis 广播收到后触发各服务 reload_config）。

        与 apply_hot_update 的事件派发逻辑完全一致：
        - logging.* → LOG_LEVEL_CHANGED
        - warning_strategy.* / risk_assessment.* / alert.* / ensemble.* → STRATEGY_CONFIG_CHANGED
        - scheduler.* → SCHEDULER_CONFIG_CHANGED
        - stream_prediction.* / data_quality.* → STREAM_CONFIG_CHANGED
        - 所有 hot 路径 → CONFIG_CHANGED
        - 前后包裹 CONFIG_PRE_RELOAD / CONFIG_POST_RELOAD

        Args:
            changed_paths: 变更路径列表（来自 Redis 广播）
            version: 版本号，默认用当前 ConfigManager 的版本
            operator: 操作者标识
            description: 描述
            source: 来源（redis / heartbeat / local）
        """
        if not changed_paths:
            logger.debug("dispatch_events_from_paths: changed_paths 为空，跳过事件派发")
            return

        hot_paths: List[str] = []
        require_restart: List[str] = []
        for p in changed_paths:
            if is_hot_updatable(p):
                hot_paths.append(p)
            else:
                require_restart.append(p)

        if not hot_paths and not require_restart:
            return

        use_version = version if version is not None else self._version
        logger.info(
            f"[source={source}] 派发配置变更细分事件: version=v{use_version}, "
            f"hot={len(hot_paths)}, require_restart={len(require_restart)}"
        )

        self._publish_local_events(
            version=use_version,
            hot_paths=hot_paths,
            require_restart=require_restart,
            operator=operator,
            description=description,
        )

    # ============================================================
    # 回滚 & 历史版本
    # ============================================================

    def get_version_history(
        self,
        limit: int = 50,
        operator: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询版本历史（从新到旧）
        """
        records = list(reversed(self._version_records))
        if operator:
            records = [r for r in records if r.operator == operator]
        out = []
        for r in records[:limit]:
            out.append({
                "version": r.version,
                "timestamp": r.timestamp,
                "operator": r.operator,
                "description": r.description,
                "change_count": len(r.changes),
                "rollback_target": r.rollback_target,
                "snapshot_before": r.snapshot_before,
                "snapshot_after": r.snapshot_after,
                "changes": r.changes,
            })
        return out

    def get_version(self, version: int) -> Optional[Dict[str, Any]]:
        """查询指定版本的详细信息"""
        for r in self._version_records:
            if r.version == version:
                return {
                    "version": r.version,
                    "timestamp": r.timestamp,
                    "operator": r.operator,
                    "description": r.description,
                    "changes": r.changes,
                    "rollback_target": r.rollback_target,
                    "snapshot_before": r.snapshot_before,
                    "snapshot_after": r.snapshot_after,
                }
        return None

    def rollback_to_version(
        self,
        version: int,
        *,
        operator: str = "system",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        回滚到指定版本

        实现：找到该版本的 snapshot_after 文件，读取为目标配置，
        对比当前配置得到变更集合，调用 apply_hot_update()。
        """
        target_record: Optional[ConfigVersionRecord] = None
        for r in self._version_records:
            if r.version == version:
                target_record = r
                break

        if target_record is None:
            return {
                "success": False,
                "error": f"版本 v{version} 不存在",
                "available_versions": [r.version for r in self._version_records[-20:]],
            }

        snapshot_path = Path(target_record.snapshot_after or "")
        if not snapshot_path or not snapshot_path.exists():
            # 退化：使用 snapshot_before 的下一个或 before
            snapshot_path = Path(target_record.snapshot_before or "")
            if not snapshot_path.exists():
                return {
                    "success": False,
                    "error": f"版本 v{version} 的快照文件不存在，无法回滚",
                }

        try:
            with open(snapshot_path, 'r', encoding='utf-8') as f:
                target_config = yaml.safe_load(f) or {}
        except Exception as e:
            return {"success": False, "error": f"读取快照文件失败: {e}"}

        # 计算差异（仅支持顶层值类型差异，嵌套 dict 递归展开成路径）
        updates: Dict[str, Any] = {}

        def flatten(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
            out: Dict[str, Any] = {}
            for k, v in d.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    out.update(flatten(v, key))
                else:
                    out[key] = v
            return out

        flat_current = flatten(self.config)
        flat_target = flatten(target_config)

        all_keys = set(flat_current.keys()) | set(flat_target.keys())
        for k in all_keys:
            cur = flat_current.get(k)
            tgt = flat_target.get(k)
            if cur != tgt and tgt is not None:
                updates[k] = tgt

        if not updates:
            return {
                "success": True,
                "version": self._version,
                "note": "当前配置与目标版本一致，无需回滚",
                "rollback_to": version,
            }

        desc = description or f"回滚到版本 v{version}（基于快照 {snapshot_path.name}）"
        result = self.apply_hot_update(
            updates=updates,
            operator=operator,
            description=desc,
        )

        # 标记为回滚操作
        if result.get("success") and self._version_records:
            self._version_records[-1].rollback_target = version
            self._persist_version_meta()
            self._append_audit_log({
                "type": "config_rollback",
                "from_version": version,
                "to_version": result.get("version"),
                "operator": operator,
                "description": desc,
                "timestamp": datetime.now().isoformat(),
            })

        result["rollback_to"] = version
        return result

    # ============================================================
    # 其他兼容 API
    # ============================================================

    def restore(self, backup_name: Optional[str] = None) -> bool:
        """兼容旧接口：按文件备份恢复（不触发事件通知）"""
        try:
            if backup_name:
                backup_path = self.backup_dir / backup_name
            else:
                backups = sorted(
                    self.backup_dir.glob("config_*.yaml"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if not backups:
                    return False
                backup_path = backups[0]

            if not backup_path.exists():
                return False

            self._create_backup()
            shutil.copy2(backup_path, self.config_path)
            self._load()
            self._sync_utils_config()
            return True
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        for backup in sorted(
            self.backup_dir.glob("config_*.yaml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            backups.append({
                'name': backup.name,
                'path': str(backup),
                'size': backup.stat().st_size,
                'modified': datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
            })
        return backups

    def get_changes(self) -> List[Dict[str, Any]]:
        return [
            {
                'path': c.path,
                'old_value': c.old_value,
                'new_value': c.new_value,
                'timestamp': c.timestamp,
                'user': c.user,
                'hot_updatable': c.hot_updatable,
            }
            for c in self.changes
        ]

    def discard_changes(self) -> None:
        self._load()
        self.changes.clear()
        logger.info("未保存的变更已丢弃")

    def export_config(self, format: str = 'yaml') -> str:
        if format == 'json':
            return json.dumps(self.config, ensure_ascii=False, indent=2)
        else:
            return yaml.dump(self.config, default_flow_style=False, allow_unicode=True)

    def list_hot_updatable_prefixes(self) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        """返回 (热更新白名单前缀, 不热更新黑名单前缀)，供 API 使用"""
        return HOT_UPDATE_WHITELIST_PREFIXES, NON_HOT_UPDATE_BLACKLIST_PREFIXES


# 全局配置管理器
config_manager = ConfigManager()
