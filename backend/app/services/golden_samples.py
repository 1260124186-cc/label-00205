"""
金样本集服务（Golden Samples Service）

提供回归测试的基准数据集与期望预测结果（golden labels），
支持版本化管理、基线比较、持久化存储与加载。

核心功能:
1. 固定 seed 生成可复现的基准数据集
2. 生成 golden labels（期望预测结果）
3. 金样本版本注册 / 查询 / 下载 / 基线设置
4. 与回归服务协同，计算 accuracy/F1 等指标

场景参数（与 data_factory.SCENARIO_GENERATORS 一致）:
- normal:             正常工况，预紧力围绕均值波动
- loosening:          渐变松动，预紧力持续下降
- sudden_overload:    突发过载，短时尖峰
- overload:           持续过载，长期高于上限
- fracture:           断裂，预紧力骤降
- temperature_coupling: 温度耦合，随温度变化漂移
"""

import csv
import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
from loguru import logger

from data_factory import (
    DataFactory,
    ScenarioConfig,
    TimeSeriesRecord,
    FactoryResult,
    SCENARIO_NAMES,
    SCENARIO_GENERATORS,
    LABEL_MAP,
)
from app.utils.config import config
from app.utils.database import get_db


GOLDEN_DEFAULT_SEED = 20260620
GOLDEN_DEFAULT_BOLTS = 24
GOLDEN_DEFAULT_DAYS = 14
GOLDEN_DEFAULT_FREQ_MINUTES = 30

STATUS_CODES = [0, 1, 2, 3, 4]


@dataclass
class GoldenSampleSpec:
    """
    金样本生成规格（决定样本内容的唯一标识）

    相同 spec + seed 必然生成相同样本，用于校验版本完整性。
    """
    scenario: str
    bolts: int
    days: int
    frequency_minutes: int
    seed: int
    scenario_config: Optional[Dict[str, Any]] = None


@dataclass
class GoldenSampleMetrics:
    """
    基线模型在金样本上的指标快照

    注册新版本时，使用当前激活模型跑一遍并记录为基线。
    """
    accuracy: float = 0.0
    macro_f1: float = 0.0
    weighted_f1: float = 0.0
    per_class_f1: Dict[str, float] = field(default_factory=dict)
    per_class_precision: Dict[str, float] = field(default_factory=dict)
    per_class_recall: Dict[str, float] = field(default_factory=dict)
    confusion_matrix: List[List[int]] = field(default_factory=list)
    total_samples: int = 0
    evaluation_model_version: str = ""
    evaluation_timestamp: str = ""


@dataclass
class GoldenSampleVersion:
    """
    金样本版本元数据（存储在 JSON + 数据库）
    """
    version: str
    spec: GoldenSampleSpec
    metrics: GoldenSampleMetrics
    data_hash: str
    data_path: str
    labels_path: str
    created_at: str
    created_by: str
    description: str = ""
    is_baseline: bool = False


class GoldenSamplesService:
    """
    金样本集服务

    存储结构:
        data/golden_samples/{version}/
            samples.csv       - 时序数据（含 sensor_id, ptf, create_time, label）
            golden_labels.csv - golden labels（含每个螺栓/窗口的期望预测）
            meta.json         - 版本元数据（spec + metrics + hash）
    """

    def __init__(self, storage_root: Optional[str] = None):
        self.storage_root = Path(
            storage_root
            or config.get("golden_samples.storage_root")
            or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "..", "data", "golden_samples",
            )
        ).resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self._ensure_table()
        logger.info(
            f"金样本服务初始化完成: 存储根目录={self.storage_root}"
        )

    # =============================================================
    # 数据库表
    # =============================================================

    def _ensure_table(self):
        """确保 sc_golden_samples 表存在"""
        try:
            with get_db() as db:
                if db is None:
                    return
                db.execute("""
                    CREATE TABLE IF NOT EXISTS sc_golden_samples (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        version VARCHAR(64) NOT NULL UNIQUE,
                        spec_json TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        data_hash VARCHAR(128) NOT NULL,
                        data_path VARCHAR(512) NOT NULL,
                        labels_path VARCHAR(512) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR(128) DEFAULT 'system',
                        description VARCHAR(512),
                        is_baseline BOOLEAN NOT NULL DEFAULT FALSE,
                        INDEX idx_baseline (is_baseline)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                db.commit()
        except Exception as e:
            logger.debug(f"创建 sc_golden_samples 表失败（可能 SQLite）: {e}")
            try:
                with get_db() as db:
                    if db is None:
                        return
                    db.execute("""
                        CREATE TABLE IF NOT EXISTS sc_golden_samples (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            version TEXT NOT NULL UNIQUE,
                            spec_json TEXT NOT NULL,
                            metrics_json TEXT NOT NULL,
                            data_hash TEXT NOT NULL,
                            data_path TEXT NOT NULL,
                            labels_path TEXT NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            created_by TEXT DEFAULT 'system',
                            description TEXT,
                            is_baseline INTEGER NOT NULL DEFAULT 0
                        )
                    """)
                    db.commit()
            except Exception as e2:
                logger.debug(f"SQLite 建表也失败，跳过: {e2}")

    # =============================================================
    # 生成金样本
    # =============================================================

    def generate_golden_samples(
        self,
        scenario: str = "all",
        bolts: int = GOLDEN_DEFAULT_BOLTS,
        days: int = GOLDEN_DEFAULT_DAYS,
        frequency_minutes: int = GOLDEN_DEFAULT_FREQ_MINUTES,
        seed: int = GOLDEN_DEFAULT_SEED,
        scenario_config_override: Optional[Dict[str, Any]] = None,
    ) -> Tuple[FactoryResult, GoldenSampleSpec]:
        """
        生成固定 seed 的金样本原始时序数据

        Args:
            scenario:               场景名（normal/loosening/.../all）
            bolts:                  螺栓数量
            days:                   时间跨度（天）
            frequency_minutes:      采样间隔（分钟）
            seed:                   随机种子（默认 20260620）
            scenario_config_override: 可选，覆盖 ScenarioConfig 字段

        Returns:
            (FactoryResult, GoldenSampleSpec)
        """
        if scenario not in SCENARIO_NAMES:
            raise ValueError(
                f"未知场景 {scenario}，可选值: {SCENARIO_NAMES}"
            )

        cfg = ScenarioConfig()
        if scenario_config_override:
            for k, v in scenario_config_override.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

        from datetime import datetime as _dt

        factory = DataFactory(cfg=cfg, seed=seed)
        result = factory.generate(
            scenario=scenario,
            bolts=bolts,
            days=days,
            frequency_minutes=frequency_minutes,
            start_time=_dt(2026, 1, 1, 0, 0, 0),
        )

        spec = GoldenSampleSpec(
            scenario=scenario,
            bolts=bolts,
            days=days,
            frequency_minutes=frequency_minutes,
            seed=seed,
            scenario_config=asdict(cfg) if scenario_config_override else None,
        )

        logger.info(
            f"金样本生成完成: scenario={scenario}, bolts={bolts}, "
            f"days={days}, rows={result.total_rows}, seed={seed}"
        )
        return result, spec

    # =============================================================
    # 生成 golden labels（期望预测结果）
    # =============================================================

    def generate_golden_labels(
        self,
        factory_result: FactoryResult,
        window_size: int = 100,
        stride: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        基于场景内置标签生成 golden labels

        对每个螺栓按滑动窗口切分，取窗口内**最后一个点的标签**作为
        该窗口的期望预测（golden label）。这样与 LSTM 分类器的
        "基于窗口预测当前状态" 口径完全对齐。

        Args:
            factory_result: generate_golden_samples 返回的 FactoryResult
            window_size:    窗口大小（与训练时一致，默认100）
            stride:         滑窗步长（默认50）

        Returns:
            [
              {
                "bolt_id": "1001",
                "window_start": idx,
                "window_end": idx + window_size,
                "preload_values": [...],  # 窗口内值
                "golden_label": 0-4,      # 期望状态码
                "golden_label_name": "正常",
                "scenario": "normal",
              },
              ...
            ]
        """
        records: List[TimeSeriesRecord] = factory_result.records
        by_bolt: Dict[int, List[TimeSeriesRecord]] = {}
        for r in records:
            by_bolt.setdefault(r.sensor_id, []).append(r)

        labels: List[Dict[str, Any]] = []
        for bolt_id, recs in by_bolt.items():
            recs_sorted = sorted(recs, key=lambda x: x.create_time)
            values = [r.ptf for r in recs_sorted]
            lbls = [r.label for r in recs_sorted]
            scenario = recs_sorted[0].scenario if recs_sorted else ""

            n = len(values)
            for i in range(0, n - window_size + 1, stride):
                window_values = values[i : i + window_size]
                golden_label = lbls[i + window_size - 1]
                labels.append({
                    "bolt_id": str(bolt_id),
                    "window_start": i,
                    "window_end": i + window_size,
                    "preload_values": [round(v, 4) for v in window_values],
                    "golden_label": int(golden_label),
                    "golden_label_name": LABEL_MAP.get(int(golden_label), "未知"),
                    "scenario": scenario,
                })

        logger.info(
            f"Golden labels 生成完成: 窗口数={len(labels)}, "
            f"window_size={window_size}, stride={stride}"
        )
        return labels

    # =============================================================
    # 持久化版本
    # =============================================================

    def register_version(
        self,
        spec: GoldenSampleSpec,
        factory_result: FactoryResult,
        golden_labels: List[Dict[str, Any]],
        metrics: GoldenSampleMetrics,
        description: str = "",
        created_by: str = "system",
    ) -> GoldenSampleVersion:
        """
        注册一个新的金样本版本

        1. 生成下一个版本号 v1.0.0 / v1.0.1 / ...
        2. 写入 samples.csv、golden_labels.csv、meta.json
        3. 计算数据 hash 做完整性校验
        4. 写入数据库
        5. 若当前无基线版本，自动设为基线
        """
        version = self._next_version()
        version_dir = self.storage_root / version
        version_dir.mkdir(parents=True, exist_ok=True)

        samples_path = version_dir / "samples.csv"
        labels_path = version_dir / "golden_labels.csv"
        meta_path = version_dir / "meta.json"

        self._write_samples_csv(factory_result, samples_path)
        self._write_golden_labels_csv(golden_labels, labels_path)

        data_hash = self._compute_data_hash(samples_path, labels_path)

        metrics.evaluation_timestamp = datetime.now().isoformat()

        version_obj = GoldenSampleVersion(
            version=version,
            spec=spec,
            metrics=metrics,
            data_hash=data_hash,
            data_path=str(samples_path),
            labels_path=str(labels_path),
            created_at=datetime.now().isoformat(),
            created_by=created_by,
            description=description,
            is_baseline=False,
        )

        meta = {
            "version": version,
            "spec": asdict(spec),
            "metrics": asdict(metrics),
            "data_hash": data_hash,
            "created_at": version_obj.created_at,
            "created_by": created_by,
            "description": description,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        self._persist_to_db(version_obj)

        baseline = self.get_baseline_version()
        if baseline is None:
            self.set_baseline_version(version)
            version_obj.is_baseline = True

        logger.info(
            f"金样本版本已注册: {version}, "
            f"样本行数={factory_result.total_rows}, "
            f"label窗口数={len(golden_labels)}, hash={data_hash[:12]}..."
        )
        return version_obj

    def _next_version(self) -> str:
        """获取下一个版本号"""
        versions = self.list_versions()
        if not versions:
            return "v1.0.0"
        latest = versions[0]["version"]
        if latest.startswith("v"):
            parts = latest[1:].split(".")
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"v{major}.{minor}.{patch + 1}"
        return "v1.0.0"

    def _write_samples_csv(
        self, result: FactoryResult, path: Path
    ) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sensor_id", "collector_id", "splitter_num", "position",
                "ptf", "create_time", "scenario", "label",
            ])
            for r in result.records:
                writer.writerow([
                    r.sensor_id, r.collector_id, r.splitter_num, r.position,
                    f"{r.ptf:.4f}",
                    r.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    r.scenario, r.label,
                ])

    def _write_golden_labels_csv(
        self, labels: List[Dict[str, Any]], path: Path
    ) -> None:
        if not labels:
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(
                    "bolt_id,window_start,window_end,"
                    "golden_label,golden_label_name,scenario,"
                    "preload_values\n"
                )
            return
        keys = list(labels[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for lbl in labels:
                row = []
                for k in keys:
                    v = lbl[k]
                    if isinstance(v, list):
                        v = json.dumps(v, ensure_ascii=False)
                    row.append(v)
                writer.writerow(row)

    @staticmethod
    def _compute_data_hash(*paths: Path) -> str:
        """计算多文件联合 MD5 用于完整性校验"""
        md5 = hashlib.md5()
        for p in paths:
            if not p.exists():
                continue
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
        return md5.hexdigest()

    def _persist_to_db(self, version_obj: GoldenSampleVersion) -> None:
        try:
            with get_db() as db:
                if db is None:
                    return
                spec_json = json.dumps(asdict(version_obj.spec), ensure_ascii=False)
                metrics_json = json.dumps(asdict(version_obj.metrics), ensure_ascii=False)
                try:
                    db.execute(
                        """
                        INSERT INTO sc_golden_samples
                        (version, spec_json, metrics_json, data_hash,
                         data_path, labels_path, created_by, description, is_baseline)
                        VALUES (:v, :s, :m, :h, :dp, :lp, :cb, :d, :b)
                        """,
                        {
                            "v": version_obj.version,
                            "s": spec_json,
                            "m": metrics_json,
                            "h": version_obj.data_hash,
                            "dp": version_obj.data_path,
                            "lp": version_obj.labels_path,
                            "cb": version_obj.created_by,
                            "d": version_obj.description,
                            "b": 1 if version_obj.is_baseline else 0,
                        },
                    )
                    db.commit()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"写入 sc_golden_samples 失败: {e}")

    # =============================================================
    # 查询与加载
    # =============================================================

    def list_versions(self) -> List[Dict[str, Any]]:
        """列出所有版本（按版本号倒序，数据库优先，文件系统兜底）"""
        results: List[Dict[str, Any]] = []
        try:
            with get_db() as db:
                if db is not None:
                    rows = db.execute(
                        "SELECT version, spec_json, metrics_json, data_hash, "
                        "created_at, created_by, description, is_baseline "
                        "FROM sc_golden_samples ORDER BY id DESC"
                    ).fetchall()
                    for row in rows:
                        results.append({
                            "version": row[0],
                            "spec": json.loads(row[1]) if row[1] else None,
                            "metrics": json.loads(row[2]) if row[2] else None,
                            "data_hash": row[3],
                            "created_at": str(row[4]),
                            "created_by": row[5],
                            "description": row[6],
                            "is_baseline": bool(row[7]),
                        })
        except Exception:
            pass

        if not results:
            for p in sorted(self.storage_root.glob("v*"), reverse=True):
                meta_path = p / "meta.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        meta.setdefault("is_baseline", False)
                        results.append(meta)
                    except Exception:
                        pass

        return results

    def get_version(self, version: str) -> Optional[GoldenSampleVersion]:
        """加载指定版本"""
        vdir = self.storage_root / version
        meta_path = vdir / "meta.json"
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            logger.warning(f"读取金样本 meta.json 失败 {version}: {e}")
            return None

        try:
            spec_dict = meta["spec"]
            spec = GoldenSampleSpec(
                scenario=spec_dict["scenario"],
                bolts=spec_dict["bolts"],
                days=spec_dict["days"],
                frequency_minutes=spec_dict["frequency_minutes"],
                seed=spec_dict["seed"],
                scenario_config=spec_dict.get("scenario_config"),
            )
            m = meta.get("metrics", {}) or {}
            metrics = GoldenSampleMetrics(
                accuracy=float(m.get("accuracy", 0.0)),
                macro_f1=float(m.get("macro_f1", 0.0)),
                weighted_f1=float(m.get("weighted_f1", 0.0)),
                per_class_f1=m.get("per_class_f1", {}),
                per_class_precision=m.get("per_class_precision", {}),
                per_class_recall=m.get("per_class_recall", {}),
                confusion_matrix=m.get("confusion_matrix", []),
                total_samples=int(m.get("total_samples", 0)),
                evaluation_model_version=m.get("evaluation_model_version", ""),
                evaluation_timestamp=m.get("evaluation_timestamp", ""),
            )
            return GoldenSampleVersion(
                version=meta["version"],
                spec=spec,
                metrics=metrics,
                data_hash=meta["data_hash"],
                data_path=str(vdir / "samples.csv"),
                labels_path=str(vdir / "golden_labels.csv"),
                created_at=meta.get("created_at", ""),
                created_by=meta.get("created_by", "system"),
                description=meta.get("description", ""),
                is_baseline=bool(meta.get("is_baseline", False)),
            )
        except Exception as e:
            logger.warning(f"解析金样本版本 {version} 失败: {e}")
            return None

    def get_baseline_version(self) -> Optional[GoldenSampleVersion]:
        """获取基线版本（is_baseline=True）"""
        try:
            with get_db() as db:
                if db is not None:
                    row = db.execute(
                        "SELECT version FROM sc_golden_samples "
                        "WHERE is_baseline = 1 ORDER BY id DESC LIMIT 1"
                    ).fetchone()
                    if row:
                        return self.get_version(row[0])
        except Exception:
            pass
        for v in self.list_versions():
            if v.get("is_baseline"):
                return self.get_version(v["version"])
        return None

    def set_baseline_version(self, version: str) -> bool:
        """设置基线版本"""
        v_obj = self.get_version(version)
        if v_obj is None:
            return False
        try:
            with get_db() as db:
                if db is not None:
                    db.execute("UPDATE sc_golden_samples SET is_baseline = 0")
                    db.execute(
                        "UPDATE sc_golden_samples SET is_baseline = 1 WHERE version = :v",
                        {"v": version},
                    )
                    db.commit()
        except Exception:
            pass

        meta_path = self.storage_root / version / "meta.json"
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["is_baseline"] = True
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        for p in self.storage_root.glob("v*/meta.json"):
            if p.parent.name != version:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    if m.get("is_baseline"):
                        m["is_baseline"] = False
                        with open(p, "w", encoding="utf-8") as f:
                            json.dump(m, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        logger.info(f"已设置金样本基线版本: {version}")
        return True

    def load_golden_labels(
        self, version: str
    ) -> Optional[List[Dict[str, Any]]]:
        """加载指定版本的 golden labels"""
        v = self.get_version(version)
        if v is None:
            return None
        labels_path = Path(v.labels_path)
        if not labels_path.exists():
            return None
        results = []
        with open(labels_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if "preload_values" in row and row["preload_values"]:
                        row["preload_values"] = json.loads(row["preload_values"])
                    else:
                        row["preload_values"] = []
                    row["golden_label"] = int(row["golden_label"])
                    row["window_start"] = int(row["window_start"])
                    row["window_end"] = int(row["window_end"])
                    results.append(row)
                except Exception:
                    continue
        return results

    # =============================================================
    # 场景参数文档化输出
    # =============================================================

    def get_scenario_parameter_docs(self) -> Dict[str, Any]:
        """
        返回 data_factory 各场景的参数说明（用于 API 文档自动生成）

        包含:
        - 每个场景的名称、描述、核心参数
        - ScenarioConfig 各字段默认值与含义
        - 标签含义（0-4）
        """
        scenario_descs = {
            "normal": {
                "description": "正常工况，预紧力围绕均值 600kN 正态波动，叠加日周期 sin 波动",
                "parameters_used": ["normal_mean", "normal_std", "daily_cycle_amp", "noise_level"],
                "label_distribution": "全部 0（正常）",
            },
            "loosening": {
                "description": "渐变松动，预紧力线性下降，按 50%/75%/90% 分位依次标 1/2/3",
                "parameters_used": ["normal_mean", "normal_std", "loosening_decline_rate", "noise_level"],
                "label_distribution": "前50%=0, 25%=1(关注), 15%=2(检查), 10%=3(紧急)",
            },
            "sudden_overload": {
                "description": "突发过载，60% 位置处出现短时尖峰",
                "parameters_used": ["normal_mean", "normal_std", "overload_ratio", "normal_max"],
                "label_distribution": "大部分=0，尖峰窗口=3(紧急)",
            },
            "overload": {
                "description": "持续过载，后半段预紧力长期高于正常上限",
                "parameters_used": ["normal_mean", "normal_std", "overload_ratio", "normal_max"],
                "label_distribution": "前半=0，25%=2(检查)，25%=3(紧急)",
            },
            "fracture": {
                "description": "断裂，70% 位置处预紧力骤降到接近 0",
                "parameters_used": ["normal_mean", "normal_std", "fracture_point", "normal_min"],
                "label_distribution": "前70%=0，后30%=4(故障)",
            },
            "temperature_coupling": {
                "description": "温度耦合，温度从 -5°C 线性升到 55°C，预紧力按系数漂移",
                "parameters_used": ["normal_mean", "normal_std", "temp_mean", "temp_coefficient", "noise_level"],
                "label_distribution": "偏差>10%→1(关注)，>15%→2(检查)",
            },
            "all": {
                "description": "混合模式，每个螺栓循环分配上述各场景（按 bolts 数轮转）",
                "parameters_used": "所有场景参数",
                "label_distribution": "各场景按比例混合",
            },
        }

        config_params = []
        for field_name, field_default in ScenarioConfig().__dict__.items():
            config_params.append({
                "field": field_name,
                "default": field_default,
                "type": type(field_default).__name__,
            })

        labels_doc = [
            {"code": k, "name": v} for k, v in LABEL_MAP.items()
        ]

        return {
            "scenarios": scenario_descs,
            "scenario_config_fields": config_params,
            "status_labels": labels_doc,
            "recommended_seed": GOLDEN_DEFAULT_SEED,
            "recommended_bolts": GOLDEN_DEFAULT_BOLTS,
            "recommended_days": GOLDEN_DEFAULT_DAYS,
            "recommended_frequency_minutes": GOLDEN_DEFAULT_FREQ_MINUTES,
            "available_scenarios": SCENARIO_NAMES,
        }


_golden_samples_service: Optional[GoldenSamplesService] = None


def get_golden_samples_service() -> GoldenSamplesService:
    """获取金样本服务单例"""
    global _golden_samples_service
    if _golden_samples_service is None:
        _golden_samples_service = GoldenSamplesService()
    return _golden_samples_service
