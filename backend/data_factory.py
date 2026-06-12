"""
仿真与压力测试数据工厂

参数化生成合成时序数据，覆盖正常、渐变松动、突发过载、断裂、温度耦合等场景。
支持批量注入 MySQL，也可导出 CSV 用于离线基准测试。

使用示例:
    python data_factory.py --scenario loosening --bolts 100 --days 30
    python data_factory.py --scenario all --bolts 50 --days 7 --frequency 1 --output csv
    python data_factory.py --scenario normal --bolts 10 --days 1 --db-host 127.0.0.1
"""

import argparse
import csv
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Generator, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.utils.config import config


@dataclass
class ScenarioConfig:
    normal_mean: float = 600.0
    normal_std: float = 20.0
    normal_min: float = 400.0
    normal_max: float = 800.0
    temp_mean: float = 25.0
    temp_std: float = 5.0
    daily_cycle_amp: float = 5.0
    loosening_decline_rate: float = 0.002
    overload_ratio: float = 1.3
    fracture_point: float = 0.7
    temp_coefficient: float = -0.5
    noise_level: float = 0.02


@dataclass
class TimeSeriesRecord:
    sensor_id: int
    collector_id: int
    splitter_num: int
    position: str
    ptf: float
    create_time: datetime
    scenario: str = ""
    label: int = 0


SCENARIO_NAMES = [
    "normal",
    "loosening",
    "overload",
    "fracture",
    "temperature_coupling",
    "all",
]

POSITIONS = ["A面", "B面", "C面", "D面"]

LABEL_MAP = {
    0: "正常",
    1: "关注级预警",
    2: "检查级预警",
    3: "紧急级预警",
    4: "故障",
}


def _daily_cycle(n: int) -> np.ndarray:
    return np.sin(np.linspace(0, 2 * np.pi, n))


def _apply_noise(base: np.ndarray, std: float, noise_level: float) -> np.ndarray:
    return base + np.random.randn(len(base)) * std * noise_level


def generate_normal(
    n: int,
    cfg: ScenarioConfig,
) -> Generator[TimeSeriesRecord, None, None]:
    preload = np.random.normal(cfg.normal_mean, cfg.normal_std, n)
    preload += cfg.daily_cycle_amp * _daily_cycle(n)
    preload += np.random.randn(n) * cfg.normal_mean * cfg.noise_level
    yield from _to_records(preload, "normal", 0)


def generate_loosening(
    n: int,
    cfg: ScenarioConfig,
) -> Generator[TimeSeriesRecord, None, None]:
    decline = np.linspace(0, -cfg.normal_mean * cfg.loosening_decline_rate * n, n)
    preload = cfg.normal_mean + decline
    preload += np.random.randn(n) * cfg.normal_std * 0.5
    labels = np.zeros(n, dtype=int)
    labels[n // 2:] = 1
    labels[int(n * 0.75):] = 2
    labels[int(n * 0.9):] = 3
    yield from _to_records(preload, "loosening", labels)


def generate_overload(
    n: int,
    cfg: ScenarioConfig,
) -> Generator[TimeSeriesRecord, None, None]:
    half = n // 2
    preload_normal = np.random.normal(cfg.normal_mean, cfg.normal_std, half)
    overload_mean = cfg.normal_max * cfg.overload_ratio
    preload_over = np.random.normal(overload_mean, cfg.normal_std * 1.5, n - half)
    preload = np.concatenate([preload_normal, preload_over])
    labels = np.zeros(n, dtype=int)
    labels[half:] = 2
    labels[int(n * 0.75):] = 3
    yield from _to_records(preload, "overload", labels)


def generate_sudden_overload(
    n: int,
    cfg: ScenarioConfig,
) -> Generator[TimeSeriesRecord, None, None]:
    spike_point = int(n * 0.6)
    preload = np.random.normal(cfg.normal_mean, cfg.normal_std, n)
    spike_width = max(3, n // 50)
    for i in range(spike_point, min(spike_point + spike_width, n)):
        preload[i] = cfg.normal_max * (cfg.overload_ratio + 0.3 * np.random.rand())
    labels = np.zeros(n, dtype=int)
    labels[spike_point:spike_point + spike_width] = 3
    yield from _to_records(preload, "sudden_overload", labels)


def generate_fracture(
    n: int,
    cfg: ScenarioConfig,
) -> Generator[TimeSeriesRecord, None, None]:
    frac_idx = int(n * cfg.fracture_point)
    preload_before = np.random.normal(cfg.normal_mean, cfg.normal_std, frac_idx)
    preload_after = np.linspace(
        cfg.normal_mean,
        cfg.normal_min * 0.1,
        n - frac_idx,
    )
    preload_after += np.random.randn(n - frac_idx) * 10
    preload = np.concatenate([preload_before, preload_after])
    labels = np.zeros(n, dtype=int)
    labels[frac_idx:] = 4
    yield from _to_records(preload, "fracture", labels)


def generate_temperature_coupling(
    n: int,
    cfg: ScenarioConfig,
) -> Generator[TimeSeriesRecord, None, None]:
    temperature = np.linspace(cfg.temp_mean - 30, cfg.temp_mean + 30, n)
    temperature += np.random.randn(n) * 3
    preload = cfg.normal_mean + cfg.temp_coefficient * (temperature - cfg.temp_mean)
    preload += np.random.randn(n) * cfg.normal_std * 0.5
    labels = np.zeros(n, dtype=int)
    deviation = np.abs(preload - cfg.normal_mean) / cfg.normal_mean
    labels[deviation > 0.1] = 1
    labels[deviation > 0.15] = 2
    yield from _to_records(preload, "temperature_coupling", labels)


SCENARIO_GENERATORS = {
    "normal": generate_normal,
    "loosening": generate_loosening,
    "overload": generate_overload,
    "sudden_overload": generate_sudden_overload,
    "fracture": generate_fracture,
    "temperature_coupling": generate_temperature_coupling,
}


def _to_records(
    preload: np.ndarray,
    scenario: str,
    labels,
) -> Generator[TimeSeriesRecord, None, None]:
    if isinstance(labels, (int, np.integer)):
        labels = np.full(len(preload), labels, dtype=int)
    for i in range(len(preload)):
        yield TimeSeriesRecord(
            sensor_id=0,
            collector_id=0,
            splitter_num=0,
            position="",
            ptf=float(preload[i]),
            create_time=datetime.min,
            scenario=scenario,
            label=int(labels[i]),
        )


@dataclass
class FactoryResult:
    records: List[TimeSeriesRecord] = field(default_factory=list)
    total_rows: int = 0
    scenarios: Dict[str, int] = field(default_factory=dict)
    elapsed_seconds: float = 0.0


class DataFactory:
    def __init__(
        self,
        cfg: Optional[ScenarioConfig] = None,
        seed: Optional[int] = None,
    ):
        self.cfg = cfg or ScenarioConfig()
        if seed is not None:
            np.random.seed(seed)

    def generate(
        self,
        scenario: str,
        bolts: int,
        days: int,
        frequency_minutes: int = 5,
        start_time: Optional[datetime] = None,
    ) -> FactoryResult:
        t0 = time.time()
        n_points = (days * 24 * 60) // frequency_minutes
        if start_time is None:
            start_time = datetime.now() - timedelta(days=days)

        scenarios_to_run = (
            list(SCENARIO_GENERATORS.keys())
            if scenario == "all"
            else [scenario]
        )

        all_records: List[TimeSeriesRecord] = []
        scenario_counts: Dict[str, int] = {}

        for bolt_idx in range(bolts):
            sensor_id = 1001 + bolt_idx
            collector_id = 100 + bolt_idx // 10
            splitter_num = 456
            position = POSITIONS[bolt_idx % len(POSITIONS)]

            chosen_scenario = (
                scenarios_to_run[bolt_idx % len(scenarios_to_run)]
            )

            gen_func = SCENARIO_GENERATORS[chosen_scenario]
            records = list(gen_func(n_points, self.cfg))

            for j, rec in enumerate(records):
                rec.sensor_id = sensor_id
                rec.collector_id = collector_id
                rec.splitter_num = splitter_num
                rec.position = position
                rec.create_time = start_time + timedelta(
                    minutes=j * frequency_minutes
                )
                all_records.append(rec)

            scenario_counts[chosen_scenario] = (
                scenario_counts.get(chosen_scenario, 0) + n_points
            )

        elapsed = time.time() - t0
        return FactoryResult(
            records=all_records,
            total_rows=len(all_records),
            scenarios=scenario_counts,
            elapsed_seconds=elapsed,
        )


class MySQLInjector:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        batch_size: int = 5000,
    ):
        db_config = config.get("database", {})
        self.host = host or db_config.get("host", "127.0.0.1")
        self.port = port or db_config.get("port", 3306)
        self.user = user or db_config.get("user", "root")
        self.password = password or db_config.get("password", "")
        self.database = database or db_config.get("database", "bolt_preload")
        self.batch_size = batch_size
        self._engine = None

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        from sqlalchemy import create_engine

        url = (
            f"mysql+pymysql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?charset=utf8mb4"
        )
        self._engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        return self._engine

    def inject(self, result: FactoryResult) -> Tuple[int, float]:
        engine = self._get_engine()
        t0 = time.time()
        inserted = 0

        from sqlalchemy import text

        with engine.connect() as conn:
            for offset in range(0, len(result.records), self.batch_size):
                batch = result.records[offset : offset + self.batch_size]
                values_clause = ", ".join(
                    f"({rec.sensor_id}, {rec.collector_id}, "
                    f"{rec.splitter_num}, '{rec.position}', "
                    f"{rec.ptf:.4f}, "
                    f"'{rec.create_time.strftime('%Y-%m-%d %H:%M:%S')}')"
                    for rec in batch
                )
                sql = text(
                    f"INSERT INTO sc_bolt_data "
                    f"(sensor_id, collector_id, splitter_num, position, ptf, create_time) "
                    f"VALUES {values_clause}"
                )
                conn.execute(sql)
                conn.commit()
                inserted += len(batch)

        elapsed = time.time() - t0
        return inserted, elapsed

    def close(self):
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


def export_csv(
    result: FactoryResult,
    filepath: str,
) -> str:
    dirpath = os.path.dirname(filepath)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sensor_id",
            "collector_id",
            "splitter_num",
            "position",
            "ptf",
            "create_time",
            "scenario",
            "label",
            "label_name",
        ])
        for rec in result.records:
            writer.writerow([
                rec.sensor_id,
                rec.collector_id,
                rec.splitter_num,
                rec.position,
                f"{rec.ptf:.4f}",
                rec.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                rec.scenario,
                rec.label,
                LABEL_MAP.get(rec.label, "未知"),
            ])

    return filepath


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="仿真与压力测试数据工厂 - 参数化生成合成时序数据",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        choices=SCENARIO_NAMES,
        help="数据场景 (default: all)",
    )
    parser.add_argument(
        "--bolts",
        type=int,
        default=10,
        help="螺栓/节点数量 (default: 10)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="时间跨度（天） (default: 7)",
    )
    parser.add_argument(
        "--frequency",
        type=int,
        default=5,
        help="采样频率（分钟） (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="mysql",
        choices=["mysql", "csv", "both"],
        help="输出方式 (default: mysql)",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default=None,
        help="CSV 文件路径 (default: ./data/factory_output.csv)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子 (default: 42)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="MySQL 批量插入大小 (default: 5000)",
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default=None,
        help="MySQL 主机 (default: 从配置文件读取)",
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=None,
        help="MySQL 端口 (default: 从配置文件读取)",
    )
    parser.add_argument(
        "--db-user",
        type=str,
        default=None,
        help="MySQL 用户名 (default: 从配置文件读取)",
    )
    parser.add_argument(
        "--db-password",
        type=str,
        default=None,
        help="MySQL 密码 (default: 从配置文件读取)",
    )
    parser.add_argument(
        "--db-name",
        type=str,
        default=None,
        help="MySQL 数据库名 (default: 从配置文件读取)",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 60)
    print("仿真与压力测试数据工厂")
    print("=" * 60)
    print(f"  场景:       {args.scenario}")
    print(f"  螺栓数:     {args.bolts}")
    print(f"  时间跨度:   {args.days} 天")
    print(f"  采样频率:   每 {args.frequency} 分钟")
    print(f"  随机种子:   {args.seed}")
    print(f"  输出方式:   {args.output}")

    n_points = (args.days * 24 * 60) // args.frequency
    total_estimate = args.bolts * n_points
    print(f"  预计行数:   ~{total_estimate:,}")
    print("-" * 60)

    factory = DataFactory(seed=args.seed)
    result = factory.generate(
        scenario=args.scenario,
        bolts=args.bolts,
        days=args.days,
        frequency_minutes=args.frequency,
    )

    print(f"  生成完成:   {result.total_rows:,} 行")
    print(f"  耗时:       {result.elapsed_seconds:.2f}s")
    print(f"  场景分布:")
    for name, count in result.scenarios.items():
        print(f"    {name}: {count:,} 点")
    print("-" * 60)

    if args.output in ("mysql", "both"):
        print("  正在注入 MySQL ...")
        injector = MySQLInjector(
            host=args.db_host,
            port=args.db_port,
            user=args.db_user,
            password=args.db_password,
            database=args.db_name,
            batch_size=args.batch_size,
        )
        try:
            inserted, inject_time = injector.inject(result)
            print(f"  注入完成:   {inserted:,} 行, 耗时 {inject_time:.2f}s")
            rate = inserted / inject_time if inject_time > 0 else 0
            print(f"  写入速率:   {rate:,.0f} 行/秒")
        except Exception as e:
            print(f"  注入失败:   {e}")
            print("  提示: 请确保 MySQL 服务已启动且 sc_bolt_data 表已创建")
        finally:
            injector.close()

    if args.output in ("csv", "both"):
        csv_path = args.csv_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "factory_output.csv",
        )
        print(f"  正在导出 CSV -> {csv_path} ...")
        export_csv(result, csv_path)
        file_size = os.path.getsize(csv_path)
        print(f"  导出完成:   {file_size / 1024 / 1024:.2f} MB")

    print("=" * 60)
    print("数据工厂运行结束")


if __name__ == "__main__":
    main()
