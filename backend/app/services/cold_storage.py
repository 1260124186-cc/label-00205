"""
时序数据冷存储抽象层
====================
提供统一的冷数据存储接口，支持多种后端：
- 对象存储 (S3/OSS/MinIO) + Parquet 文件
- 时序数据库 (InfluxDB / TimescaleDB)
- 本地文件系统 (开发测试用)

主要功能：
1. Parquet 序列化/反序列化
2. 对象存储读写（可选依赖 boto3）
3. 冷数据定位与检索
4. 懒加载恢复支持
"""

import abc
import io
import os
import json
import hashlib
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger


# ============================================================
# 可选依赖处理
# ============================================================
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    logger.warning("pyarrow 未安装，Parquet 功能不可用。请执行: pip install pyarrow")

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 未安装，S3/OSS 功能不可用。请执行: pip install boto3")


# ============================================================
# 数据类定义
# ============================================================

@dataclass
class StorageConfig:
    """存储配置基类"""
    storage_type: str = "local"  # local/s3/oss/minio/influxdb/timescaledb
    compression: str = "snappy"  # none/snappy/gzip/zstd/brotli/lz4

@dataclass
class ObjectStorageConfig(StorageConfig):
    """对象存储配置"""
    storage_type: str = "s3"
    endpoint_url: Optional[str] = None  # 自定义 endpoint（MinIO/OSS）
    region: str = "us-east-1"
    bucket: str = "bolt-preload-archive"
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    base_path: str = "timeseries"  # Bucket 内的基础路径
    use_ssl: bool = True

@dataclass
class LocalStorageConfig(StorageConfig):
    """本地文件系统配置（开发/测试用）"""
    storage_type: str = "local"
    base_dir: str = "./data/cold_storage"

@dataclass
class TimeseriesDBConfig(StorageConfig):
    """时序数据库配置"""
    storage_type: str = "influxdb"  # influxdb/timescaledb
    host: str = "localhost"
    port: int = 8086
    username: Optional[str] = None
    password: Optional[str] = None
    database: str = "bolt_preload_cold"
    retention_policy: str = "7_year"

@dataclass
class ArchiveFileInfo:
    """归档文件信息"""
    storage_type: str
    bucket: str
    path: str
    file_name: str
    file_format: str = "parquet"
    size_bytes: int = 0
    record_count: int = 0
    checksum: str = ""
    min_time: Optional[datetime] = None
    max_time: Optional[datetime] = None
    compression_codec: str = "snappy"
    row_group_count: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Parquet 序列化工具
# ============================================================

class ParquetSerializer:
    """Parquet 文件序列化/反序列化工具"""

    # Schema 版本管理，便于后续演进
    SCHEMA_VERSION = "1.0"

    # 预紧力时序数据标准 Schema
    BOLT_DATA_SCHEMA = {
        "id": "int64",
        "sensor_id": "int64",
        "collector_id": "int64",
        "splitter_num": "int64",
        "position": "string",
        "ptf": "float64",
        "tenant_id": "int64",
        "create_time": "timestamp[ns]",
    }

    COMPRESSION_MAP = {
        "snappy": "SNAPPY",
        "gzip": "GZIP",
        "zstd": "ZSTD",
        "brotli": "BROTLI",
        "lz4": "LZ4",
        "none": "NONE",
    }

    def __init__(self, compression: str = "snappy"):
        if not PYARROW_AVAILABLE:
            raise RuntimeError("pyarrow 未安装，无法使用 Parquet 功能")
        self.compression = self.COMPRESSION_MAP.get(compression.lower(), "SNAPPY")

    def dataframe_to_parquet(self, df: pd.DataFrame, columns_map: Optional[Dict[str, str]] = None) -> bytes:
        """
        将 DataFrame 序列化为 Parquet 字节流

        Args:
            df: 输入 DataFrame
            columns_map: 可选的列重命名映射

        Returns:
            Parquet 格式的字节流
        """
        if columns_map:
            df = df.rename(columns=columns_map)

        if "create_time" in df.columns:
            df["create_time"] = pd.to_datetime(df["create_time"])

        table = pa.Table.from_pandas(df, preserve_index=False)

        metadata = {
            b"schema_version": self.SCHEMA_VERSION.encode(),
            b"created_at": datetime.now().isoformat().encode(),
            b"record_count": str(len(df)).encode(),
        }
        existing_meta = table.schema.metadata or {}
        existing_meta.update(metadata)
        table = table.replace_schema_metadata(existing_meta)

        buffer = io.BytesIO()
        pq.write_table(
            table,
            buffer,
            compression=self.compression,
            row_group_size=100_000,
            use_dictionary=True,
            write_statistics=True,
        )
        buffer.seek(0)
        return buffer.getvalue()

    def parquet_to_dataframe(self, data: bytes, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        将 Parquet 字节流反序列化为 DataFrame

        Args:
            data: Parquet 字节流
            columns: 可选的要读取的列子集

        Returns:
            DataFrame
        """
        buffer = io.BytesIO(data)
        table = pq.read_table(buffer, columns=columns)
        df = table.to_pandas()

        if "create_time" in df.columns:
            df["create_time"] = pd.to_datetime(df["create_time"])

        return df

    def write_parquet_file(self, df: pd.DataFrame, file_path: str, columns_map: Optional[Dict[str, str]] = None) -> ArchiveFileInfo:
        """
        将 DataFrame 写入本地 Parquet 文件，返回文件信息

        Args:
            df: 输入 DataFrame
            file_path: 目标文件路径
            columns_map: 可选的列映射

        Returns:
            ArchiveFileInfo
        """
        if columns_map:
            df = df.rename(columns=columns_map)

        if "create_time" in df.columns:
            df["create_time"] = pd.to_datetime(df["create_time"])
            min_time = df["create_time"].min() if len(df) > 0 else None
            max_time = df["create_time"].max() if len(df) > 0 else None
        else:
            min_time = max_time = None

        table = pa.Table.from_pandas(df, preserve_index=False)

        metadata = {
            b"schema_version": self.SCHEMA_VERSION.encode(),
            b"created_at": datetime.now().isoformat().encode(),
            b"record_count": str(len(df)).encode(),
            b"source_table": b"sc_bolt_data",
        }
        existing_meta = table.schema.metadata or {}
        existing_meta.update(metadata)
        table = table.replace_schema_metadata(existing_meta)

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        pq.write_table(
            table,
            file_path,
            compression=self.compression,
            row_group_size=100_000,
            use_dictionary=True,
            write_statistics=True,
        )

        file_size = os.path.getsize(file_path)
        parquet_file = pq.ParquetFile(file_path)
        row_group_count = parquet_file.num_row_groups

        checksum = self._compute_sha256(file_path)

        return ArchiveFileInfo(
            storage_type="local",
            bucket=str(Path(file_path).parent),
            path=str(Path(file_path).parent),
            file_name=Path(file_path).name,
            file_format="parquet",
            size_bytes=file_size,
            record_count=len(df),
            checksum=checksum,
            min_time=min_time.to_pydatetime() if isinstance(min_time, pd.Timestamp) else min_time,
            max_time=max_time.to_pydatetime() if isinstance(max_time, pd.Timestamp) else max_time,
            compression_codec=self.compression.lower(),
            row_group_count=row_group_count,
        )

    def read_parquet_file(self, file_path: str, columns: Optional[List[str]] = None,
                          time_range: Optional[Tuple[datetime, datetime]] = None,
                          sensor_ids: Optional[List[Union[int, str]]] = None) -> pd.DataFrame:
        """
        读取本地 Parquet 文件，支持下推谓词

        Args:
            file_path: Parquet 文件路径
            columns: 要读取的列
            time_range: (start, end) 时间范围过滤
            sensor_ids: 传感器 ID 过滤

        Returns:
            过滤后的 DataFrame
        """
        parquet_file = pq.ParquetFile(file_path)
        table = parquet_file.read(columns=columns)
        df = table.to_pandas()

        if "create_time" in df.columns:
            df["create_time"] = pd.to_datetime(df["create_time"])

            if time_range:
                start, end = time_range
                mask = (df["create_time"] >= pd.Timestamp(start)) & (df["create_time"] < pd.Timestamp(end))
                df = df[mask]

        if sensor_ids and "sensor_id" in df.columns:
            sensor_id_list = [int(s) if isinstance(s, str) and s.isdigit() else s for s in sensor_ids]
            df = df[df["sensor_id"].isin(sensor_id_list)]

        return df

    def read_parquet_bytes(self, data: bytes, columns: Optional[List[str]] = None,
                           time_range: Optional[Tuple[datetime, datetime]] = None,
                           sensor_ids: Optional[List[Union[int, str]]] = None) -> pd.DataFrame:
        """
        从字节流读取 Parquet 数据

        Args:
            data: Parquet 字节流
            columns: 列过滤
            time_range: 时间范围过滤
            sensor_ids: 传感器过滤

        Returns:
            DataFrame
        """
        buffer = io.BytesIO(data)
        table = pq.read_table(buffer, columns=columns)
        df = table.to_pandas()

        if "create_time" in df.columns:
            df["create_time"] = pd.to_datetime(df["create_time"])

            if time_range:
                start, end = time_range
                mask = (df["create_time"] >= pd.Timestamp(start)) & (df["create_time"] < pd.Timestamp(end))
                df = df[mask]

        if sensor_ids and "sensor_id" in df.columns:
            sensor_id_list = [int(s) if isinstance(s, str) and s.isdigit() else s for s in sensor_ids]
            df = df[df["sensor_id"].isin(sensor_id_list)]

        return df

    @staticmethod
    def _compute_sha256(file_path: str, chunk_size: int = 8192) -> str:
        """计算文件 SHA256 校验和"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()


# ============================================================
# 冷存储抽象基类
# ============================================================

class ColdStorageBackend(abc.ABC):
    """冷存储后端抽象基类"""

    @abc.abstractmethod
    def write_archive(self, data: Any, archive_path: str, file_name: str,
                      tenant_id: int, partition_key: str) -> ArchiveFileInfo:
        """
        写入归档数据

        Args:
            data: 数据对象（DataFrame 或其他）
            archive_path: 归档路径（不含文件名）
            file_name: 文件名
            tenant_id: 租户ID
            partition_key: 分区键 YYYYMM

        Returns:
            ArchiveFileInfo
        """
        ...

    @abc.abstractmethod
    def read_archive(self, bucket: str, archive_path: str, file_name: str,
                     columns: Optional[List[str]] = None,
                     time_range: Optional[Tuple[datetime, datetime]] = None,
                     sensor_ids: Optional[List[Union[int, str]]] = None) -> pd.DataFrame:
        """
        读取归档数据

        Args:
            bucket: 存储桶/父路径
            archive_path: 归档路径
            file_name: 文件名
            columns: 列过滤
            time_range: 时间范围过滤
            sensor_ids: 传感器ID过滤

        Returns:
            DataFrame
        """
        ...

    @abc.abstractmethod
    def delete_archive(self, bucket: str, archive_path: str, file_name: str) -> bool:
        """
        删除归档文件

        Args:
            bucket: 存储桶
            archive_path: 归档路径
            file_name: 文件名

        Returns:
            是否成功
        """
        ...

    @abc.abstractmethod
    def exists(self, bucket: str, archive_path: str, file_name: str) -> bool:
        """检查文件是否存在"""
        ...

    @abc.abstractmethod
    def verify_checksum(self, bucket: str, archive_path: str, file_name: str, expected_checksum: str) -> bool:
        """校验文件完整性"""
        ...

    @abc.abstractmethod
    def list_archives(self, bucket: str, prefix: str) -> List[Dict[str, Any]]:
        """列出指定前缀的归档文件"""
        ...


# ============================================================
# 本地文件系统后端（开发/测试）
# ============================================================

class LocalFileStorage(ColdStorageBackend):
    """本地文件系统冷存储"""

    def __init__(self, config: LocalStorageConfig):
        self.config = config
        self.base_dir = Path(config.base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.serializer = ParquetSerializer(compression=config.compression)
        logger.info(f"LocalFileStorage 初始化，基目录: {self.base_dir}")

    def _resolve_path(self, tenant_id: int, partition_key: str, archive_path: str, file_name: str) -> Path:
        """解析完整文件路径"""
        if archive_path.startswith("/"):
            archive_path = archive_path[1:]
        full_path = self.base_dir / f"tenant_{tenant_id}" / archive_path / partition_key / file_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def write_archive(self, data: Any, archive_path: str, file_name: str,
                      tenant_id: int, partition_key: str) -> ArchiveFileInfo:
        """写入 DataFrame 到本地 Parquet"""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("LocalFileStorage 只支持写入 pandas DataFrame")

        full_path = self._resolve_path(tenant_id, partition_key, archive_path, file_name)
        logger.info(f"写入归档文件: {full_path}, 记录数: {len(data)}")

        file_info = self.serializer.write_parquet_file(data, str(full_path))

        file_info.storage_type = "local"
        file_info.bucket = str(self.base_dir)
        file_info.path = str(full_path.parent.relative_to(self.base_dir))
        file_info.file_name = full_path.name

        return file_info

    def read_archive(self, bucket: str, archive_path: str, file_name: str,
                     columns: Optional[List[str]] = None,
                     time_range: Optional[Tuple[datetime, datetime]] = None,
                     sensor_ids: Optional[List[Union[int, str]]] = None) -> pd.DataFrame:
        """从本地 Parquet 读取数据"""
        if bucket:
            full_path = Path(bucket) / archive_path / file_name
        else:
            full_path = self.base_dir / archive_path / file_name

        logger.info(f"读取归档文件: {full_path}")

        if not full_path.exists():
            logger.warning(f"归档文件不存在: {full_path}")
            return pd.DataFrame()

        return self.serializer.read_parquet_file(
            str(full_path), columns=columns, time_range=time_range, sensor_ids=sensor_ids
        )

    def delete_archive(self, bucket: str, archive_path: str, file_name: str) -> bool:
        """删除本地归档文件"""
        if bucket:
            full_path = Path(bucket) / archive_path / file_name
        else:
            full_path = self.base_dir / archive_path / file_name

        if full_path.exists():
            full_path.unlink()
            logger.info(f"已删除归档文件: {full_path}")
            return True
        return False

    def exists(self, bucket: str, archive_path: str, file_name: str) -> bool:
        if bucket:
            full_path = Path(bucket) / archive_path / file_name
        else:
            full_path = self.base_dir / archive_path / file_name
        return full_path.exists()

    def verify_checksum(self, bucket: str, archive_path: str, file_name: str, expected_checksum: str) -> bool:
        if bucket:
            full_path = Path(bucket) / archive_path / file_name
        else:
            full_path = self.base_dir / archive_path / file_name

        if not full_path.exists():
            return False
        actual = ParquetSerializer._compute_sha256(str(full_path))
        return actual == expected_checksum

    def list_archives(self, bucket: str, prefix: str) -> List[Dict[str, Any]]:
        base = Path(bucket) if bucket else self.base_dir
        search_dir = base / prefix if prefix else base

        if not search_dir.exists():
            return []

        results = []
        for f in search_dir.rglob("*.parquet"):
            stat = f.stat()
            results.append({
                "path": str(f.relative_to(base)),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
            })
        return results


# ============================================================
# S3 / OSS / MinIO 对象存储后端
# ============================================================

class ObjectStorage(ColdStorageBackend):
    """S3 兼容对象存储后端（AWS S3 / 阿里云 OSS / MinIO）"""

    def __init__(self, config: ObjectStorageConfig):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 未安装，无法使用对象存储功能")

        self.config = config
        self.serializer = ParquetSerializer(compression=config.compression)

        client_kwargs = {
            "region_name": config.region,
            "use_ssl": config.use_ssl,
        }
        if config.endpoint_url:
            client_kwargs["endpoint_url"] = config.endpoint_url
        if config.access_key and config.secret_key:
            client_kwargs["aws_access_key_id"] = config.access_key
            client_kwargs["aws_secret_access_key"] = config.secret_key

        self.client = boto3.client("s3", **client_kwargs)
        self.bucket = config.bucket

        self._ensure_bucket_exists()
        logger.info(f"ObjectStorage 初始化: type={config.storage_type}, bucket={config.bucket}, endpoint={config.endpoint_url}")

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.info(f"存储桶 {self.bucket} 不存在，尝试创建")
                self.client.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={"LocationConstraint": self.config.region}
                    if self.config.region != "us-east-1" else None,
                )
            elif error_code == "403":
                logger.error(f"无权限访问存储桶 {self.bucket}")
                raise
            else:
                raise

    def _build_key(self, tenant_id: int, partition_key: str, archive_path: str, file_name: str) -> str:
        """构建 S3 对象 Key"""
        parts = [self.config.base_path.rstrip("/")]
        parts.append(f"tenant_{tenant_id}")
        if archive_path:
            parts.append(archive_path.strip("/"))
        parts.append(partition_key)
        parts.append(file_name)
        return "/".join(p for p in parts if p)

    def write_archive(self, data: Any, archive_path: str, file_name: str,
                      tenant_id: int, partition_key: str) -> ArchiveFileInfo:
        """写入 DataFrame 到对象存储"""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("ObjectStorage 只支持写入 pandas DataFrame")

        # 先写入临时 Parquet 文件
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            file_info = self.serializer.write_parquet_file(data, tmp_path)

            s3_key = self._build_key(tenant_id, partition_key, archive_path, file_name)

            with open(tmp_path, "rb") as f:
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=f,
                    ContentType="application/octet-stream",
                    Metadata={
                        "record_count": str(file_info.record_count),
                        "schema_version": ParquetSerializer.SCHEMA_VERSION,
                        "compression": file_info.compression_codec,
                        "checksum_sha256": file_info.checksum,
                        "min_time": file_info.min_time.isoformat() if file_info.min_time else "",
                        "max_time": file_info.max_time.isoformat() if file_info.max_time else "",
                    },
                )

            logger.info(f"上传归档到 S3: s3://{self.bucket}/{s3_key}, size={file_info.size_bytes}")

            file_info.storage_type = self.config.storage_type
            file_info.bucket = self.bucket
            file_info.path = str(Path(s3_key).parent)
            file_info.file_name = Path(s3_key).name
            return file_info

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def read_archive(self, bucket: str, archive_path: str, file_name: str,
                     columns: Optional[List[str]] = None,
                     time_range: Optional[Tuple[datetime, datetime]] = None,
                     sensor_ids: Optional[List[Union[int, str]]] = None) -> pd.DataFrame:
        """从对象存储读取归档数据"""
        s3_bucket = bucket or self.bucket
        s3_key = f"{archive_path.rstrip('/')}/{file_name}" if archive_path else file_name

        logger.info(f"从 S3 读取归档: s3://{s3_bucket}/{s3_key}")

        try:
            response = self.client.get_object(Bucket=s3_bucket, Key=s3_key)
            data = response["Body"].read()

            return self.serializer.read_parquet_bytes(
                data, columns=columns, time_range=time_range, sensor_ids=sensor_ids
            )
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("404", "NoSuchKey"):
                logger.warning(f"归档对象不存在: s3://{s3_bucket}/{s3_key}")
                return pd.DataFrame()
            raise

    def delete_archive(self, bucket: str, archive_path: str, file_name: str) -> bool:
        s3_bucket = bucket or self.bucket
        s3_key = f"{archive_path.rstrip('/')}/{file_name}" if archive_path else file_name

        try:
            self.client.delete_object(Bucket=s3_bucket, Key=s3_key)
            logger.info(f"已删除 S3 对象: s3://{s3_bucket}/{s3_key}")
            return True
        except ClientError:
            return False

    def exists(self, bucket: str, archive_path: str, file_name: str) -> bool:
        s3_bucket = bucket or self.bucket
        s3_key = f"{archive_path.rstrip('/')}/{file_name}" if archive_path else file_name

        try:
            self.client.head_object(Bucket=s3_bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    def verify_checksum(self, bucket: str, archive_path: str, file_name: str, expected_checksum: str) -> bool:
        s3_bucket = bucket or self.bucket
        s3_key = f"{archive_path.rstrip('/')}/{file_name}" if archive_path else file_name

        try:
            response = self.client.head_object(Bucket=s3_bucket, Key=s3_key)
            metadata = response.get("Metadata", {})
            stored_checksum = metadata.get("checksum_sha256")
            if stored_checksum:
                return stored_checksum == expected_checksum

            # 如果元数据中没有，下载完整计算
            obj = self.client.get_object(Bucket=s3_bucket, Key=s3_key)
            data = obj["Body"].read()
            actual = hashlib.sha256(data).hexdigest()
            return actual == expected_checksum
        except ClientError:
            return False

    def list_archives(self, bucket: str, prefix: str) -> List[Dict[str, Any]]:
        s3_bucket = bucket or self.bucket
        full_prefix = f"{self.config.base_path.rstrip('/')}/{prefix}" if prefix else self.config.base_path

        results = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=s3_bucket, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                results.append({
                    "path": obj["Key"],
                    "size_bytes": obj["Size"],
                    "modified": obj["LastModified"],
                    "etag": obj["ETag"].strip('"'),
                })
        return results


# ============================================================
# 时序数据库后端（InfluxDB / TimescaleDB）
# ============================================================

class TimeseriesDBStorage(ColdStorageBackend):
    """时序数据库冷存储后端（占位实现，可扩展）"""

    def __init__(self, config: TimeseriesDBConfig):
        self.config = config
        self._connected = False
        logger.warning(f"TimeseriesDBStorage 是占位实现，实际使用请集成 InfluxDB/TimescaleDB 客户端")

    def write_archive(self, data: Any, archive_path: str, file_name: str,
                      tenant_id: int, partition_key: str) -> ArchiveFileInfo:
        if isinstance(data, pd.DataFrame) and len(data) > 0:
            record_count = len(data)
            if "create_time" in data.columns:
                min_t = pd.to_datetime(data["create_time"]).min().to_pydatetime()
                max_t = pd.to_datetime(data["create_time"]).max().to_pydatetime()
            else:
                min_t = max_t = None
        else:
            record_count = 0
            min_t = max_t = None

        logger.info(f"[占位] 写入 {record_count} 条时序数据到 {self.config.storage_type}:"
                    f" db={self.config.database}, table={archive_path}, partition={partition_key}")

        return ArchiveFileInfo(
            storage_type=self.config.storage_type,
            bucket=self.config.database,
            path=archive_path,
            file_name=file_name,
            file_format="timeseries",
            record_count=record_count,
            min_time=min_t,
            max_time=max_t,
            compression_codec="tsdb",
            extra={"partition_key": partition_key, "tenant_id": tenant_id},
        )

    def read_archive(self, bucket: str, archive_path: str, file_name: str,
                     columns: Optional[List[str]] = None,
                     time_range: Optional[Tuple[datetime, datetime]] = None,
                     sensor_ids: Optional[List[Union[int, str]]] = None) -> pd.DataFrame:
        logger.info(f"[占位] 从 {self.config.storage_type} 查询: table={archive_path},"
                    f" time_range={time_range}, sensors={sensor_ids}")
        return pd.DataFrame()

    def delete_archive(self, bucket: str, archive_path: str, file_name: str) -> bool:
        logger.info(f"[占位] 从 {self.config.storage_type} 删除: {archive_path}/{file_name}")
        return True

    def exists(self, bucket: str, archive_path: str, file_name: str) -> bool:
        return True

    def verify_checksum(self, bucket: str, archive_path: str, file_name: str, expected_checksum: str) -> bool:
        return True

    def list_archives(self, bucket: str, prefix: str) -> List[Dict[str, Any]]:
        return []


# ============================================================
# 冷存储工厂
# ============================================================

class ColdStorageFactory:
    """冷存储后端工厂，根据配置创建对应后端"""

    _instances: Dict[str, ColdStorageBackend] = {}

    @classmethod
    def create(cls, config: StorageConfig) -> ColdStorageBackend:
        """
        根据配置创建冷存储后端

        Args:
            config: 存储配置对象

        Returns:
            ColdStorageBackend 实现
        """
        cache_key = f"{config.storage_type}:{getattr(config, 'bucket', '') or getattr(config, 'base_dir', '')}"

        if cache_key in cls._instances:
            return cls._instances[cache_key]

        storage_type = config.storage_type.lower()

        if storage_type == "local":
            if not isinstance(config, LocalStorageConfig):
                config = LocalStorageConfig(
                    compression=config.compression,
                    base_dir=getattr(config, "base_dir", "./data/cold_storage"),
                )
            instance = LocalFileStorage(config)

        elif storage_type in ("s3", "oss", "minio"):
            if not isinstance(config, ObjectStorageConfig):
                config = ObjectStorageConfig(
                    storage_type=storage_type,
                    compression=config.compression,
                    endpoint_url=getattr(config, "endpoint_url", None),
                    region=getattr(config, "region", "us-east-1"),
                    bucket=getattr(config, "bucket", "bolt-preload-archive"),
                    access_key=getattr(config, "access_key", None),
                    secret_key=getattr(config, "secret_key", None),
                    base_path=getattr(config, "base_path", "timeseries"),
                    use_ssl=getattr(config, "use_ssl", True),
                )
            instance = ObjectStorage(config)

        elif storage_type in ("influxdb", "timescaledb"):
            if not isinstance(config, TimeseriesDBConfig):
                config = TimeseriesDBConfig(
                    storage_type=storage_type,
                    compression=config.compression,
                    host=getattr(config, "host", "localhost"),
                    port=getattr(config, "port", 8086),
                    database=getattr(config, "database", "bolt_preload_cold"),
                )
            instance = TimeseriesDBStorage(config)

        else:
            raise ValueError(f"不支持的冷存储类型: {storage_type}")

        cls._instances[cache_key] = instance
        return instance

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> ColdStorageBackend:
        """从字典配置创建"""
        storage_type = config_dict.get("storage_type", "local").lower()

        if storage_type == "local":
            config = LocalStorageConfig(**config_dict)
        elif storage_type in ("s3", "oss", "minio"):
            config = ObjectStorageConfig(**config_dict)
        elif storage_type in ("influxdb", "timescaledb"):
            config = TimeseriesDBConfig(**config_dict)
        else:
            config = StorageConfig(**config_dict)

        return cls.create(config)

    @classmethod
    def reset(cls):
        """重置所有缓存实例（测试用）"""
        cls._instances.clear()
