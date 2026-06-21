"""
灾备备份与恢复模块（运维化增强版）

功能清单:
1. 定时备份策略
   - 每日增量备份（仅模型文件 + 配置文件）
   - 每周全量备份（模型 + 配置 + DB dump）
   - pre-restore 快照备份（恢复前自动触发）

2. 备份元数据管理
   - 元数据持久化到 MySQL (sc_backup_records)
   - 记录: 大小、组件、checksum(sha256/md5)、保留策略
   - 增量链管理 (base_backup_id / backup_chain_id)

3. 异地备份 (S3 / MinIO)
   - 兼容 boto3 S3 API (AWS S3 / MinIO / 阿里云OSS等)
   - 异步上传 + 重试机制
   - 上传状态追踪

4. 恢复服务
   - 恢复前自动创建 pre-restore 快照
   - 按组件选择性恢复 (models/config/database)
   - 恢复后触发模型缓存刷新
   - 恢复操作日志 (sc_backup_restore_logs)

使用示例:
    from app.core.backup import BackupOpsManager

    manager = BackupOpsManager()

    # 每日增量备份 (模型+配置)
    record = manager.create_incremental_backup()

    # 每周全量备份 (含DB)
    record = manager.create_full_backup()

    # 恢复指定备份 (自动pre-restore快照 + 缓存刷新)
    restore_log = manager.restore_backup(backup_id="backup_xxx")

    # 列出备份
    backups = manager.list_backups(backup_type="incremental")
"""

import os
import io
import gzip
import json
import uuid
import shutil
import hashlib
import tarfile
import subprocess
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager

from loguru import logger

from app.utils.config import config
from app.utils.database import get_db, BackupRecord, BackupRestoreLog


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ComponentBackupResult:
    """单个组件备份结果"""
    component: str
    included: bool = False
    file_count: int = 0
    size_bytes: int = 0
    source_path: str = ""
    target_path: str = ""
    checksum_sha256: str = ""
    error: str = ""


@dataclass
class BackupBuildResult:
    """备份构建结果（内部使用，写库前的中间状态）"""
    backup_id: str
    backup_type: str
    backup_scope: str
    components: List[str] = field(default_factory=list)
    component_results: List[ComponentBackupResult] = field(default_factory=list)
    source_dir: Path = None
    archive_path: Path = None
    total_size_bytes: int = 0
    compressed_size_bytes: int = 0
    file_count: int = 0
    checksum_sha256: str = ""
    checksum_md5: str = ""
    checksums_detail: Dict = field(default_factory=dict)
    retention_policy: str = "standard"
    retention_days: int = 30
    backup_chain_id: str = ""
    base_backup_id: str = ""
    incremental_since: Optional[datetime] = None
    database_dump_info: Dict = field(default_factory=dict)
    error: str = ""


@dataclass
class RestoreBuildResult:
    """恢复操作结果（内部使用）"""
    restore_id: str
    backup_id: str
    pre_snapshot_backup_id: str = ""
    pre_snapshot_path: str = ""
    restored_components: List[str] = field(default_factory=list)
    restored_file_count: int = 0
    restored_size_bytes: int = 0
    cache_refresh_status: str = "pending"
    cache_refresh_detail: Dict = field(default_factory=dict)
    models_reloaded: List[str] = field(default_factory=list)
    validation_result: Dict = field(default_factory=dict)
    validation_passed: bool = True
    error: str = ""


# ============================================================
# 工具函数
# ============================================================

def generate_backup_id(backup_type: str) -> str:
    """生成备份ID"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{backup_type}_{ts}_{uuid.uuid4().hex[:6]}"


def generate_chain_id() -> str:
    """生成备份链ID (按周分组)"""
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return f"chain_{year}_W{week:02d}"


def generate_restore_id() -> str:
    """生成恢复操作ID"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"restore_{ts}_{uuid.uuid4().hex[:6]}"


def calculate_file_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """计算单个文件 SHA256"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_file_md5(file_path: Path, chunk_size: int = 8192) -> str:
    """计算单个文件 MD5"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def calculate_stream_sha256(stream_path: Path, chunk_size: int = 8192) -> Tuple[str, int]:
    """流式计算 SHA256 和总字节数"""
    sha256 = hashlib.sha256()
    total = 0
    with open(stream_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
            total += len(chunk)
    return sha256.hexdigest(), total


def scan_directory_files(src_dir: Path) -> List[Tuple[Path, int]]:
    """扫描目录下所有文件，返回 [(路径, 大小)]"""
    result = []
    if not src_dir.exists():
        return result
    for root, _, files in os.walk(src_dir):
        for name in files:
            p = Path(root) / name
            try:
                sz = p.stat().st_size
                result.append((p, sz))
            except OSError:
                continue
    return result


def scan_directory_modified_since(
    src_dir: Path,
    since_time: datetime,
) -> List[Tuple[Path, int]]:
    """扫描增量文件（since_time之后修改过的）"""
    result = []
    if not src_dir.exists():
        return result
    since_ts = since_time.timestamp()
    for root, _, files in os.walk(src_dir):
        for name in files:
            p = Path(root) / name
            try:
                stat = p.stat()
                if stat.st_mtime >= since_ts:
                    result.append((p, stat.st_size))
            except OSError:
                continue
    return result


# ============================================================
# S3 / MinIO 异地备份上传器
# ============================================================

class RemoteBackupUploader:
    """
    S3/MinIO 异地备份上传器

    支持:
    - AWS S3 (endpoint_url 留空)
    - MinIO (endpoint_url = http://minio-host:9000)
    - 阿里云 OSS (endpoint_url = https://oss-cn-xxx.aliyuncs.com)
    """

    def __init__(self):
        backup_cfg = config.get("backup", {}) or {}
        remote_cfg = backup_cfg.get("remote_storage", {}) or {}
        self.enabled = remote_cfg.get("enabled", False)
        self.storage_type = remote_cfg.get("type", "s3")

        s3_cfg = remote_cfg.get("s3", {}) or {}
        minio_cfg = remote_cfg.get("minio", {}) or {}

        if self.storage_type == "minio":
            active_cfg = minio_cfg
        else:
            active_cfg = s3_cfg

        self.endpoint_url = (
            os.getenv("BACKUP_REMOTE_ENDPOINT")
            or active_cfg.get("endpoint_url", "")
        )
        self.region = (
            os.getenv("BACKUP_REMOTE_REGION")
            or active_cfg.get("region", "us-east-1")
        )
        self.bucket = (
            os.getenv("BACKUP_REMOTE_BUCKET")
            or active_cfg.get("bucket", "bolt-preload-backups")
        )
        self.access_key = (
            os.getenv("BACKUP_REMOTE_ACCESS_KEY")
            or active_cfg.get("access_key", "")
        )
        self.secret_key = (
            os.getenv("BACKUP_REMOTE_SECRET_KEY")
            or active_cfg.get("secret_key", "")
        )
        self.base_path = (
            active_cfg.get("base_path", "backups")
        )
        self.use_ssl = active_cfg.get("use_ssl", True)
        self.storage_class = active_cfg.get("storage_class", "standard_ia")
        self.server_side_encryption = active_cfg.get("server_side_encryption", "AES256")

        self.max_retries = remote_cfg.get("upload_max_retries", 3)
        self.retry_delay_seconds = remote_cfg.get("upload_retry_delay_seconds", 5)
        self.chunk_size_mb = remote_cfg.get("multipart_chunksize_mb", 8)

        self._boto3_client = None
        self._initialized = False

    def _get_client(self):
        """懒加载 boto3 客户端"""
        if self._initialized:
            return self._boto3_client

        if not self.enabled:
            logger.debug("[RemoteUploader] 远程存储未启用")
            self._initialized = True
            return None

        try:
            import boto3
            from botocore.client import Config

            kwargs = {
                "aws_access_key_id": self.access_key,
                "aws_secret_access_key": self.secret_key,
                "region_name": self.region,
                "config": Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                ),
            }
            if self.endpoint_url:
                kwargs["endpoint_url"] = self.endpoint_url
                if not self.use_ssl and self.endpoint_url.startswith("http://"):
                    kwargs["use_ssl"] = False

            self._boto3_client = boto3.client("s3", **kwargs)
            logger.info(
                f"[RemoteUploader] 初始化成功: type={self.storage_type}, "
                f"endpoint={self.endpoint_url or 'AWS-S3'}, bucket={self.bucket}"
            )
        except ImportError:
            logger.warning("[RemoteUploader] boto3 未安装，远程存储功能不可用。请 pip install boto3")
            self._boto3_client = None
        except Exception as e:
            logger.error(f"[RemoteUploader] 初始化失败: {e}")
            self._boto3_client = None

        self._initialized = True
        return self._boto3_client

    def build_object_key(self, backup_id: str, archive_path: Path) -> str:
        """构建远程对象 Key"""
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        filename = archive_path.name
        return f"{self.base_path}/{date_prefix}/{backup_id}/{filename}"

    def upload_backup(
        self,
        backup_id: str,
        archive_path: Path,
        extra_args: Optional[Dict] = None,
    ) -> Tuple[bool, str, str]:
        """
        上传备份文件到远程存储

        Returns:
            (success, object_key, error_message)
        """
        if not self.enabled:
            return True, "", "remote_storage_disabled"

        client = self._get_client()
        if client is None:
            return False, "", "s3_client_not_available"

        if not archive_path.exists():
            return False, "", f"archive_not_found: {archive_path}"

        object_key = self.build_object_key(backup_id, archive_path)

        upload_extra = {}
        if self.storage_class:
            upload_extra["StorageClass"] = self.storage_class
        if self.server_side_encryption:
            upload_extra["ServerSideEncryption"] = self.server_side_encryption
        if extra_args:
            upload_extra.update(extra_args)

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"[RemoteUploader] 开始上传 [{attempt}/{self.max_retries}]: "
                    f"{archive_path.name} -> {self.bucket}/{object_key}"
                )
                client.upload_file(
                    Filename=str(archive_path),
                    Bucket=self.bucket,
                    Key=object_key,
                    ExtraArgs=upload_extra if upload_extra else None,
                    Config=None,
                )
                logger.info(f"[RemoteUploader] 上传成功: {object_key}")
                return True, object_key, ""
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"[RemoteUploader] 上传失败 [{attempt}/{self.max_retries}]: "
                    f"{archive_path.name}, error: {e}"
                )
                if attempt < self.max_retries:
                    import time
                    time.sleep(self.retry_delay_seconds)

        return False, object_key, last_error

    def download_backup(
        self,
        object_key: str,
        dest_path: Path,
    ) -> bool:
        """从远程存储下载备份"""
        if not self.enabled:
            return False
        client = self._get_client()
        if client is None:
            return False
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(
                Bucket=self.bucket,
                Key=object_key,
                Filename=str(dest_path),
            )
            return True
        except Exception as e:
            logger.error(f"[RemoteUploader] 下载失败: {object_key} -> {dest_path}: {e}")
            return False


# ============================================================
# 主操作类
# ============================================================

class BackupOpsManager:
    """
    灾备备份与恢复操作管理器
    """

    COMPONENT_MODELS = "models"
    COMPONENT_CONFIG = "config"
    COMPONENT_DATABASE = "database"

    SCOPE_MODELS_CONFIG = "models_config"
    SCOPE_MODELS_CONFIG_DB = "models_config_db"
    SCOPE_ALL = "all"

    RETENTION_STANDARD = "standard"
    RETENTION_WEEKLY = "weekly"
    RETENTION_MONTHLY = "monthly"
    RETENTION_YEARLY = "yearly"
    RETENTION_PERMANENT = "permanent"

    def __init__(self):
        backup_cfg = config.get("backup", {}) or {}

        paths_cfg = backup_cfg.get("paths", {}) or {}
        self.backup_root = Path(
            paths_cfg.get("backup_dir", "./data/backups")
        ).resolve()
        self.backup_root.mkdir(parents=True, exist_ok=True)

        self.temp_root = self.backup_root / "_temp"
        self.temp_root.mkdir(parents=True, exist_ok=True)

        self.project_root = Path(__file__).parent.parent.parent.resolve()
        self.models_dir = Path(
            backup_cfg.get("model_path") or self.project_root / "trained_models"
        ).resolve()
        self.config_dir = Path(
            backup_cfg.get("config_path") or self.project_root / "config"
        ).resolve()

        retention_cfg = backup_cfg.get("retention", {}) or {}
        self.default_retention_days = retention_cfg.get("default_days", 30)
        self.incremental_retention_days = retention_cfg.get("incremental_days", 7)
        self.full_retention_days = retention_cfg.get("full_days", 30)
        self.weekly_retention_days = retention_cfg.get("weekly_days", 90)
        self.monthly_retention_days = retention_cfg.get("monthly_days", 180)
        self.snapshot_retention_days = retention_cfg.get("snapshot_days", 7)

        self.enable_compression = backup_cfg.get("compress", True)
        self.compression_format = backup_cfg.get("compression_format", "tar.gz")

        self.remote_uploader = RemoteBackupUploader()

        logger.info(
            f"[BackupOpsManager] 初始化完成: "
            f"backup_root={self.backup_root}, "
            f"models={self.models_dir}, "
            f"config={self.config_dir}, "
            f"remote_enabled={self.remote_uploader.enabled}"
        )

    # ================================================================
    # 公共 API: 创建备份
    # ================================================================

    def create_incremental_backup(
        self,
        trigger_type: str = "scheduled",
        trigger_source: str = "scheduler",
        operator_id: str = "",
        operator_name: str = "",
    ) -> Optional[BackupRecord]:
        """
        创建每日增量备份（仅模型 + 配置）

        增量逻辑:
        - 查找最近一次同链路上的备份（全量或增量）作为基准
        - 仅备份 since 基准时间之后有变更的文件
        """
        logger.info("[BackupOps] 开始执行每日增量备份 (models + config)")

        chain_id = generate_chain_id()
        last_backup_time = self._get_chain_last_backup_time(chain_id)
        base_backup = self._get_latest_chain_backup(chain_id)

        build = BackupBuildResult(
            backup_id=generate_backup_id("inc"),
            backup_type="incremental",
            backup_scope=self.SCOPE_MODELS_CONFIG,
            backup_chain_id=chain_id,
            base_backup_id=base_backup.backup_id if base_backup else "",
            incremental_since=last_backup_time,
            retention_policy=self.RETENTION_STANDARD,
            retention_days=self.incremental_retention_days,
        )

        return self._execute_backup_pipeline(
            build=build,
            include_models=True,
            include_config=True,
            include_database=False,
            incremental_since=last_backup_time,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def create_full_backup(
        self,
        trigger_type: str = "scheduled",
        trigger_source: str = "scheduler",
        operator_id: str = "",
        operator_name: str = "",
    ) -> Optional[BackupRecord]:
        """
        创建每周全量备份（模型 + 配置 + DB dump）
        """
        logger.info("[BackupOps] 开始执行每周全量备份 (models + config + database)")

        chain_id = generate_chain_id()

        build = BackupBuildResult(
            backup_id=generate_backup_id("full"),
            backup_type="full",
            backup_scope=self.SCOPE_MODELS_CONFIG_DB,
            backup_chain_id=chain_id,
            base_backup_id="",
            incremental_since=None,
            retention_policy=self.RETENTION_WEEKLY,
            retention_days=self.weekly_retention_days,
        )

        return self._execute_backup_pipeline(
            build=build,
            include_models=True,
            include_config=True,
            include_database=True,
            incremental_since=None,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def create_pre_restore_snapshot(
        self,
        source_backup_id: str,
        operator_id: str = "",
        operator_name: str = "",
    ) -> Tuple[Optional[BackupRecord], str]:
        """
        恢复前自动创建快照（快速，当前状态作为回滚点）

        Returns:
            (BackupRecord, error_message)
        """
        logger.info(f"[BackupOps] 为恢复操作创建 pre-restore 快照, source={source_backup_id}")

        build = BackupBuildResult(
            backup_id=generate_backup_id("snap"),
            backup_type="snapshot",
            backup_scope=self.SCOPE_MODELS_CONFIG,
            backup_chain_id=f"pre_restore_{uuid.uuid4().hex[:8]}",
            base_backup_id="",
            incremental_since=None,
            retention_policy=self.RETENTION_STANDARD,
            retention_days=self.snapshot_retention_days,
        )

        record = self._execute_backup_pipeline(
            build=build,
            include_models=True,
            include_config=True,
            include_database=False,
            incremental_since=None,
            trigger_type="pre_restore",
            trigger_source=f"restore:{source_backup_id}",
            operator_id=operator_id,
            operator_name=operator_name,
            skip_remote_upload=True,
        )

        if record is None:
            return None, "pre_restore_snapshot_failed"
        return record, ""

    # ================================================================
    # 公共 API: 恢复备份
    # ================================================================

    def restore_backup(
        self,
        backup_id: str,
        restore_models: bool = True,
        restore_config: bool = True,
        restore_database: bool = False,
        trigger_type: str = "manual",
        operator_id: str = "",
        operator_name: str = "",
        operator_note: str = "",
        skip_pre_snapshot: bool = False,
        skip_cache_refresh: bool = False,
    ) -> Optional[BackupRestoreLog]:
        """
        恢复指定备份

        流程:
        1. 校验备份记录存在
        2. (可选) 创建 pre-restore 快照
        3. 解压并按组件恢复
        4. (可选) 触发模型缓存刷新
        5. 写库 + 校验
        """
        logger.info(
            f"[BackupOps] 开始恢复备份: backup_id={backup_id}, "
            f"restore_models={restore_models}, restore_config={restore_config}, "
            f"restore_db={restore_database}"
        )

        restore_id = generate_restore_id()
        result = RestoreBuildResult(
            restore_id=restore_id,
            backup_id=backup_id,
        )

        try:
            with get_db() as db:
                backup_record = (
                    db.query(BackupRecord)
                    .filter(BackupRecord.backup_id == backup_id)
                    .first()
                )
                if not backup_record:
                    raise FileNotFoundError(f"backup_id 不存在: {backup_id}")
                if backup_record.status not in ("completed", "uploaded"):
                    raise ValueError(
                        f"备份状态不可恢复: {backup_record.status}, backup_id={backup_id}"
                    )

                restore_log = BackupRestoreLog(
                    restore_id=restore_id,
                    backup_id=backup_id,
                    backup_record_id=backup_record.id,
                    status="pending",
                    progress_percent=0.0,
                    restore_scope=self._derive_restore_scope(
                        restore_models, restore_config, restore_database
                    ),
                    restore_options=json.dumps({
                        "restore_models": restore_models,
                        "restore_config": restore_config,
                        "restore_database": restore_database,
                        "skip_pre_snapshot": skip_pre_snapshot,
                        "skip_cache_refresh": skip_cache_refresh,
                    }),
                    trigger_type=trigger_type,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    operator_note=operator_note,
                    tenant_id=backup_record.tenant_id,
                )
                db.add(restore_log)
                db.flush()

                archive_path = self._ensure_backup_available(backup_record)
                if not archive_path:
                    raise FileNotFoundError(f"备份文件不可用: {backup_id}")

                if not skip_pre_snapshot and restore_models or restore_config:
                    restore_log.status = "pre_snapshot"
                    db.flush()

                    snap_record, snap_err = self.create_pre_restore_snapshot(
                        source_backup_id=backup_id,
                        operator_id=operator_id,
                        operator_name=operator_name,
                    )
                    if snap_record:
                        result.pre_snapshot_backup_id = snap_record.backup_id
                        result.pre_snapshot_path = snap_record.local_path or ""
                        restore_log.pre_snapshot_backup_id = snap_record.backup_id
                        restore_log.pre_snapshot_path = snap_record.local_path or ""
                        logger.info(
                            f"[BackupOps] pre-restore 快照已创建: {snap_record.backup_id}"
                        )
                    else:
                        logger.warning(
                            f"[BackupOps] pre-restore 快照创建失败 ({snap_err}), 继续恢复..."
                        )

                restore_log.status = "restoring"
                restore_log.progress_percent = 20.0
                db.flush()

                extracted_dir = self._unpack_archive(archive_path, backup_id)

                restored_components = []
                total_restored_files = 0
                total_restored_size = 0

                if restore_models:
                    ok, cnt, sz = self._restore_component(
                        extracted_dir, "models", self.models_dir
                    )
                    if ok:
                        restored_components.append("models")
                        total_restored_files += cnt
                        total_restored_size += sz
                        logger.info(f"[BackupOps] 组件[models] 已恢复: {cnt}个文件")

                if restore_config:
                    ok, cnt, sz = self._restore_component(
                        extracted_dir, "config", self.config_dir
                    )
                    if ok:
                        restored_components.append("config")
                        total_restored_files += cnt
                        total_restored_size += sz
                        logger.info(f"[BackupOps] 组件[config] 已恢复: {cnt}个文件")

                if restore_database and "database" in backup_record.component_list_dict:
                    ok = self._restore_database_dump(extracted_dir)
                    if ok:
                        restored_components.append("database")
                        logger.info("[BackupOps] 组件[database] 已恢复")

                result.restored_components = restored_components
                result.restored_file_count = total_restored_files
                result.restored_size_bytes = total_restored_size
                restore_log.restored_components = json.dumps(restored_components)
                restore_log.restored_file_count = total_restored_files
                restore_log.restored_size_bytes = total_restored_size
                restore_log.progress_percent = 70.0
                db.flush()

                shutil.rmtree(extracted_dir, ignore_errors=True)

                cache_status = "skipped"
                cache_detail = {}
                models_loaded = []

                if not skip_cache_refresh and restore_models:
                    restore_log.status = "refresh_cache"
                    restore_log.cache_refresh_status = "running"
                    db.flush()
                    cache_status, cache_detail, models_loaded = self._refresh_model_cache()

                result.cache_refresh_status = cache_status
                result.cache_refresh_detail = cache_detail
                result.models_reloaded = models_loaded
                restore_log.cache_refresh_status = cache_status
                restore_log.cache_refresh_detail = json.dumps(cache_detail)
                restore_log.models_reloaded = json.dumps(models_loaded)
                logger.info(
                    f"[BackupOps] 模型缓存刷新: status={cache_status}, "
                    f"reloaded={len(models_loaded)}"
                )

                validation = self._validate_restored_backup(
                    backup_record,
                    restored_components,
                    total_restored_files,
                )
                result.validation_result = validation
                result.validation_passed = validation.get("passed", True)
                restore_log.validation_result = json.dumps(validation)
                restore_log.validation_passed = validation.get("passed", True)

                backup_record.restore_count = (backup_record.restore_count or 0) + 1
                backup_record.last_restore_time = datetime.now()

                restore_log.status = "completed"
                restore_log.progress_percent = 100.0
                restore_log.complete_time = datetime.now()
                restore_log.duration_seconds = int(
                    (restore_log.complete_time - restore_log.create_time).total_seconds()
                )
                db.commit()

                logger.info(
                    f"[BackupOps] 恢复完成: restore_id={restore_id}, "
                    f"components={restored_components}, "
                    f"validation_passed={result.validation_passed}"
                )
                return restore_log

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[BackupOps] 恢复失败: {e}\n{tb}")
            result.error = str(e)
            try:
                with get_db() as db:
                    log = (
                        db.query(BackupRestoreLog)
                        .filter(BackupRestoreLog.restore_id == restore_id)
                        .first()
                    )
                    if log:
                        log.status = "failed"
                        log.error_message = str(e)
                        log.error_stack = tb
                        log.complete_time = datetime.now()
                        log.duration_seconds = int(
                            (log.complete_time - log.create_time).total_seconds()
                        )
                        db.commit()
            except Exception:
                pass
            return None

    # ================================================================
    # 公共 API: 查询
    # ================================================================

    def list_backups(
        self,
        backup_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        with get_db() as db:
            q = db.query(BackupRecord)
            if backup_type:
                q = q.filter(BackupRecord.backup_type == backup_type)
            if status:
                q = q.filter(BackupRecord.status == status)
            q = q.order_by(BackupRecord.create_time.desc()).offset(offset).limit(limit)
            return [r.to_dict() for r in q.all()]

    def get_backup_detail(self, backup_id: str) -> Optional[Dict]:
        with get_db() as db:
            r = (
                db.query(BackupRecord)
                .filter(BackupRecord.backup_id == backup_id)
                .first()
            )
            return r.to_dict() if r else None

    def list_restore_logs(
        self,
        backup_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        with get_db() as db:
            q = db.query(BackupRestoreLog)
            if backup_id:
                q = q.filter(BackupRestoreLog.backup_id == backup_id)
            q = q.order_by(BackupRestoreLog.create_time.desc()).limit(limit)
            return [r.to_dict() for r in q.all()]

    def get_restore_log(self, restore_id: str) -> Optional[Dict]:
        with get_db() as db:
            r = (
                db.query(BackupRestoreLog)
                .filter(BackupRestoreLog.restore_id == restore_id)
                .first()
            )
            return r.to_dict() if r else None

    def cleanup_expired_backups(self) -> int:
        """按保留策略清理过期备份"""
        now = datetime.now()
        removed = 0
        with get_db() as db:
            expired = (
                db.query(BackupRecord)
                .filter(BackupRecord.expire_time.isnot(None))
                .filter(BackupRecord.expire_time <= now)
                .filter(BackupRecord.status != "purged")
                .all()
            )
            for rec in expired:
                try:
                    if rec.local_path:
                        p = Path(rec.local_path)
                        if p.exists():
                            if p.is_file():
                                p.unlink()
                            else:
                                shutil.rmtree(p, ignore_errors=True)
                    rec.status = "purged"
                    removed += 1
                except Exception as e:
                    logger.warning(
                        f"[BackupOps] 清理过期备份失败 {rec.backup_id}: {e}"
                    )
            db.commit()
        logger.info(f"[BackupOps] 清理过期备份: 移除 {removed} 个")
        return removed

    # ================================================================
    # 内部: 备份流水线
    # ================================================================

    def _execute_backup_pipeline(
        self,
        build: BackupBuildResult,
        include_models: bool,
        include_config: bool,
        include_database: bool,
        incremental_since: Optional[datetime],
        trigger_type: str,
        trigger_source: str,
        operator_id: str,
        operator_name: str,
        skip_remote_upload: bool = False,
    ) -> Optional[BackupRecord]:
        """执行完整备份流水线"""
        start_time = datetime.now()

        try:
            with get_db() as db:
                record = BackupRecord(
                    backup_id=build.backup_id,
                    backup_type=build.backup_type,
                    backup_scope=build.backup_scope,
                    status="running",
                    progress_percent=0.0,
                    retention_policy=build.retention_policy,
                    retention_days=build.retention_days,
                    expire_time=(
                        start_time + timedelta(days=build.retention_days)
                        if build.retention_days > 0 else None
                    ),
                    backup_chain_id=build.backup_chain_id,
                    base_backup_id=build.base_backup_id,
                    incremental_since=build.incremental_since,
                    storage_location="local",
                    trigger_type=trigger_type,
                    trigger_source=trigger_source,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    create_time=start_time,
                )
                db.add(record)
                db.flush()

                backup_work_dir = self.temp_root / build.backup_id
                backup_work_dir.mkdir(parents=True, exist_ok=True)
                build.source_dir = backup_work_dir

                record.progress_percent = 5.0
                db.flush()

                component_results: List[ComponentBackupResult] = []

                if include_models:
                    comp = self._backup_component_models(
                        backup_work_dir, incremental_since
                    )
                    component_results.append(comp)

                if include_config:
                    comp = self._backup_component_config(
                        backup_work_dir, incremental_since
                    )
                    component_results.append(comp)

                if include_database:
                    comp = self._backup_component_database(backup_work_dir)
                    component_results.append(comp)
                    if comp.error:
                        build.database_dump_info = {"error": comp.error}
                    else:
                        build.database_dump_info = {
                            "tables_found": True,
                            "component_size": comp.size_bytes,
                        }

                included = [c for c in component_results if c.included]
                build.component_results = included
                build.components = [c.component for c in included]
                build.file_count = sum(c.file_count for c in included)
                build.total_size_bytes = sum(c.size_bytes for c in included)
                record.component_list = json.dumps(build.components)
                record.component_sizes = json.dumps({
                    c.component: {"file_count": c.file_count, "size_bytes": c.size_bytes}
                    for c in included
                })
                record.file_count = build.file_count
                record.size_bytes = build.total_size_bytes
                record.database_dump_info = json.dumps(build.database_dump_info)
                record.progress_percent = 40.0
                db.flush()

                if build.file_count == 0 and not include_database:
                    raise RuntimeError("没有任何文件需要备份（所有组件均为空）")

                if include_database and build.file_count == 0 and \
                        [c for c in included if c.component == "database"]:
                    pass

                manifest = {
                    "backup_id": build.backup_id,
                    "backup_type": build.backup_type,
                    "created_at": start_time.isoformat(),
                    "components": build.components,
                    "component_detail": [asdict(c) for c in included],
                    "incremental_since": incremental_since.isoformat() if incremental_since else None,
                    "base_backup_id": build.base_backup_id,
                    "backup_chain_id": build.backup_chain_id,
                }
                manifest_path = backup_work_dir / "backup_manifest.json"
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                manifest_size = manifest_path.stat().st_size
                build.total_size_bytes += manifest_size
                build.file_count += 1

                checksums = {}
                for c in included:
                    if c.checksum_sha256:
                        checksums[f"{c.component}/MANIFEST"] = c.checksum_sha256
                checksums["backup_manifest.json"] = calculate_file_sha256(manifest_path)

                archive_path, comp_size = self._pack_backup_directory(
                    backup_work_dir, build.backup_id
                )
                build.archive_path = archive_path
                build.compressed_size_bytes = comp_size
                record.compressed_size_bytes = comp_size
                record.progress_percent = 70.0
                db.flush()

                sha, _ = calculate_stream_sha256(archive_path)
                md5 = calculate_file_md5(archive_path)
                build.checksum_sha256 = sha
                build.checksum_md5 = md5
                build.checksums_detail = checksums
                record.checksum_sha256 = sha
                record.checksum_md5 = md5
                record.checksums_detail = json.dumps(checksums)

                final_dir = self.backup_root / build.backup_type
                final_dir.mkdir(parents=True, exist_ok=True)
                final_path = final_dir / archive_path.name
                shutil.move(str(archive_path), str(final_path))
                build.archive_path = final_path
                record.local_path = str(final_path)
                record.progress_percent = 85.0
                db.flush()

                shutil.rmtree(backup_work_dir, ignore_errors=True)

                record.model_versions = json.dumps(self._collect_model_versions_snapshot())
                record.config_snapshot = json.dumps(self._collect_config_snapshot())

                record.status = "completed"
                record.complete_time = datetime.now()
                record.duration_seconds = int(
                    (record.complete_time - start_time).total_seconds()
                )
                record.progress_percent = 100.0
                db.flush()

                if not skip_remote_upload and self.remote_uploader.enabled:
                    record.status = "uploading"
                    record.remote_upload_status = "uploading"
                    db.flush()
                    success, obj_key, err = self.remote_uploader.upload_backup(
                        backup_id=build.backup_id,
                        archive_path=final_path,
                    )
                    if success:
                        record.storage_location = self.remote_uploader.storage_type
                        record.remote_bucket = self.remote_uploader.bucket
                        record.remote_object_key = obj_key
                        record.remote_endpoint = self.remote_uploader.endpoint_url
                        record.remote_upload_status = "success"
                        record.remote_upload_time = datetime.now()
                        record.status = "uploaded"
                    else:
                        record.remote_upload_status = "failed"
                        record.remote_upload_retries = self.remote_uploader.max_retries
                        logger.warning(
                            f"[BackupOps] 远程上传失败: {err}, 本地备份仍然有效"
                        )

                db.commit()
                logger.info(
                    f"[BackupOps] 备份完成: id={build.backup_id}, "
                    f"type={build.backup_type}, size={comp_size / (1024 * 1024):.2f}MB, "
                    f"files={build.file_count}, duration={record.duration_seconds}s"
                )
                return record

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[BackupOps] 备份失败 {build.backup_id}: {e}\n{tb}")
            try:
                with get_db() as db:
                    rec = (
                        db.query(BackupRecord)
                        .filter(BackupRecord.backup_id == build.backup_id)
                        .first()
                    )
                    if rec:
                        rec.status = "failed"
                        rec.error_message = str(e)
                        rec.error_stack = tb
                        rec.complete_time = datetime.now()
                        rec.duration_seconds = int(
                            (rec.complete_time - start_time).total_seconds()
                        )
                        db.commit()
            except Exception:
                pass
            try:
                if build.source_dir and build.source_dir.exists():
                    shutil.rmtree(build.source_dir, ignore_errors=True)
            except Exception:
                pass
            return None

    # ================================================================
    # 内部: 各组件备份
    # ================================================================

    def _backup_component_models(
        self,
        target_dir: Path,
        incremental_since: Optional[datetime],
    ) -> ComponentBackupResult:
        result = ComponentBackupResult(component=self.COMPONENT_MODELS)
        if not self.models_dir.exists():
            result.error = "models_dir_not_exist"
            return result

        dest = target_dir / self.COMPONENT_MODELS
        dest.mkdir(parents=True, exist_ok=True)

        if incremental_since:
            files = scan_directory_modified_since(self.models_dir, incremental_since)
        else:
            files = scan_directory_files(self.models_dir)

        if not files:
            result.included = True
            result.source_path = str(self.models_dir)
            result.target_path = str(dest)
            result.file_count = 0
            return result

        total_size = 0
        file_cnt = 0
        for src_file, sz in files:
            try:
                rel = src_file.relative_to(self.models_dir)
                dst_file = dest / rel
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                total_size += sz
                file_cnt += 1
            except Exception as e:
                logger.warning(f"[BackupOps] 复制模型文件失败 {src_file}: {e}")

        result.included = True
        result.source_path = str(self.models_dir)
        result.target_path = str(dest)
        result.file_count = file_cnt
        result.size_bytes = total_size
        if total_size > 0:
            result.checksum_sha256 = self._dir_sha256_manifest(dest)
        return result

    def _backup_component_config(
        self,
        target_dir: Path,
        incremental_since: Optional[datetime],
    ) -> ComponentBackupResult:
        result = ComponentBackupResult(component=self.COMPONENT_CONFIG)
        if not self.config_dir.exists():
            result.error = "config_dir_not_exist"
            return result

        dest = target_dir / self.COMPONENT_CONFIG
        dest.mkdir(parents=True, exist_ok=True)

        if incremental_since:
            files = scan_directory_modified_since(self.config_dir, incremental_since)
        else:
            files = scan_directory_files(self.config_dir)

        if not files:
            result.included = True
            result.source_path = str(self.config_dir)
            result.target_path = str(dest)
            return result

        total_size = 0
        file_cnt = 0
        for src_file, sz in files:
            try:
                rel = src_file.relative_to(self.config_dir)
                dst_file = dest / rel
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                total_size += sz
                file_cnt += 1
            except Exception as e:
                logger.warning(f"[BackupOps] 复制配置文件失败 {src_file}: {e}")

        result.included = True
        result.source_path = str(self.config_dir)
        result.target_path = str(dest)
        result.file_count = file_cnt
        result.size_bytes = total_size
        if total_size > 0:
            result.checksum_sha256 = self._dir_sha256_manifest(dest)
        return result

    def _backup_component_database(
        self,
        target_dir: Path,
    ) -> ComponentBackupResult:
        result = ComponentBackupResult(component=self.COMPONENT_DATABASE)
        dest_dir = target_dir / self.COMPONENT_DATABASE
        dest_dir.mkdir(parents=True, exist_ok=True)

        db_config = config.get("database", {}) or {}
        host = db_config.get("host", "127.0.0.1")
        port = db_config.get("port", 3306)
        user = db_config.get("user", "root")
        password = db_config.get("password", "") or os.getenv("DB_PASSWORD", "")
        database = db_config.get("database", "bolt_preload")

        dump_file = dest_dir / "database_dump.sql"
        compressed_file = dest_dir / "database_dump.sql.gz"

        cmd = ["mysqldump", f"-h{host}", f"-P{port}", f"-u{user}"]
        env = os.environ.copy()
        if password:
            env["MYSQL_PWD"] = password
        cmd.append(database)

        try:
            logger.info(f"[BackupOps] 开始 mysqldump: database={database}")
            with open(dump_file, "w") as f:
                proc = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    timeout=600,
                    env=env,
                )
            if proc.returncode != 0:
                err = proc.stderr.decode(errors="ignore")[:500]
                logger.warning(f"[BackupOps] mysqldump 返回非零: {err}")
                result.error = f"mysqldump_failed: {err}"
                return result

            if not dump_file.exists() or dump_file.stat().st_size == 0:
                result.error = "dump_file_empty"
                return result

            with open(dump_file, "rb") as f_in, gzip.open(compressed_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

            dump_file.unlink(missing_ok=True)

            sz = compressed_file.stat().st_size
            lines = 0
            try:
                with gzip.open(compressed_file, "rt", errors="ignore") as gf:
                    for _ in gf:
                        lines += 1
            except Exception:
                pass

            result.included = True
            result.source_path = f"mysql://{host}:{port}/{database}"
            result.target_path = str(compressed_file)
            result.file_count = 1
            result.size_bytes = sz
            result.checksum_sha256 = calculate_file_sha256(compressed_file)
            build.database_dump_info = getattr(
                result, "database_dump_info", {}
            )
            result.error = ""
            logger.info(
                f"[BackupOps] DB dump 完成: size={sz/1024/1024:.2f}MB, lines~={lines}"
            )
            return result

        except FileNotFoundError:
            msg = "mysqldump_not_found"
            logger.warning(f"[BackupOps] {msg}")
            result.error = msg
            return result
        except subprocess.TimeoutExpired:
            result.error = "mysqldump_timeout"
            return result
        except Exception as e:
            logger.error(f"[BackupOps] DB dump 异常: {e}")
            result.error = f"exception: {e}"
            return result

    # ================================================================
    # 内部: 打包/解包
    # ================================================================

    def _pack_backup_directory(
        self,
        src_dir: Path,
        backup_id: str,
    ) -> Tuple[Path, int]:
        """将备份工作目录打包为压缩归档"""
        archive_base = self.temp_root / backup_id

        if self.enable_compression:
            if self.compression_format == "tar.gz":
                archive_path = archive_base.with_suffix(".tar.gz")
                with tarfile.open(archive_path, "w:gz") as tar:
                    tar.add(str(src_dir), arcname=backup_id)
            else:
                archive_path = archive_base.with_suffix(".tar")
                with tarfile.open(archive_path, "w") as tar:
                    tar.add(str(src_dir), arcname=backup_id)
        else:
            archive_path = archive_base.with_suffix(".tar")
            with tarfile.open(archive_path, "w") as tar:
                tar.add(str(src_dir), arcname=backup_id)

        size = archive_path.stat().st_size
        return archive_path, size

    def _unpack_archive(self, archive_path: Path, backup_id: str) -> Path:
        """解压归档到临时目录，返回解压后目录"""
        dest = self.temp_root / f"restore_{backup_id}_{uuid.uuid4().hex[:6]}"
        dest.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=dest)

        candidates = list(dest.glob("backup_*"))
        if candidates:
            return candidates[0]
        return dest

    def _ensure_backup_available(self, record: BackupRecord) -> Optional[Path]:
        """确保备份文件本地可用（必要时从远程下载）"""
        if record.local_path:
            p = Path(record.local_path)
            if p.exists():
                return p

        if record.remote_object_key and self.remote_uploader.enabled:
            logger.info(
                f"[BackupOps] 本地备份不存在，尝试从远程下载: "
                f"{record.remote_bucket}/{record.remote_object_key}"
            )
            restore_dir = self.backup_root / "_restored_from_remote"
            restore_dir.mkdir(parents=True, exist_ok=True)
            download_path = restore_dir / Path(record.remote_object_key).name
            ok = self.remote_uploader.download_backup(
                record.remote_object_key, download_path
            )
            if ok and download_path.exists():
                return download_path

        return None

    # ================================================================
    # 内部: 组件恢复
    # ================================================================

    def _restore_component(
        self,
        extracted_dir: Path,
        component_name: str,
        target_dir: Path,
    ) -> Tuple[bool, int, int]:
        """
        恢复单个组件目录 (models/config)
        Returns: (success, file_count, size_bytes)
        """
        comp_src = extracted_dir / component_name
        if not comp_src.exists():
            return False, 0, 0

        files = scan_directory_files(comp_src)
        if not files:
            return True, 0, 0

        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_old = target_dir.parent / f"{target_dir.name}.pre_restore_{timestamp_suffix}"
        if target_dir.exists() and any(target_dir.iterdir()):
            try:
                shutil.move(str(target_dir), str(backup_old))
                logger.info(
                    f"[BackupOps] 原{component_name}目录已重命名: {target_dir.name} -> {backup_old.name}"
                )
            except Exception as e:
                logger.warning(f"[BackupOps] 重命名原{component_name}目录失败: {e}")

        target_dir.mkdir(parents=True, exist_ok=True)

        total_size = 0
        cnt = 0
        for src_file, sz in files:
            try:
                rel = src_file.relative_to(comp_src)
                dst = target_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst)
                total_size += sz
                cnt += 1
            except Exception as e:
                logger.warning(f"[BackupOps] 恢复文件失败 {src_file}: {e}")

        return True, cnt, total_size

    def _restore_database_dump(self, extracted_dir: Path) -> bool:
        """恢复数据库 dump"""
        db_src = extracted_dir / self.COMPONENT_DATABASE / "database_dump.sql.gz"
        if not db_src.exists():
            logger.warning("[BackupOps] 未找到 database dump")
            return False

        db_config = config.get("database", {}) or {}
        host = db_config.get("host", "127.0.0.1")
        port = db_config.get("port", 3306)
        user = db_config.get("user", "root")
        password = db_config.get("password", "") or os.getenv("DB_PASSWORD", "")
        database = db_config.get("database", "bolt_preload")

        sql_file = db_src.parent / "database_dump.sql"
        try:
            with gzip.open(db_src, "rb") as gf, open(sql_file, "wb") as wf:
                shutil.copyfileobj(gf, wf)
        except Exception as e:
            logger.error(f"[BackupOps] 解压数据库 dump 失败: {e}")
            return False

        cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}", database]
        env = os.environ.copy()
        if password:
            env["MYSQL_PWD"] = password

        try:
            with open(sql_file, "r") as f:
                proc = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    timeout=1200,
                    env=env,
                )
            if proc.returncode != 0:
                err = proc.stderr.decode(errors="ignore")[:1000]
                logger.error(f"[BackupOps] mysql 恢复失败: {err}")
                return False
            logger.info("[BackupOps] 数据库恢复成功")
            return True
        except FileNotFoundError:
            logger.error("[BackupOps] mysql 客户端未找到")
            return False
        except subprocess.TimeoutExpired:
            logger.error("[BackupOps] 数据库恢复超时")
            return False
        except Exception as e:
            logger.error(f"[BackupOps] 数据库恢复异常: {e}")
            return False
        finally:
            sql_file.unlink(missing_ok=True)

    # ================================================================
    # 内部: 缓存刷新 / 校验
    # ================================================================

    def _refresh_model_cache(self) -> Tuple[str, Dict, List[str]]:
        """
        恢复后触发模型缓存刷新

        尝试:
        1. 通知 prediction_service 重新加载模型
        2. 清理进程内的模型缓存
        3. 尝试通过 event_bus 广播事件

        Returns: (status_str, detail_dict, reloaded_model_ids)
        """
        status = "success"
        detail = {}
        reloaded: List[str] = []

        try:
            try:
                from app.services.prediction_service import PredictionService
                svc = PredictionService()
                cleared = svc.clear_model_cache()
                detail["prediction_service_cache_cleared"] = cleared
                if cleared:
                    logger.info("[BackupOps] PredictionService 模型缓存已清理")
            except Exception as e:
                detail["prediction_service_error"] = str(e)
                logger.warning(f"[BackupOps] PredictionService 缓存清理失败: {e}")

            try:
                from app.services.model_version_service import ModelVersionService
                mvs = ModelVersionService()
                invalidated = mvs.invalidate_all_caches()
                detail["model_version_cache_invalidated"] = invalidated
            except Exception as e:
                detail["model_version_service_error"] = str(e)

            try:
                from app.core.event_bus import event_bus, EventType, Event
                try:
                    event_bus.publish(Event(
                        event_type=EventType.MODEL_CONFIG_CHANGED
                        if hasattr(EventType, "MODEL_CONFIG_CHANGED")
                        else getattr(EventType, "CONFIG_CHANGED", EventType.SCHEDULER_CONFIG_CHANGED),
                        data={"reason": "backup_restored", "timestamp": datetime.now().isoformat()},
                    ))
                    detail["event_published"] = True
                except Exception as e:
                    detail["event_publish_error"] = str(e)
            except Exception as e:
                detail["event_bus_error"] = str(e)

            try:
                import gc, torch, sys
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                detail["gc_and_torch_cache"] = True
            except Exception:
                pass

            for p in self.models_dir.rglob("*.pt"):
                reloaded.append(str(p.relative_to(self.models_dir)))

            detail["reload_model_count"] = len(reloaded)

        except Exception as e:
            status = "failed"
            detail["error"] = str(e)
            logger.error(f"[BackupOps] 模型缓存刷新异常: {e}")

        return status, detail, reloaded[:100]

    def _validate_restored_backup(
        self,
        record: BackupRecord,
        restored_components: List[str],
        restored_file_count: int,
    ) -> Dict:
        """恢复后简单校验"""
        result = {"passed": True, "checks": {}, "warnings": []}

        expected_components = record.component_list_dict

        for comp in expected_components:
            if comp in ("database",):
                continue
            expected_sizes = record.component_sizes_dict.get(comp, {})
            expected_cnt = expected_sizes.get("file_count", 0)

            comp_dir = self.models_dir if comp == "models" else (
                self.config_dir if comp == "config" else None
            )
            if comp_dir and expected_cnt > 0:
                actual = scan_directory_files(comp_dir)
                if len(actual) == 0:
                    result["warnings"].append(
                        f"组件[{comp}] 恢复后目录为空"
                    )
                    result["passed"] = False

        result["checks"]["restored_components"] = restored_components
        result["checks"]["restored_file_count"] = restored_file_count
        result["checks"]["expected_components"] = expected_components
        return result

    # ================================================================
    # 内部: 辅助
    # ================================================================

    def _get_chain_last_backup_time(self, chain_id: str) -> Optional[datetime]:
        with get_db() as db:
            rec = (
                db.query(BackupRecord.complete_time)
                .filter(BackupRecord.backup_chain_id == chain_id)
                .filter(BackupRecord.status.in_(["completed", "uploaded"]))
                .order_by(BackupRecord.complete_time.desc())
                .first()
            )
            return rec[0] if rec else None

    def _get_latest_chain_backup(self, chain_id: str) -> Optional[BackupRecord]:
        with get_db() as db:
            return (
                db.query(BackupRecord)
                .filter(BackupRecord.backup_chain_id == chain_id)
                .filter(BackupRecord.status.in_(["completed", "uploaded"]))
                .order_by(BackupRecord.complete_time.desc())
                .first()
            )

    def _dir_sha256_manifest(self, dir_path: Path) -> str:
        """计算目录所有文件内容的组合哈希"""
        h = hashlib.sha256()
        files = sorted([p for p in dir_path.rglob("*") if p.is_file()])
        for p in files:
            rel = str(p.relative_to(dir_path))
            h.update(rel.encode("utf-8"))
            try:
                h.update(calculate_file_sha256(p).encode("utf-8"))
            except Exception:
                pass
        return h.hexdigest()

    def _collect_model_versions_snapshot(self) -> Dict:
        """采集当前模型版本快照"""
        result = {"models": [], "timestamp": datetime.now().isoformat()}
        try:
            for p in sorted(self.models_dir.rglob("*.pt")):
                try:
                    rel = str(p.relative_to(self.models_dir))
                    st = p.stat()
                    result["models"].append({
                        "path": rel,
                        "size_bytes": st.st_size,
                        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        "sha256": calculate_file_sha256(p)[:16],
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return result

    def _collect_config_snapshot(self) -> Dict:
        """采集当前配置摘要"""
        result = {"files": [], "timestamp": datetime.now().isoformat()}
        try:
            for p in sorted(self.config_dir.rglob("*")):
                if not p.is_file():
                    continue
                try:
                    rel = str(p.relative_to(self.config_dir))
                    result["files"].append({
                        "path": rel,
                        "size_bytes": p.stat().st_size,
                    })
                except Exception:
                    continue
        except Exception:
            pass
        return result

    @staticmethod
    def _derive_restore_scope(
        restore_models: bool,
        restore_config: bool,
        restore_database: bool,
    ) -> str:
        parts = []
        if restore_models:
            parts.append("models")
        if restore_config:
            parts.append("config")
        if restore_database:
            parts.append("database")
        if len(parts) == 3:
            return "all"
        return "_".join(parts) if parts else "none"


# ============================================================
# 全局单例
# ============================================================

_backup_ops_manager_singleton: Optional[BackupOpsManager] = None


def get_backup_ops_manager() -> BackupOpsManager:
    """获取全局备份管理器单例"""
    global _backup_ops_manager_singleton
    if _backup_ops_manager_singleton is None:
        _backup_ops_manager_singleton = BackupOpsManager()
    return _backup_ops_manager_singleton
