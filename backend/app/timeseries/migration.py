"""
MySQL 历史数据迁移工具

将 MySQL 中的历史数据批量导入时序数据库。

支持功能：
- 按时间范围迁移
- 按传感器分批迁移
- 断点续传（记录迁移进度）
- 迁移后自动执行降采样
- 迁移进度监控
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
from dataclasses import dataclass, field

from app.utils.database import get_db, BoltData
from app.timeseries.base import TimeSeriesDataPoint, TimeSeriesRepository
from app.timeseries.factory import get_timeseries_repository


@dataclass
class MigrationProgress:
    """
    迁移进度记录

    Attributes:
        sensor_id: 传感器ID
        last_time: 已迁移的最后时间
        total_count: 已迁移总条数
        start_time: 迁移开始时间
        status: 状态 (pending/running/completed/failed)
        error_message: 错误信息
    """
    sensor_id: str
    last_time: Optional[datetime] = None
    total_count: int = 0
    start_time: Optional[datetime] = None
    status: str = "pending"
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'last_time': self.last_time.isoformat() if self.last_time else None,
            'total_count': self.total_count,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'status': self.status,
            'error_message': self.error_message,
        }


@dataclass
class MigrationResult:
    """
    迁移结果汇总

    Attributes:
        total_sensors: 总传感器数
        completed_sensors: 已完成传感器数
        total_records: 总迁移记录数
        failed_sensors: 失败的传感器列表
        start_time: 开始时间
        end_time: 结束时间
    """
    total_sensors: int = 0
    completed_sensors: int = 0
    total_records: int = 0
    failed_sensors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_sensors': self.total_sensors,
            'completed_sensors': self.completed_sensors,
            'total_records': self.total_records,
            'failed_sensors': self.failed_sensors,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration.total_seconds() if self.duration else None,
        }


class MySQLToTimeseriesMigrator:
    """
    MySQL 到时序数据库的数据迁移器

    将 MySQL 中的 sc_bolt_data 表数据迁移到时序数据库。
    """

    def __init__(
        self,
        repository: Optional[TimeSeriesRepository] = None,
        batch_size: int = 5000,
        progress_file: Optional[str] = None,
    ):
        """
        初始化迁移器

        Args:
            repository: 时序数据库仓库，默认使用全局实例
            batch_size: 每批迁移的记录数
            progress_file: 进度保存文件路径
        """
        self.repository = repository or get_timeseries_repository()
        if self.repository is None:
            raise ValueError("时序数据库未启用，无法进行迁移")

        self.batch_size = batch_size
        self.progress_file = progress_file or "./data/migration_progress.json"
        self._progress: Dict[str, MigrationProgress] = {}
        self._load_progress()

    # ---------- 进度管理 ----------

    def _load_progress(self) -> None:
        """加载迁移进度"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for sensor_id, prog_data in data.items():
                    self._progress[sensor_id] = MigrationProgress(
                        sensor_id=sensor_id,
                        last_time=(
                            datetime.fromisoformat(prog_data['last_time'])
                            if prog_data.get('last_time')
                            else None
                        ),
                        total_count=prog_data.get('total_count', 0),
                        start_time=(
                            datetime.fromisoformat(prog_data['start_time'])
                            if prog_data.get('start_time')
                            else None
                        ),
                        status=prog_data.get('status', 'pending'),
                        error_message=prog_data.get('error_message', ''),
                    )

            logger.info(f"已加载迁移进度: {len(self._progress)} 个传感器")
        except Exception as e:
            logger.error(f"加载迁移进度失败: {e}")

    def _save_progress(self) -> None:
        """保存迁移进度"""
        try:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)

            data = {
                sensor_id: prog.to_dict()
                for sensor_id, prog in self._progress.items()
            }

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存迁移进度失败: {e}")

    def _get_progress(self, sensor_id: str) -> MigrationProgress:
        """获取传感器的迁移进度"""
        if sensor_id not in self._progress:
            self._progress[sensor_id] = MigrationProgress(sensor_id=sensor_id)
        return self._progress[sensor_id]

    # ---------- 迁移方法 ----------

    def migrate_all(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sensor_ids: Optional[List[str]] = None,
        run_downsampling: bool = True,
    ) -> MigrationResult:
        """
        迁移所有传感器数据

        Args:
            start_date: 迁移起始时间
            end_date: 迁移结束时间
            sensor_ids: 指定传感器ID列表，None表示全部
            run_downsampling: 迁移完成后是否执行降采样

        Returns:
            迁移结果
        """
        result = MigrationResult(start_time=datetime.now())

        try:
            if sensor_ids is None:
                sensor_ids = self._list_mysql_sensors()

            result.total_sensors = len(sensor_ids)
            logger.info(f"开始迁移，共 {len(sensor_ids)} 个传感器")

            for i, sensor_id in enumerate(sensor_ids, 1):
                logger.info(
                    f"迁移进度: {i}/{len(sensor_ids)} - 传感器 {sensor_id}"
                )

                try:
                    count = self.migrate_sensor(
                        sensor_id=sensor_id,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    result.completed_sensors += 1
                    result.total_records += count
                    logger.info(
                        f"传感器 {sensor_id} 迁移完成，共 {count} 条记录"
                    )
                except Exception as e:
                    result.failed_sensors.append(sensor_id)
                    logger.error(f"传感器 {sensor_id} 迁移失败: {e}")

            if run_downsampling and result.total_records > 0:
                logger.info("开始执行降采样...")
                from app.timeseries.downsampling import DownsamplingEngine, AggregationLevel

                engine = DownsamplingEngine(self.repository)
                engine.run_full()
                logger.info("降采样完成")

        except Exception as e:
            logger.error(f"迁移过程出错: {e}")
        finally:
            result.end_time = datetime.now()
            self._save_progress()

        return result

    def migrate_sensor(
        self,
        sensor_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        迁移单个传感器的数据

        Args:
            sensor_id: 传感器ID
            start_date: 起始时间
            end_date: 结束时间

        Returns:
            迁移的记录数
        """
        progress = self._get_progress(sensor_id)
        progress.status = "running"
        progress.start_time = progress.start_time or datetime.now()

        total_count = 0

        try:
            current_start = start_date or progress.last_time

            while True:
                rows = self._fetch_mysql_batch(
                    sensor_id=sensor_id,
                    start_time=current_start,
                    end_time=end_date,
                    limit=self.batch_size,
                )

                if not rows:
                    break

                points = [self._row_to_datapoint(row) for row in rows]
                self.repository.write_batch(points)

                batch_count = len(rows)
                total_count += batch_count
                progress.total_count += batch_count
                progress.last_time = rows[-1].create_time

                self._save_progress()

                current_start = rows[-1].create_time

                logger.debug(
                    f"传感器 {sensor_id}: 已迁移 {total_count} 条, "
                    f"当前时间 {progress.last_time}"
                )

                if batch_count < self.batch_size:
                    break

            progress.status = "completed"
            return total_count

        except Exception as e:
            progress.status = "failed"
            progress.error_message = str(e)
            raise

    # ---------- 内部方法 ----------

    def _list_mysql_sensors(self) -> List[str]:
        """从 MySQL 获取所有传感器ID"""
        with get_db() as db:
            from sqlalchemy import func

            result = db.query(
                BoltData.sensor_id
            ).distinct().all()

            return [str(row.sensor_id) for row in result]

    def _fetch_mysql_batch(
        self,
        sensor_id: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
    ) -> List:
        """从 MySQL 批量获取数据"""
        with get_db() as db:
            query = db.query(BoltData).filter(
                BoltData.sensor_id == sensor_id
            )

            if start_time:
                query = query.filter(BoltData.create_time > start_time)

            if end_time:
                query = query.filter(BoltData.create_time <= end_time)

            query = query.order_by(BoltData.create_time.asc()).limit(limit)

            return query.all()

    def _row_to_datapoint(self, row: BoltData) -> TimeSeriesDataPoint:
        """将 MySQL 行转换为时序数据点"""
        fields = {}
        if row.temperature is not None:
            fields['temperature'] = row.temperature
        if row.humidity is not None:
            fields['humidity'] = row.humidity
        if row.vibration is not None:
            fields['vibration'] = row.vibration
        if row.torque is not None:
            fields['torque'] = row.torque
        if row.pressure is not None:
            fields['pressure'] = row.pressure

        tags = {}
        if row.collector_id is not None:
            tags['collector_id'] = str(row.collector_id)
        if row.splitter_num is not None:
            tags['splitter_num'] = str(row.splitter_num)
        if row.position:
            tags['position'] = row.position

        return TimeSeriesDataPoint(
            timestamp=row.create_time,
            sensor_id=str(row.sensor_id),
            value=row.ptf if row.ptf is not None else 0.0,
            fields=fields,
            tags=tags,
        )

    # ---------- 状态查询 ----------

    def get_progress_summary(self) -> Dict[str, Any]:
        """获取迁移进度摘要"""
        total = len(self._progress)
        completed = sum(
            1 for p in self._progress.values() if p.status == 'completed')
        running = sum(
            1 for p in self._progress.values() if p.status == 'running')
        failed = sum(
            1 for p in self._progress.values() if p.status == 'failed')
        pending = sum(
            1 for p in self._progress.values() if p.status == 'pending')
        total_records = sum(p.total_count for p in self._progress.values())

        return {
            'total_sensors': total,
            'completed': completed,
            'running': running,
            'failed': failed,
            'pending': pending,
            'total_records': total_records,
        }

    def reset_progress(self, sensor_id: Optional[str] = None) -> None:
        """重置迁移进度"""
        if sensor_id:
            if sensor_id in self._progress:
                del self._progress[sensor_id]
                logger.info(f"已重置传感器 {sensor_id} 的迁移进度")
        else:
            self._progress.clear()
            logger.info("已重置所有迁移进度")

        self._save_progress()
