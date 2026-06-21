"""
时序数据归档服务
================
核心职责：
1. 按月分区键管理（自动创建/更新分区元数据）
2. 热→冷归档执行（MySQL → Parquet → 对象存储）
3. 归档元数据索引维护
4. 租户级保留策略应用
5. 冷数据懒加载恢复
6. 过期冷数据清理
"""

import json
import uuid
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from calendar import monthrange

import pandas as pd
import numpy as np
from sqlalchemy import and_, or_, func, update, select, text
from sqlalchemy.orm import Session, joinedload
from loguru import logger

from .cold_storage import (
    ColdStorageBackend,
    ColdStorageFactory,
    StorageConfig,
    LocalStorageConfig,
    ObjectStorageConfig,
    ArchiveFileInfo,
)
from ..utils.database import (
    SessionLocal,
    get_db,
    Base,
    # 归档相关 ORM 模型
    ArchivePartitionKey,
    ArchiveMetadata,
    ArchiveJob,
    TenantRetentionPolicy,
    ColdDataLoadRequest,
    # 时序源表
    BoltData,
)


# ============================================================
# 数据类定义
# ============================================================

@dataclass
class ArchiveResult:
    """归档执行结果"""
    success: bool
    archive_job_id: Optional[str] = None
    partitions_processed: int = 0
    rows_archived: int = 0
    rows_deleted: int = 0
    files_created: int = 0
    total_bytes: int = 0
    error_message: Optional[str] = None
    archive_metadata_ids: List[int] = field(default_factory=list)

@dataclass
class LazyLoadResult:
    """懒加载执行结果"""
    success: bool
    request_id: Optional[str] = None
    status: str = "completed"
    hot_rows: int = 0
    cold_rows: int = 0
    total_rows: int = 0
    files_read: int = 0
    bytes_loaded: int = 0
    duration_seconds: float = 0.0
    dataframe: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None


# ============================================================
# 核心归档服务类
# ============================================================

class ArchiveService:
    """时序数据归档服务主类"""

    # 支持归档的时序源表
    ARCHIVABLE_TABLES = {
        "sc_bolt_data": {
            "orm_model": BoltData,
            "time_column": "create_time",
            "id_column": "id",
            "tenant_column": "tenant_id",
            "sensor_column": "sensor_id",
            "default_partition_by": "month",
        },
    }

    def __init__(self, db: Optional[Session] = None,
                 cold_storage: Optional[ColdStorageBackend] = None,
                 storage_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            db: SQLAlchemy Session（外部传入或自动创建）
            cold_storage: 冷存储后端实例
            storage_config: 冷存储配置字典（cold_storage 为 None 时使用）
        """
        self._external_db = db is not None
        self._db = db
        self._cold_storage = cold_storage

        if cold_storage is None and storage_config is not None:
            self._cold_storage = ColdStorageFactory.from_dict(storage_config)

    # ============================================================
    # 会话管理
    # ============================================================

    @property
    def db(self) -> Session:
        if self._db is None or not self._db.is_active:
            self._db = SessionLocal()
        return self._db

    @property
    def cold_storage(self) -> ColdStorageBackend:
        if self._cold_storage is None:
            # 默认使用本地文件系统
            default_config = LocalStorageConfig(
                storage_type="local",
                compression="snappy",
                base_dir="./data/cold_storage",
            )
            self._cold_storage = ColdStorageFactory.create(default_config)
        return self._cold_storage

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_db and self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass

    # ============================================================
    # 分区键管理
    # ============================================================

    @staticmethod
    def _get_month_range(any_date: Union[datetime, str]) -> Tuple[datetime, datetime, str, int]:
        """
        计算给定日期所在月份的时间范围

        Returns:
            (month_start, month_end, partition_key_yyyy_mm, partition_value_yyyymm)
        """
        if isinstance(any_date, str):
            dt = pd.to_datetime(any_date).to_pydatetime()
        elif isinstance(any_date, datetime):
            dt = any_date
        else:
            dt = datetime(any_date.year, any_date.month, 1) if hasattr(any_date, "year") else datetime.now()

        year, month = dt.year, dt.month
        month_start = datetime(year, month, 1)
        days_in_month = monthrange(year, month)[1]
        month_end = datetime(year, month, days_in_month, 23, 59, 59) + timedelta(microseconds=999999)
        # 下月 1 号 0 点作为 partition_end（不含）
        next_month = month_start + timedelta(days=days_in_month)
        partition_end = next_month.replace(day=1)

        partition_key = month_start.strftime("%Y-%m")
        partition_value = int(month_start.strftime("%Y%m"))

        return month_start, partition_end, partition_key, partition_value

    def ensure_partition_keys(self, tenant_id: int, table_name: str,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[ArchivePartitionKey]:
        """
        确保给定时间范围内的分区键存在，不存在则创建

        Args:
            tenant_id: 租户ID
            table_name: 源表名
            start_date: 起始时间（默认1年前）
            end_date: 结束时间（默认当前）

        Returns:
            分区键记录列表
        """
        now = datetime.now()
        if start_date is None:
            start_date = now - timedelta(days=400)
        if end_date is None:
            end_date = now

        table_conf = self.ARCHIVABLE_TABLES.get(table_name)
        if not table_conf:
            raise ValueError(f"不支持归档的表: {table_name}")

        partitions = []
        cursor = datetime(start_date.year, start_date.month, 1)
        end_cursor = datetime(end_date.year, end_date.month, 1)

        while cursor <= end_cursor:
            month_start, month_end_exclusive, partition_key, partition_value = self._get_month_range(cursor)
            partition_name = f"p{partition_value}"

            existing = self.db.query(ArchivePartitionKey).filter(
                ArchivePartitionKey.tenant_id == tenant_id,
                ArchivePartitionKey.table_name == table_name,
                ArchivePartitionKey.partition_name == partition_name,
            ).first()

            if not existing:
                # 统计该分区的行数
                orm_model = table_conf["orm_model"]
                time_col = getattr(orm_model, table_conf["time_column"])
                tenant_col = getattr(orm_model, table_conf["tenant_column"])

                row_count = self.db.query(func.count(getattr(orm_model, table_conf["id_column"]))).filter(
                    tenant_col == tenant_id,
                    time_col >= month_start,
                    time_col < month_end_exclusive,
                ).scalar() or 0

                pk = ArchivePartitionKey(
                    tenant_id=tenant_id,
                    table_name=table_name,
                    partition_name=partition_name,
                    partition_key=partition_key,
                    partition_value=partition_value,
                    start_date=month_start,
                    end_date=month_end_exclusive,
                    row_count=row_count,
                    archive_status="hot",
                    is_active=True,
                )
                self.db.add(pk)
                self.db.flush()
                partitions.append(pk)
            else:
                partitions.append(existing)

            # 推进到下月
            next_month = month_start + timedelta(days=monthrange(month_start.year, month_start.month)[1])
            cursor = next_month.replace(day=1)

        self.db.commit()
        return partitions

    def get_hot_partitions_for_archive(self, tenant_id: int, table_name: str,
                                        hot_threshold_days: int = 90) -> List[ArchivePartitionKey]:
        """
        获取满足归档条件的热分区：分区结束时间超过 hot_threshold_days

        Args:
            tenant_id: 租户ID
            table_name: 源表名
            hot_threshold_days: 热数据阈值（天）

        Returns:
            可归档的分区列表
        """
        cutoff_date = datetime.now() - timedelta(days=hot_threshold_days)

        return self.db.query(ArchivePartitionKey).filter(
            ArchivePartitionKey.tenant_id == tenant_id,
            ArchivePartitionKey.table_name == table_name,
            ArchivePartitionKey.archive_status == "hot",
            ArchivePartitionKey.is_active == True,
            ArchivePartitionKey.end_date <= cutoff_date,
            ArchivePartitionKey.row_count > 0,
        ).order_by(ArchivePartitionKey.partition_value.asc()).all()

    # ============================================================
    # 保留策略管理
    # ============================================================

    def get_retention_policy(self, tenant_id: int) -> TenantRetentionPolicy:
        """
        获取租户的保留策略，不存在则创建默认策略

        Returns:
            TenantRetentionPolicy
        """
        policy = self.db.query(TenantRetentionPolicy).filter(
            TenantRetentionPolicy.tenant_id == tenant_id,
            TenantRetentionPolicy.is_active == True,
        ).order_by(TenantRetentionPolicy.is_default.desc(),
                   TenantRetentionPolicy.priority.desc()).first()

        if policy:
            return policy

        # 创建默认策略
        default_policy = TenantRetentionPolicy(
            tenant_id=tenant_id,
            policy_name=f"租户{tenant_id}默认策略",
            policy_type="operations",
            description="系统自动创建的默认运营策略",
            is_default=True,
            is_active=True,
            priority=0,
            hot_retention_days=90,
            cold_retention_days=365,
            compliance_retention_years=None,
            archive_cron="0 3 1 * *",
            purge_cron="0 4 1 * *",
            auto_delete_hot=True,
            lazy_load_enabled=True,
            storage_class="standard_ia",
            compression_algo="snappy",
            encryption_enabled=True,
            version=1,
            change_reason="initial_default",
            created_by="system",
        )
        self.db.add(default_policy)
        self.db.commit()
        self.db.refresh(default_policy)
        return default_policy

    def set_retention_policy(self, tenant_id: int, policy_data: Dict[str, Any],
                             operator: str = "system") -> TenantRetentionPolicy:
        """
        设置/更新租户保留策略（带版本管理）

        Args:
            tenant_id: 租户ID
            policy_data: 策略字段字典
            operator: 操作人

        Returns:
            更新后的策略
        """
        existing = self.db.query(TenantRetentionPolicy).filter(
            TenantRetentionPolicy.tenant_id == tenant_id,
            TenantRetentionPolicy.is_active == True,
        ).order_by(TenantRetentionPolicy.version.desc()).first()

        if existing:
            # 旧版本置为非激活
            stmt = update(TenantRetentionPolicy).where(
                TenantRetentionPolicy.tenant_id == tenant_id,
                TenantRetentionPolicy.is_active == True,
            ).values(is_active=False)
            self.db.execute(stmt)
            self.db.commit()
            new_version = existing.version + 1
            # 合并新数据
            merged = {
                "policy_name": existing.policy_name,
                "policy_type": existing.policy_type,
                "description": existing.description,
                "hot_retention_days": existing.hot_retention_days,
                "cold_retention_days": existing.cold_retention_days,
                "compliance_retention_years": existing.compliance_retention_years,
                "archive_cron": existing.archive_cron,
                "purge_cron": existing.purge_cron,
                "auto_delete_hot": existing.auto_delete_hot,
                "lazy_load_enabled": existing.lazy_load_enabled,
                "storage_class": existing.storage_class,
                "compression_algo": existing.compression_algo,
                "encryption_enabled": existing.encryption_enabled,
                **policy_data,
            }
        else:
            new_version = 1
            merged = {
                "policy_name": f"租户{tenant_id}策略",
                "policy_type": "custom",
                "description": "自定义策略",
                "hot_retention_days": 90,
                "cold_retention_days": 365,
                "compliance_retention_years": None,
                "archive_cron": "0 3 1 * *",
                "purge_cron": "0 4 1 * *",
                "auto_delete_hot": True,
                "lazy_load_enabled": True,
                "storage_class": "standard_ia",
                "compression_algo": "snappy",
                "encryption_enabled": True,
                **policy_data,
            }

        # 根据 policy_type 自动设置保留期
        if merged.get("policy_type") == "compliance":
            merged["cold_retention_days"] = max(merged.get("cold_retention_days", 0), 2555)  # 7年
            merged["compliance_retention_years"] = 7
        elif merged.get("policy_type") == "operations":
            merged["cold_retention_days"] = min(merged.get("cold_retention_days", 365), 365)  # 1年
            merged["compliance_retention_years"] = None

        new_policy = TenantRetentionPolicy(
            tenant_id=tenant_id,
            is_default=False,
            is_active=True,
            priority=100,
            version=new_version,
            change_reason=policy_data.get("change_reason", f"updated by {operator}"),
            created_by=operator,
            approved_by=operator if merged.get("policy_type") == "compliance" else None,
            **merged,
        )
        self.db.add(new_policy)
        self.db.commit()
        self.db.refresh(new_policy)
        return new_policy

    # ============================================================
    # 归档任务执行
    # ============================================================

    def create_archive_job(self, tenant_id: Optional[int], job_type: str,
                           job_name: Optional[str] = None,
                           trigger_type: str = "scheduled",
                           **job_kwargs) -> ArchiveJob:
        """
        创建归档任务记录

        Args:
            tenant_id: 租户ID（None为全局任务）
            job_type: 任务类型
            job_name: 任务名称
            trigger_type: scheduled/manual/api
            **job_kwargs: 其他字段

        Returns:
            ArchiveJob
        """
        job = ArchiveJob(
            job_id=str(uuid.uuid4()).replace("-", ""),
            tenant_id=tenant_id,
            job_name=job_name or f"{job_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            job_type=job_type,
            trigger_type=trigger_type,
            status="running",
            start_time=datetime.now(),
            total_partitions=0,
            processed_partitions=0,
            total_rows=0,
            archived_rows=0,
            failed_rows=0,
            deleted_rows=0,
            archive_size_bytes=0,
            archive_file_count=0,
            error_count=0,
            **job_kwargs,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _finish_archive_job(self, job: ArchiveJob, success: bool,
                            error_message: Optional[str] = None) -> None:
        """完成归档任务，更新状态"""
        job.end_time = datetime.now()
        job.duration_seconds = int((job.end_time - job.start_time).total_seconds())
        job.status = "completed" if success else "failed"
        if error_message:
            job.error_count = 1
            job.error_summary = json.dumps({"message": error_message[:2000]}, ensure_ascii=False)
        self.db.commit()

    def _export_partition_to_dataframe(self, orm_model, time_column: str,
                                        tenant_column: str, tenant_id: int,
                                        partition_start: datetime,
                                        partition_end_exclusive: datetime,
                                        sensor_column: Optional[str] = None,
                                        batch_size: int = 50000) -> pd.DataFrame:
        """
        分批从 MySQL 导出分区数据为 DataFrame，避免大查询 OOM

        Args:
            orm_model: ORM 模型类
            time_column: 时间列名
            tenant_column: 租户列名
            tenant_id: 租户ID
            partition_start: 分区起始
            partition_end_exclusive: 分区结束（不含）
            batch_size: 每批行数
            sensor_column: 传感器列名（用于排序，保证有序）

        Returns:
            DataFrame
        """
        time_attr = getattr(orm_model, time_column)
        tenant_attr = getattr(orm_model, tenant_column)
        id_attr = getattr(orm_model, "id")

        all_frames = []
        last_id = 0

        while True:
            query = self.db.query(orm_model).filter(
                tenant_attr == tenant_id,
                time_attr >= partition_start,
                time_attr < partition_end_exclusive,
                id_attr > last_id,
            ).order_by(id_attr.asc()).limit(batch_size)

            batch = query.all()
            if not batch:
                break

            records = []
            for row in batch:
                rec = {col.name: getattr(row, col.name) for col in orm_model.__table__.columns}
                records.append(rec)

            df_batch = pd.DataFrame(records)
            all_frames.append(df_batch)
            last_id = records[-1]["id"]

            if len(batch) < batch_size:
                break

        if not all_frames:
            # 获取列名
            columns = [col.name for col in orm_model.__table__.columns]
            return pd.DataFrame(columns=columns)

        return pd.concat(all_frames, ignore_index=True)

    def _archive_single_partition(self, partition: ArchivePartitionKey,
                                  policy: TenantRetentionPolicy,
                                  job: ArchiveJob) -> Tuple[bool, Optional[int], int, int]:
        """
        归档单个分区

        Returns:
            (success, archive_metadata_id, rows_archived, bytes_written)
        """
        table_conf = self.ARCHIVABLE_TABLES.get(partition.table_name)
        if not table_conf:
            return False, None, 0, 0

        orm_model = table_conf["orm_model"]
        time_col_name = table_conf["time_column"]
        tenant_col_name = table_conf["tenant_column"]
        sensor_col_name = table_conf["sensor_column"]

        # 1. 更新分区状态为 archiving
        partition.archive_status = "archiving"
        self.db.commit()

        try:
            # 2. 导出数据
            logger.info(f"开始导出分区 {partition.partition_name} (tenant={partition.tenant_id})")
            df = self._export_partition_to_dataframe(
                orm_model=orm_model,
                time_column=time_col_name,
                tenant_column=tenant_col_name,
                tenant_id=partition.tenant_id,
                partition_start=partition.start_date,
                partition_end_exclusive=partition.end_date,
                sensor_column=sensor_col_name,
                batch_size=getattr(job, "config_snapshot_batch_size", 50000),
            )

            row_count = len(df)
            if row_count == 0:
                logger.warning(f"分区 {partition.partition_name} 无数据，标记为已归档")
                partition.archive_status = "archived"
                partition.archive_time = datetime.now()
                partition.row_count = 0
                self.db.commit()
                return True, None, 0, 0

            # 3. 写入冷存储
            partition_key = partition.partition_key  # YYYY-MM
            partition_name = partition.partition_name  # pYYYYMM
            file_name = f"{partition.table_name}_{partition_name}_{partition.tenant_id}_{int(datetime.now().timestamp())}.parquet"
            archive_path = f"{partition.table_name}/raw"

            logger.info(f"写入冷存储: {len(df)} 行, 文件={file_name}")
            file_info: ArchiveFileInfo = self.cold_storage.write_archive(
                data=df,
                archive_path=archive_path,
                file_name=file_name,
                tenant_id=partition.tenant_id,
                partition_key=partition_key,
            )

            # 4. 写入元数据索引
            if sensor_col_name and sensor_col_name in df.columns:
                sensor_ids = sorted(df[sensor_col_name].dropna().unique().tolist())
            else:
                sensor_ids = []

            fields_list = [col.name for col in orm_model.__table__.columns]

            statistics = {}
            for col_name in ["ptf"]:
                if col_name in df.columns and pd.api.types.is_numeric_dtype(df[col_name]):
                    series = df[col_name].dropna()
                    if len(series) > 0:
                        statistics[col_name] = {
                            "min": float(series.min()),
                            "max": float(series.max()),
                            "mean": float(series.mean()),
                            "count": int(series.count()),
                        }

            # 计算保留到期时间
            cold_days = policy.cold_retention_days or 365
            if policy.compliance_retention_years:
                cold_days = max(cold_days, policy.compliance_retention_years * 365)
            retention_expire = file_info.max_time + timedelta(days=cold_days) if file_info.max_time else datetime.now() + timedelta(days=cold_days)

            metadata = ArchiveMetadata(
                archive_id=str(uuid.uuid4()).replace("-", ""),
                tenant_id=partition.tenant_id,
                source_table=partition.table_name,
                partition_name=partition_name,
                partition_key=partition_key,
                sensor_ids=json.dumps([str(s) for s in sensor_ids], ensure_ascii=False) if sensor_ids else None,
                data_start_time=file_info.min_time or partition.start_date,
                data_end_time=file_info.max_time or (partition.end_date - timedelta(microseconds=1)),
                row_count=file_info.record_count,
                file_size_bytes=file_info.size_bytes,
                storage_type=file_info.storage_type,
                storage_bucket=file_info.bucket,
                storage_path=file_info.path,
                file_checksum=file_info.checksum,
                compression=file_info.compression_codec or policy.compression_algo or "snappy",
                schema_version="v1",
                aggregation_level="raw",
                fields=json.dumps(fields_list, ensure_ascii=False),
                statistics=json.dumps(statistics, ensure_ascii=False) if statistics else None,
                job_id=job.job_id,
                status="active",
                restore_count=0,
                access_count=0,
            )
            self.db.add(metadata)
            self.db.flush()

            # 5. 可选：从热库删除数据
            rows_deleted = 0
            if policy.auto_delete_hot:
                time_attr = getattr(orm_model, time_col_name)
                tenant_attr = getattr(orm_model, tenant_col_name)

                delete_query = orm_model.__table__.delete().where(and_(
                    tenant_attr == partition.tenant_id,
                    time_attr >= partition.start_date,
                    time_attr < partition.end_date,
                ))
                result = self.db.execute(delete_query)
                rows_deleted = result.rowcount or 0
                logger.info(f"从热库删除 {rows_deleted} 行")

            # 6. 更新分区状态
            partition.archive_status = "archived"
            partition.archive_time = datetime.now()
            partition.row_count = 0
            partition.retention_expire_time = retention_expire
            partition.purge_time = datetime.now() if policy.auto_delete_hot else None

            job.processed_partitions += 1
            job.archived_rows += file_info.record_count
            job.deleted_rows += rows_deleted
            job.archive_size_bytes += file_info.size_bytes
            job.archive_file_count += 1

            self.db.commit()
            self.db.refresh(metadata)

            logger.info(f"分区 {partition.partition_name} 归档完成: {file_info.record_count} 行, {file_info.size_bytes} 字节, 删除={rows_deleted}")
            return True, metadata.id, file_info.record_count, file_info.size_bytes

        except Exception as e:
            self.db.rollback()
            partition.archive_status = "hot"  # 恢复为热
            self.db.commit()

            logger.error(f"分区 {partition.partition_name} 归档失败: {e}")
            logger.error(traceback.format_exc())
            return False, None, 0, 0

    def run_monthly_archive(self, tenant_id: int,
                            table_name: Optional[str] = None,
                            hot_threshold_days: Optional[int] = None,
                            trigger_type: str = "scheduled",
                            operator: Optional[str] = None) -> ArchiveResult:
        """
        执行月度归档任务（主入口）

        Args:
            tenant_id: 租户ID
            table_name: 指定表名（None=全部可归档表）
            hot_threshold_days: 热数据阈值（None=从策略读取）
            trigger_type: scheduled/manual/api
            operator: 操作人

        Returns:
            ArchiveResult
        """
        from app.utils.db_pool import db_pool

        quota_name = "archive"
        quota = db_pool.get_quota(quota_name)
        quota_acquired = False
        if quota:
            quota_acquired = quota.acquire(timeout=30.0)
            if not quota_acquired:
                logger.warning(f"归档连接池配额获取超时 ({quota.current}/{quota.max_connections})")

        try:
            return self._run_monthly_archive_impl(
                tenant_id=tenant_id,
                table_name=table_name,
                hot_threshold_days=hot_threshold_days,
                trigger_type=trigger_type,
                operator=operator,
            )
        finally:
            if quota and quota_acquired:
                quota.release()

    def _run_monthly_archive_impl(self, tenant_id: int,
                            table_name: Optional[str] = None,
                            hot_threshold_days: Optional[int] = None,
                            trigger_type: str = "scheduled",
                            operator: Optional[str] = None) -> ArchiveResult:
        policy = self.get_retention_policy(tenant_id)

        if hot_threshold_days is None:
            hot_threshold_days = policy.hot_retention_days or 90

        tables_to_process = [table_name] if table_name else list(self.ARCHIVABLE_TABLES.keys())

        # 创建任务记录
        job = self.create_archive_job(
            tenant_id=tenant_id,
            job_type="archive_monthly",
            job_name=f"月度归档_租户{tenant_id}_{datetime.now().strftime('%Y%m%d')}",
            trigger_type=trigger_type,
            source_table=",".join(tables_to_process),
            target_storage=self.cold_storage.config.storage_type if hasattr(self.cold_storage, "config") else "local",
            hot_threshold_days=hot_threshold_days,
            retention_days=policy.cold_retention_days,
            delete_from_hot=policy.auto_delete_hot,
            cron_expression=policy.archive_cron,
            created_by=operator,
            config_snapshot=json.dumps({
                "policy_type": policy.policy_type,
                "hot_threshold_days": hot_threshold_days,
                "cold_retention_days": policy.cold_retention_days,
                "compliance_years": policy.compliance_retention_years,
                "compression": policy.compression_algo,
                "storage_class": policy.storage_class,
            }, ensure_ascii=False),
        )

        result = ArchiveResult(success=True, archive_job_id=job.job_id)

        try:
            for tbl in tables_to_process:
                # 确保分区键存在
                self.ensure_partition_keys(tenant_id, tbl)

                # 获取可归档分区
                partitions = self.get_hot_partitions_for_archive(tenant_id, tbl, hot_threshold_days)
                job.total_partitions += len(partitions)
                logger.info(f"表 {tbl}: 发现 {len(partitions)} 个可归档分区, 阈值={hot_threshold_days}天")

                partition_keys_list = []
                total_rows_for_table = 0

                for part in partitions:
                    partition_keys_list.append(part.partition_key)
                    success, meta_id, rows, bytes_written = self._archive_single_partition(
                        partition=part,
                        policy=policy,
                        job=job,
                    )
                    if success:
                        result.partitions_processed += 1
                        result.rows_archived += rows
                        result.total_bytes += bytes_written
                        total_rows_for_table += rows
                        if meta_id:
                            result.archive_metadata_ids.append(meta_id)
                    else:
                        result.success = False
                        job.failed_rows += part.row_count

                if partition_keys_list:
                    job.partitions = json.dumps(partition_keys_list, ensure_ascii=False)
                job.total_rows += total_rows_for_table

            # 统计删除行数
            result.rows_deleted = job.deleted_rows
            result.files_created = job.archive_file_count

            self._finish_archive_job(job, result.success)

        except Exception as e:
            logger.error(f"归档任务异常: {e}")
            logger.error(traceback.format_exc())
            result.success = False
            result.error_message = str(e)[:2000]
            self._finish_archive_job(job, False, str(e))

        return result

    # ============================================================
    # 懒加载（冷→热查询）
    # ============================================================

    def _match_archive_metadata(self, tenant_id: int, table_name: str,
                                start_time: datetime, end_time: datetime,
                                sensor_ids: Optional[List[Any]] = None
                                ) -> List[ArchiveMetadata]:
        """
        根据时间范围和传感器匹配归档元数据

        Returns:
            匹配的 ArchiveMetadata 列表
        """
        query = self.db.query(ArchiveMetadata).filter(
            ArchiveMetadata.tenant_id == tenant_id,
            ArchiveMetadata.source_table == table_name,
            ArchiveMetadata.status == "active",
            # 时间范围有交集
            ArchiveMetadata.data_start_time < end_time,
            ArchiveMetadata.data_end_time >= start_time,
        )

        results = query.order_by(ArchiveMetadata.partition_key.asc()).all()

        # 传感器过滤（数据库级 JSON 查询复杂，这里应用层过滤）
        if sensor_ids and results:
            sensor_id_strs = {str(s) for s in sensor_ids}
            filtered = []
            for meta in results:
                if meta.sensor_ids:
                    try:
                        meta_sensors = set(json.loads(meta.sensor_ids))
                    except (json.JSONDecodeError, TypeError):
                        meta_sensors = set()
                    if meta_sensors and not meta_sensors & sensor_id_strs:
                        continue
                filtered.append(meta)
            return filtered

        return results

    def query_tiered(self, tenant_id: int, table_name: str,
                     start_time: datetime, end_time: datetime,
                     sensor_ids: Optional[List[Any]] = None,
                     columns: Optional[List[str]] = None,
                     read_tier: str = "hot_only",
                     policy: Optional[TenantRetentionPolicy] = None,
                     user_id: Optional[str] = None,
                     api_endpoint: Optional[str] = None,
                     user_type: str = "api",
                     async_mode: bool = False,
                     priority: str = "normal",
                     restore_to_hot: bool = False,
                     request_params: Optional[Dict[str, Any]] = None,
                     ) -> LazyLoadResult:
        """
        透明分层查询：指定时间范围自动路由热/冷数据

        Args:
            tenant_id: 租户ID
            table_name: 源表名
            start_time: 查询起始时间
            end_time: 查询结束时间
            sensor_ids: 传感器ID列表
            columns: 列过滤
            read_tier: hot_only / hot_warm / all（控制是否访问冷数据）
            policy: 保留策略（None=自动读取）
            user_id: 触发用户
            api_endpoint: 触发 API
            user_type: api/user/training/analysis
            async_mode: 是否异步加载冷数据
            priority: 懒加载优先级
            restore_to_hot: 加载后是否回迁到热库
            request_params: 原始请求参数（审计用）

        Returns:
            LazyLoadResult
        """
        if policy is None:
            policy = self.get_retention_policy(tenant_id)

        start_dt = start_time
        end_dt = end_time
        table_conf = self.ARCHIVABLE_TABLES.get(table_name)

        if not table_conf:
            return LazyLoadResult(success=False, error_message=f"不支持的表: {table_name}")

        orm_model = table_conf["orm_model"]
        time_col = getattr(orm_model, table_conf["time_column"])
        tenant_col = getattr(orm_model, table_conf["tenant_column"])
        sensor_col_name = table_conf["sensor_column"]
        id_col = getattr(orm_model, table_conf["id_column"])

        result = LazyLoadResult(success=True)
        overall_start = datetime.now()

        # ---------- 1. 计算冷热阈值分界 ----------
        hot_cutoff = datetime.now() - timedelta(days=policy.hot_retention_days or 90)
        warm_cutoff = datetime.now() - timedelta(days=(policy.cold_retention_days or 365))

        hot_start = max(start_dt, hot_cutoff)
        hot_end = end_dt
        cold_range_start = start_dt
        cold_range_end = min(end_dt, hot_cutoff)

        hot_data_need = hot_start < hot_end
        cold_data_need = (cold_range_start < cold_range_end) and (read_tier != "hot_only")

        # ---------- 2. 读取热数据 ----------
        hot_df = pd.DataFrame()
        if hot_data_need:
            try:
                query = self.db.query(orm_model).filter(
                    tenant_col == tenant_id,
                    time_col >= hot_start,
                    time_col < hot_end,
                )

                if sensor_ids and sensor_col_name:
                    sensor_attr = getattr(orm_model, sensor_col_name)
                    query = query.filter(sensor_attr.in_([
                        int(s) if isinstance(s, str) and s.isdigit() else s for s in sensor_ids
                    ]))

                hot_rows = query.all()
                if hot_rows:
                    records = [{c.name: getattr(r, c.name) for c in orm_model.__table__.columns} for r in hot_rows]
                    hot_df = pd.DataFrame(records)
                    result.hot_rows = len(hot_df)
                    logger.info(f"热数据查询: {len(hot_df)} 行")
            except Exception as e:
                logger.error(f"热数据查询失败: {e}")
                result.success = False
                result.error_message = f"热数据查询失败: {e}"

        # ---------- 3. 匹配并读取冷数据 ----------
        cold_df = pd.DataFrame()
        cold_matches: List[ArchiveMetadata] = []

        if cold_data_need and policy.lazy_load_enabled:
            cold_matches = self._match_archive_metadata(
                tenant_id=tenant_id,
                table_name=table_name,
                start_time=cold_range_start,
                end_time=cold_range_end,
                sensor_ids=sensor_ids,
            )
            logger.info(f"匹配到 {len(cold_matches)} 个冷数据归档文件")

        # ---------- 3.1 异步模式：只创建请求记录，不实际加载 ----------
        if async_mode and cold_matches:
            request_id = str(uuid.uuid4()).replace("-", "")
            load_req = ColdDataLoadRequest(
                request_id=request_id,
                tenant_id=tenant_id,
                user_id=user_id,
                user_type=user_type,
                api_endpoint=api_endpoint,
                source_table=table_name,
                sensor_ids=json.dumps([str(s) for s in sensor_ids], ensure_ascii=False) if sensor_ids else None,
                query_start_time=start_dt,
                query_end_time=end_dt,
                aggregation_level="raw",
                hot_data_range=json.dumps({"start": hot_start.isoformat(), "end": hot_end.isoformat()}, ensure_ascii=False),
                cold_data_ranges=json.dumps([{"start": cold_range_start.isoformat(), "end": cold_range_end.isoformat()}], ensure_ascii=False),
                archive_ids=json.dumps([m.archive_id for m in cold_matches], ensure_ascii=False),
                partition_keys=json.dumps(list({m.partition_key for m in cold_matches}), ensure_ascii=False),
                status="pending",
                priority=priority,
                async_mode=True,
                restore_to_hot=restore_to_hot,
                restore_expire_hours=72,
                request_params=json.dumps(request_params or {}, ensure_ascii=False),
            )
            self.db.add(load_req)
            self.db.commit()

            result.request_id = request_id
            result.status = "pending"
            result.total_rows = result.hot_rows
            if not hot_df.empty:
                result.dataframe = hot_df
            result.duration_seconds = (datetime.now() - overall_start).total_seconds()
            return result

        # ---------- 3.2 同步模式：实际加载冷数据 ----------
        request_id = str(uuid.uuid4()).replace("-", "")
        load_req = ColdDataLoadRequest(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_type=user_type,
            api_endpoint=api_endpoint,
            source_table=table_name,
            sensor_ids=json.dumps([str(s) for s in sensor_ids], ensure_ascii=False) if sensor_ids else None,
            query_start_time=start_dt,
            query_end_time=end_dt,
            aggregation_level="raw",
            hot_data_range=json.dumps({"start": hot_start.isoformat(), "end": hot_end.isoformat()}, ensure_ascii=False),
            cold_data_ranges=json.dumps([{"start": cold_range_start.isoformat(), "end": cold_range_end.isoformat()}], ensure_ascii=False),
            archive_ids=json.dumps([m.archive_id for m in cold_matches], ensure_ascii=False) if cold_matches else None,
            partition_keys=json.dumps(list({m.partition_key for m in cold_matches}), ensure_ascii=False) if cold_matches else None,
            status="loading",
            priority=priority,
            async_mode=False,
            start_time=datetime.now(),
            restore_to_hot=restore_to_hot,
            restore_expire_hours=72,
            hot_row_count=result.hot_rows,
            request_params=json.dumps(request_params or {}, ensure_ascii=False),
        )
        self.db.add(load_req)
        self.db.flush()

        if cold_matches:
            cold_frames = []
            for meta in cold_matches:
                try:
                    df_cold = self.cold_storage.read_archive(
                        bucket=meta.storage_bucket,
                        archive_path=meta.storage_path,
                        file_name=meta.storage_path.rsplit("/", 1)[-1] if "/" in meta.storage_path else meta.storage_path,
                        columns=columns,
                        time_range=(cold_range_start, cold_range_end),
                        sensor_ids=sensor_ids,
                    )
                    if not df_cold.empty:
                        cold_frames.append(df_cold)
                        result.cold_bytes_loaded += meta.file_size_bytes
                        result.files_read += 1

                    # 更新访问统计
                    meta.access_count = (meta.access_count or 0) + 1
                    meta.last_access_time = datetime.now()
                except Exception as e:
                    logger.error(f"读取归档文件失败 (id={meta.archive_id}): {e}")

            if cold_frames:
                cold_df = pd.concat(cold_frames, ignore_index=True)
                result.cold_rows = len(cold_df)
                load_req.cold_row_count = result.cold_rows
                load_req.cold_file_count = result.files_read
                load_req.cold_bytes_loaded = result.cold_bytes_loaded
                logger.info(f"冷数据读取: {len(cold_df)} 行, {result.files_read} 个文件")

        # ---------- 4. 合并冷热数据 ----------
        frames = []
        if not hot_df.empty:
            frames.append(hot_df)
        if not cold_df.empty:
            frames.append(cold_df)

        if frames:
            merged = pd.concat(frames, ignore_index=True)
            if not merged.empty and "create_time" in merged.columns:
                merged = merged.sort_values("create_time").reset_index(drop=True)
            result.dataframe = merged

        result.total_rows = result.hot_rows + result.cold_rows
        load_req.total_row_count = result.total_rows
        load_req.status = "completed" if result.success else "failed"
        load_req.end_time = datetime.now()
        load_req.duration_seconds = (load_req.end_time - load_req.start_time).total_seconds()
        if not result.success and result.error_message:
            load_req.error_message = result.error_message[:2000]

        self.db.commit()

        result.request_id = request_id
        result.duration_seconds = (datetime.now() - overall_start).total_seconds()
        return result

    # ============================================================
    # 过期冷数据清理
    # ============================================================

    def purge_expired_cold_data(self, tenant_id: int,
                                trigger_type: str = "scheduled") -> ArchiveResult:
        """
        清理已超过保留期限的冷数据

        Args:
            tenant_id: 租户ID
            trigger_type: scheduled/manual

        Returns:
            ArchiveResult
        """
        policy = self.get_retention_policy(tenant_id)

        job = self.create_archive_job(
            tenant_id=tenant_id,
            job_type="purge_expired",
            job_name=f"过期清理_租户{tenant_id}_{datetime.now().strftime('%Y%m%d')}",
            trigger_type=trigger_type,
            retention_days=policy.cold_retention_days,
            cron_expression=policy.purge_cron,
        )

        result = ArchiveResult(success=True, archive_job_id=job.job_id)
        now = datetime.now()

        try:
            # 查询到期的分区
            expired_partitions = self.db.query(ArchivePartitionKey).filter(
                ArchivePartitionKey.tenant_id == tenant_id,
                ArchivePartitionKey.archive_status == "archived",
                ArchivePartitionKey.retention_expire_time <= now,
                ArchivePartitionKey.is_active == True,
            ).all()

            job.total_partitions = len(expired_partitions)
            logger.info(f"发现 {len(expired_partitions)} 个到期分区需要清理")

            for part in expired_partitions:
                # 查找关联元数据
                metas = self.db.query(ArchiveMetadata).filter(
                    ArchiveMetadata.tenant_id == tenant_id,
                    ArchiveMetadata.partition_name == part.partition_name,
                    ArchiveMetadata.source_table == part.table_name,
                    ArchiveMetadata.status == "active",
                ).all()

                for meta in metas:
                    try:
                        deleted = self.cold_storage.delete_archive(
                            bucket=meta.storage_bucket,
                            archive_path=meta.storage_path,
                            file_name=meta.storage_path.rsplit("/", 1)[-1] if "/" in meta.storage_path else meta.storage_path,
                        )
                        if deleted:
                            meta.status = "deleted"
                            result.rows_archived += meta.row_count  # 复用字段表示清理行数
                            result.files_created += 1  # 复用字段表示清理文件数
                            job.archive_file_count += 1
                            job.archived_rows += meta.row_count
                    except Exception as e:
                        logger.error(f"删除冷存储文件失败: {meta.archive_id}, err={e}")

                part.archive_status = "purged"
                result.partitions_processed += 1
                job.processed_partitions += 1

            self.db.commit()
            self._finish_archive_job(job, True)

        except Exception as e:
            logger.error(f"过期清理失败: {e}")
            logger.error(traceback.format_exc())
            result.success = False
            result.error_message = str(e)
            self._finish_archive_job(job, False, str(e))

        return result

    # ============================================================
    # 辅助：获取归档统计
    # ============================================================

    def get_archive_statistics(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户归档统计"""
        policy = self.get_retention_policy(tenant_id)

        # 分区统计
        partition_stats = self.db.query(
            ArchivePartitionKey.archive_status,
            func.count(ArchivePartitionKey.id),
            func.sum(ArchivePartitionKey.row_count),
            func.sum(ArchivePartitionKey.data_size_bytes),
        ).filter(ArchivePartitionKey.tenant_id == tenant_id).group_by(ArchivePartitionKey.archive_status).all()

        status_map = {}
        for status, cnt, rows, size in partition_stats:
            status_map[status] = {
                "partition_count": cnt,
                "row_count": int(rows or 0),
                "size_bytes": int(size or 0),
            }

        # 归档文件统计
        archive_stats = self.db.query(
            func.count(ArchiveMetadata.id),
            func.sum(ArchiveMetadata.row_count),
            func.sum(ArchiveMetadata.file_size_bytes),
        ).filter(
            ArchiveMetadata.tenant_id == tenant_id,
            ArchiveMetadata.status == "active",
        ).first()

        # 最近任务
        recent_jobs = self.db.query(ArchiveJob).filter(
            ArchiveJob.tenant_id == tenant_id,
        ).order_by(ArchiveJob.start_time.desc()).limit(10).all()

        return {
            "tenant_id": tenant_id,
            "retention_policy": {
                "type": policy.policy_type,
                "hot_days": policy.hot_retention_days,
                "cold_days": policy.cold_retention_days,
                "compliance_years": policy.compliance_retention_years,
                "lazy_load_enabled": policy.lazy_load_enabled,
            },
            "partitions_by_status": status_map,
            "archive_summary": {
                "file_count": int(archive_stats[0] or 0),
                "total_rows": int(archive_stats[1] or 0),
                "total_bytes": int(archive_stats[2] or 0),
            },
            "recent_jobs": [
                {
                    "job_id": j.job_id,
                    "type": j.job_type,
                    "status": j.status,
                    "start_time": j.start_time.isoformat() if j.start_time else None,
                    "duration_seconds": j.duration_seconds,
                    "rows_archived": j.archived_rows,
                    "files": j.archive_file_count,
                }
                for j in recent_jobs
            ],
        }
