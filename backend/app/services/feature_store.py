"""
特征存储模块 - Feature Store

负责特征向量的版本化管理、快照存储和检索，保证训练可复现和推理分析。

主要功能:
1. 特征 Schema 版本管理 - 定义和校验特征结构
2. 特征快照存储 - 训练/推理时的特征向量持久化
3. 版本兼容性检查 - 拒绝不兼容版本的混训
4. 异步写入 - 推理时异步写入特征快照
5. 数据溯源 - 通过 source_window_hash 追踪输入数据

使用示例:
    from app.services.feature_store import FeatureStore, get_feature_store

    store = get_feature_store()

    # 获取最新特征快照
    snapshot = store.get_latest_snapshot(node_id="B001", node_type="bolt")

    # 计算并保存特征（调试用）
    snapshot = store.compute_and_save(
        node_id="B001",
        node_type="bolt",
        data=time_series_data,
        timestamps=timestamps,
        feature_version="v1.0",
        data_source="debug"
    )

    # 训练时批量加载特征（保证可复现）
    features = store.load_training_features(
        node_ids=["B001", "B002"],
        feature_version="v1.0",
        start_time="2025-01-01",
        end_time="2025-06-01"
    )

    # 检查版本兼容性
    is_compatible = store.check_version_compatibility("v1.0", "v1.1")
"""

import json
import hashlib
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.utils.database import (
    get_db,
    FeatureSnapshot,
    FeatureSchemaVersion,
)
from app.services.feature_engineering import FeatureEngineer
from app.middleware import get_effective_tenant_id


@dataclass
class FeatureVersionInfo:
    """特征版本信息"""
    version: str
    dimension: int
    feature_names: List[str]
    feature_types: List[str]
    description: str
    is_active: bool
    compatible_versions: List[str]
    breaking_change: bool

    @classmethod
    def from_orm(cls, obj: FeatureSchemaVersion) -> 'FeatureVersionInfo':
        return cls(
            version=obj.version,
            dimension=obj.dimension,
            feature_names=json.loads(obj.feature_names) if obj.feature_names else [],
            feature_types=json.loads(obj.feature_types) if obj.feature_types else [],
            description=obj.description or "",
            is_active=bool(obj.is_active),
            compatible_versions=json.loads(obj.compatible_versions) if obj.compatible_versions else [],
            breaking_change=bool(obj.breaking_change),
        )


@dataclass
class FeatureSnapshotData:
    """特征快照数据"""
    id: Optional[int]
    node_id: str
    node_type: str
    compute_time: datetime
    feature_version: str
    vector: np.ndarray
    vector_dim: int
    source_window_hash: str
    source_window_start: Optional[datetime]
    source_window_end: Optional[datetime]
    data_source: str
    model_version: Optional[str]
    prediction_result: Optional[Dict[str, Any]]
    is_used_for_training: bool
    training_session_id: Optional[str]
    create_time: datetime

    @classmethod
    def from_orm(cls, obj: FeatureSnapshot) -> 'FeatureSnapshotData':
        vector = None
        if obj.vector_bin:
            try:
                vector = pickle.loads(obj.vector_bin)
            except Exception as e:
                logger.warning(f"二进制特征向量解析失败，尝试JSON: {e}")
        if vector is None and obj.vector:
            try:
                vector = np.array(json.loads(obj.vector), dtype=np.float32)
            except Exception as e:
                logger.warning(f"JSON特征向量解析失败: {e}")
                vector = np.array([], dtype=np.float32)

        return cls(
            id=obj.id,
            node_id=obj.node_id,
            node_type=obj.node_type,
            compute_time=obj.compute_time,
            feature_version=obj.feature_version,
            vector=vector if vector is not None else np.array([], dtype=np.float32),
            vector_dim=obj.vector_dim or 0,
            source_window_hash=obj.source_window_hash or "",
            source_window_start=obj.source_window_start,
            source_window_end=obj.source_window_end,
            data_source=obj.data_source or "",
            model_version=obj.model_version,
            prediction_result=json.loads(obj.prediction_result) if obj.prediction_result else None,
            is_used_for_training=bool(obj.is_used_for_training),
            training_session_id=obj.training_session_id,
            create_time=obj.create_time,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "compute_time": self.compute_time.isoformat() if self.compute_time else None,
            "feature_version": self.feature_version,
            "vector": self.vector.tolist(),
            "vector_dim": self.vector_dim,
            "source_window_hash": self.source_window_hash,
            "source_window_start": self.source_window_start.isoformat() if self.source_window_start else None,
            "source_window_end": self.source_window_end.isoformat() if self.source_window_end else None,
            "data_source": self.data_source,
            "model_version": self.model_version,
            "prediction_result": self.prediction_result,
            "is_used_for_training": self.is_used_for_training,
            "training_session_id": self.training_session_id,
            "create_time": self.create_time.isoformat() if self.create_time else None,
        }


class IncompatibleFeatureVersionError(Exception):
    """特征版本不兼容异常"""
    pass


class FeatureStore:
    """
    特征存储服务

    提供特征版本管理、快照存储/检索、版本兼容性检查等功能。
    """

    DEFAULT_VERSION = "v1.0"

    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self._version_cache: Dict[str, FeatureVersionInfo] = {}
        logger.info("特征存储服务初始化完成")

    # ============================================================
    # 特征 Schema 版本管理
    # ============================================================

    def get_version_info(self, version: str) -> Optional[FeatureVersionInfo]:
        """
        获取指定版本的特征 Schema 信息

        Args:
            version: 特征版本号，如 "v1.0"

        Returns:
            FeatureVersionInfo 或 None
        """
        if version in self._version_cache:
            return self._version_cache[version]

        with get_db() as db:
            obj = db.query(FeatureSchemaVersion).filter(
                FeatureSchemaVersion.version == version
            ).first()
            if obj:
                info = FeatureVersionInfo.from_orm(obj)
                self._version_cache[version] = info
                return info
        return None

    def get_active_versions(self) -> List[FeatureVersionInfo]:
        """
        获取所有活跃的特征版本

        Returns:
            FeatureVersionInfo 列表
        """
        with get_db() as db:
            objs = db.query(FeatureSchemaVersion).filter(
                FeatureSchemaVersion.is_active == True
            ).order_by(FeatureSchemaVersion.create_time.desc()).all()
            return [FeatureVersionInfo.from_orm(obj) for obj in objs]

    def get_latest_version(self) -> Optional[FeatureVersionInfo]:
        """
        获取最新的活跃特征版本

        Returns:
            最新的 FeatureVersionInfo 或 None
        """
        versions = self.get_active_versions()
        return versions[0] if versions else None

    def check_version_compatibility(
        self,
        version_a: str,
        version_b: str
    ) -> bool:
        """
        检查两个特征版本是否兼容

        Args:
            version_a: 版本A
            version_b: 版本B

        Returns:
            True 表示兼容，False 表示不兼容

        Raises:
            ValueError: 如果任一版本不存在
        """
        if version_a == version_b:
            return True

        info_a = self.get_version_info(version_a)
        info_b = self.get_version_info(version_b)

        if not info_a or not info_b:
            raise ValueError(f"特征版本不存在: {version_a if not info_a else version_b}")

        if version_b in info_a.compatible_versions:
            return True
        if version_a in info_b.compatible_versions:
            return True

        return False

    def assert_training_compatibility(
        self,
        target_version: str,
        snapshot_versions: List[str]
    ) -> None:
        """
        断言训练时的特征版本兼容性

        如果有任何快照版本与目标版本不兼容，则抛出异常。

        Args:
            target_version: 训练使用的目标特征版本
            snapshot_versions: 实际快照的版本列表

        Raises:
            IncompatibleFeatureVersionError: 存在不兼容版本
        """
        incompatible = []
        for v in set(snapshot_versions):
            if v != target_version and not self.check_version_compatibility(target_version, v):
                incompatible.append(v)

        if incompatible:
            raise IncompatibleFeatureVersionError(
                f"特征版本不兼容，拒绝混训。"
                f"目标版本: {target_version}, "
                f"不兼容版本: {incompatible}. "
                f"请统一特征版本或使用兼容版本。"
            )

    # ============================================================
    # 特征向量计算
    # ============================================================

    def _compute_source_window_hash(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None
    ) -> str:
        """
        计算输入数据窗口的哈希值，用于去重和溯源

        Args:
            data: 输入数据数组
            timestamps: 时间戳数组（可选）

        Returns:
            SHA256 哈希字符串
        """
        hasher = hashlib.sha256()

        if timestamps is not None and len(timestamps) > 0:
            ts_str = str([pd.Timestamp(t).isoformat() for t in timestamps]).encode()
            hasher.update(ts_str)

        hasher.update(data.tobytes())
        return hasher.hexdigest()

    def _extract_working_condition_features(
        self,
        timestamps: Optional[np.ndarray] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        提取工况特征（v1.1 新增）

        Args:
            timestamps: 时间戳数组
            extra_data: 额外的工况数据

        Returns:
            7维工况特征数组
        """
        wc_features = np.zeros(7, dtype=np.float32)

        if timestamps is not None and len(timestamps) > 0:
            if isinstance(timestamps[0], datetime):
                hours = [t.hour for t in timestamps]
            else:
                hours = [pd.Timestamp(t).hour for t in timestamps]

            avg_hour = np.mean(hours)
            if 6 <= avg_hour < 14:
                wc_features[0] = 1.0
            elif 14 <= avg_hour < 22:
                wc_features[1] = 1.0
            else:
                wc_features[2] = 1.0

            if isinstance(timestamps[0], datetime):
                months = [t.month for t in timestamps]
            else:
                months = [pd.Timestamp(t).month for t in timestamps]
            avg_month = np.mean(months)
            if 3 <= avg_month <= 5:
                wc_features[6] = 0.3
            elif 6 <= avg_month <= 8:
                wc_features[6] = 1.0
            elif 9 <= avg_month <= 11:
                wc_features[6] = 0.3
            else:
                wc_features[6] = -0.5

        if extra_data:
            if 'temperature' in extra_data:
                wc_features[0] = float(extra_data['temperature']) / 100.0
            if 'humidity' in extra_data:
                wc_features[1] = float(extra_data['humidity']) / 100.0
            if 'pressure' in extra_data:
                wc_features[2] = float(extra_data['pressure']) / 10.0
            if 'vibration' in extra_data:
                wc_features[3] = float(extra_data['vibration']) / 5.0
            if 'operating_mode' in extra_data:
                wc_features[4] = float(extra_data['operating_mode'])
            if 'load_factor' in extra_data:
                wc_features[5] = float(extra_data['load_factor'])

        return wc_features

    def compute_features(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        feature_version: str = "v1.0",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, str]:
        """
        计算特征向量

        Args:
            data: 输入时间序列数据
            timestamps: 时间戳数组
            feature_version: 目标特征版本
            extra_data: 额外的工况数据（v1.1 需要）

        Returns:
            (特征向量, source_window_hash)

        Raises:
            ValueError: 如果特征版本不存在
        """
        version_info = self.get_version_info(feature_version)
        if not version_info:
            raise ValueError(f"特征版本不存在: {feature_version}")

        feature_set = self.feature_engineer.extract_features(data, timestamps)
        base_features = feature_set.combined_features

        if feature_version == "v1.1":
            wc_features = self._extract_working_condition_features(timestamps, extra_data)
            features = np.concatenate([base_features, wc_features])
        else:
            features = base_features

        if len(features) != version_info.dimension:
            logger.warning(
                f"特征维度不匹配: 期望 {version_info.dimension}, "
                f"实际 {len(features)}. 自动填充/截断。"
            )
            if len(features) < version_info.dimension:
                features = np.pad(features, (0, version_info.dimension - len(features)))
            else:
                features = features[:version_info.dimension]

        features = features.astype(np.float32)
        source_hash = self._compute_source_window_hash(data, timestamps)

        return features, source_hash

    # ============================================================
    # 特征快照存储
    # ============================================================

    def save_snapshot(
        self,
        node_id: str,
        node_type: str,
        feature_vector: np.ndarray,
        feature_version: str,
        source_window_hash: str,
        compute_time: Optional[datetime] = None,
        source_window_start: Optional[datetime] = None,
        source_window_end: Optional[datetime] = None,
        data_source: str = "inference",
        model_version: Optional[str] = None,
        prediction_result: Optional[Dict[str, Any]] = None,
        training_session_id: Optional[str] = None,
        is_used_for_training: bool = False,
        tenant_id: Optional[int] = None,
    ) -> Optional[FeatureSnapshotData]:
        """
        保存特征快照

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            feature_vector: 特征向量
            feature_version: 特征版本
            source_window_hash: 输入窗口哈希
            compute_time: 计算时间（默认当前时间）
            source_window_start: 窗口起始时间
            source_window_end: 窗口结束时间
            data_source: 数据来源 training/inference/debug
            model_version: 关联的模型版本
            prediction_result: 关联的预测结果
            training_session_id: 训练会话ID
            is_used_for_training: 是否用于训练
            tenant_id: 租户ID

        Returns:
            保存的 FeatureSnapshotData，如遇唯一键冲突则返回 None
        """
        if tenant_id is None:
            tenant_id = get_effective_tenant_id()

        compute_time = compute_time or datetime.now()

        vector_json = json.dumps(feature_vector.tolist(), ensure_ascii=False)
        vector_bin = pickle.dumps(feature_vector)

        snapshot = FeatureSnapshot(
            node_id=node_id,
            node_type=node_type,
            compute_time=compute_time,
            feature_version=feature_version,
            vector=vector_json,
            vector_bin=vector_bin,
            vector_dim=len(feature_vector),
            source_window_hash=source_window_hash,
            source_window_start=source_window_start,
            source_window_end=source_window_end,
            data_source=data_source,
            model_version=model_version,
            prediction_result=json.dumps(prediction_result, ensure_ascii=False) if prediction_result else None,
            is_used_for_training=is_used_for_training,
            training_session_id=training_session_id,
            tenant_id=tenant_id,
        )

        try:
            with get_db() as db:
                db.add(snapshot)
                db.commit()
                db.refresh(snapshot)
                logger.debug(
                    f"特征快照已保存: node={node_id}, version={feature_version}, "
                    f"dim={len(feature_vector)}, source={data_source}"
                )
                return FeatureSnapshotData.from_orm(snapshot)
        except IntegrityError:
            logger.debug(
                f"特征快照已存在（唯一键冲突）: node={node_id}, "
                f"compute_time={compute_time}, version={feature_version}, "
                f"hash={source_window_hash}"
            )
            return None
        except Exception as e:
            logger.error(f"保存特征快照失败: {e}")
            raise

    def compute_and_save(
        self,
        node_id: str,
        node_type: str,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        feature_version: str = "v1.0",
        data_source: str = "debug",
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> FeatureSnapshotData:
        """
        计算特征并保存快照（调试接口用）

        Args:
            node_id: 节点ID
            node_type: 节点类型
            data: 输入数据
            timestamps: 时间戳
            feature_version: 特征版本
            data_source: 数据来源
            extra_data: 额外工况数据
            **kwargs: 其他传递给 save_snapshot 的参数

        Returns:
            FeatureSnapshotData
        """
        features, source_hash = self.compute_features(
            data=data,
            timestamps=timestamps,
            feature_version=feature_version,
            extra_data=extra_data
        )

        source_window_start = None
        source_window_end = None
        if timestamps is not None and len(timestamps) > 0:
            if isinstance(timestamps[0], datetime):
                source_window_start = timestamps[0]
                source_window_end = timestamps[-1]
            else:
                source_window_start = pd.Timestamp(timestamps[0]).to_pydatetime()
                source_window_end = pd.Timestamp(timestamps[-1]).to_pydatetime()

        result = self.save_snapshot(
            node_id=node_id,
            node_type=node_type,
            feature_vector=features,
            feature_version=feature_version,
            source_window_hash=source_hash,
            source_window_start=source_window_start,
            source_window_end=source_window_end,
            data_source=data_source,
            **kwargs
        )

        if result is None:
            existing = self.get_snapshot_by_hash(node_id, source_hash, feature_version)
            if existing:
                return existing
            raise RuntimeError("特征快照保存失败且无法找到已存在的快照")

        return result

    # ============================================================
    # 特征快照查询
    # ============================================================

    def get_latest_snapshot(
        self,
        node_id: str,
        node_type: Optional[str] = None,
        feature_version: Optional[str] = None
    ) -> Optional[FeatureSnapshotData]:
        """
        获取指定节点的最新特征快照

        Args:
            node_id: 节点ID
            node_type: 节点类型（可选）
            feature_version: 特征版本（可选，默认返回最新版本的）

        Returns:
            FeatureSnapshotData 或 None
        """
        tenant_id = get_effective_tenant_id()

        with get_db() as db:
            query = db.query(FeatureSnapshot).filter(
                FeatureSnapshot.node_id == node_id,
                FeatureSnapshot.tenant_id == tenant_id
            )

            if node_type:
                query = query.filter(FeatureSnapshot.node_type == node_type)

            if feature_version:
                query = query.filter(FeatureSnapshot.feature_version == feature_version)

            obj = query.order_by(
                FeatureSnapshot.compute_time.desc(),
                FeatureSnapshot.id.desc()
            ).first()

            return FeatureSnapshotData.from_orm(obj) if obj else None

    def get_snapshot_by_hash(
        self,
        node_id: str,
        source_window_hash: str,
        feature_version: str
    ) -> Optional[FeatureSnapshotData]:
        """
        通过 source_window_hash 查询特征快照

        Args:
            node_id: 节点ID
            source_window_hash: 窗口哈希
            feature_version: 特征版本

        Returns:
            FeatureSnapshotData 或 None
        """
        with get_db() as db:
            obj = db.query(FeatureSnapshot).filter(
                FeatureSnapshot.node_id == node_id,
                FeatureSnapshot.source_window_hash == source_window_hash,
                FeatureSnapshot.feature_version == feature_version
            ).first()
            return FeatureSnapshotData.from_orm(obj) if obj else None

    def list_snapshots(
        self,
        node_id: str,
        node_type: Optional[str] = None,
        feature_version: Optional[str] = None,
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[FeatureSnapshotData], int]:
        """
        列出特征快照

        Args:
            node_id: 节点ID
            node_type: 节点类型
            feature_version: 特征版本
            start_time: 起始时间
            end_time: 结束时间
            limit: 返回数量上限
            offset: 偏移量

        Returns:
            (快照列表, 总数)
        """
        tenant_id = get_effective_tenant_id()

        if isinstance(start_time, str):
            start_time = pd.Timestamp(start_time).to_pydatetime()
        if isinstance(end_time, str):
            end_time = pd.Timestamp(end_time).to_pydatetime()

        with get_db() as db:
            query = db.query(FeatureSnapshot).filter(
                FeatureSnapshot.node_id == node_id,
                FeatureSnapshot.tenant_id == tenant_id
            )

            if node_type:
                query = query.filter(FeatureSnapshot.node_type == node_type)
            if feature_version:
                query = query.filter(FeatureSnapshot.feature_version == feature_version)
            if start_time:
                query = query.filter(FeatureSnapshot.compute_time >= start_time)
            if end_time:
                query = query.filter(FeatureSnapshot.compute_time <= end_time)

            total = query.count()

            objs = query.order_by(FeatureSnapshot.compute_time.desc()) \
                .offset(offset).limit(limit).all()

            return [FeatureSnapshotData.from_orm(obj) for obj in objs], total

    def load_training_features(
        self,
        node_ids: List[str],
        feature_version: str,
        node_type: str = "bolt",
        start_time: Optional[Union[datetime, str]] = None,
        end_time: Optional[Union[datetime, str]] = None,
        check_compatibility: bool = True
    ) -> Tuple[np.ndarray, List[FeatureSnapshotData]]:
        """
        加载训练用的特征数据集

        Args:
            node_ids: 节点ID列表
            feature_version: 目标特征版本
            node_type: 节点类型
            start_time: 起始时间
            end_time: 结束时间
            check_compatibility: 是否检查版本兼容性

        Returns:
            (特征矩阵 (n_samples, n_features), 快照数据列表)

        Raises:
            IncompatibleFeatureVersionError: 存在不兼容版本
        """
        tenant_id = get_effective_tenant_id()

        if isinstance(start_time, str):
            start_time = pd.Timestamp(start_time).to_pydatetime()
        if isinstance(end_time, str):
            end_time = pd.Timestamp(end_time).to_pydatetime()

        with get_db() as db:
            query = db.query(FeatureSnapshot).filter(
                FeatureSnapshot.node_id.in_(node_ids),
                FeatureSnapshot.node_type == node_type,
                FeatureSnapshot.tenant_id == tenant_id
            )

            if start_time:
                query = query.filter(FeatureSnapshot.compute_time >= start_time)
            if end_time:
                query = query.filter(FeatureSnapshot.compute_time <= end_time)

            objs = query.order_by(
                FeatureSnapshot.node_id,
                FeatureSnapshot.compute_time
            ).all()

            if check_compatibility and objs:
                versions = [obj.feature_version for obj in objs]
                self.assert_training_compatibility(feature_version, versions)

            snapshots = [FeatureSnapshotData.from_orm(obj) for obj in objs]

            if not snapshots:
                return np.array([], dtype=np.float32), []

            version_info = self.get_version_info(feature_version)
            dim = version_info.dimension if version_info else snapshots[0].vector_dim

            feature_matrix = np.zeros((len(snapshots), dim), dtype=np.float32)
            for i, snap in enumerate(snapshots):
                vec = snap.vector
                if len(vec) < dim:
                    vec = np.pad(vec, (0, dim - len(vec)))
                elif len(vec) > dim:
                    vec = vec[:dim]
                feature_matrix[i] = vec

            logger.info(
                f"加载训练特征完成: {len(snapshots)} 条, "
                f"维度={dim}, 节点数={len(node_ids)}, "
                f"版本={feature_version}"
            )

            return feature_matrix, snapshots

    # ============================================================
    # 异步写入支持
    # ============================================================

    def async_save_snapshot(
        self,
        background_tasks,
        **kwargs
    ) -> None:
        """
        异步保存特征快照（用于推理时）

        Args:
            background_tasks: FastAPI BackgroundTasks 对象
            **kwargs: 传递给 save_snapshot 的参数
        """
        try:
            background_tasks.add_task(self.save_snapshot, **kwargs)
            logger.debug(f"特征快照异步写入任务已添加: node={kwargs.get('node_id')}")
        except Exception as e:
            logger.warning(f"添加特征快照异步任务失败: {e}")

    def mark_used_for_training(
        self,
        snapshot_ids: List[int],
        training_session_id: str
    ) -> int:
        """
        标记快照为已用于训练

        Args:
            snapshot_ids: 快照ID列表
            training_session_id: 训练会话ID

        Returns:
            更新的记录数
        """
        if not snapshot_ids:
            return 0

        with get_db() as db:
            updated = db.query(FeatureSnapshot).filter(
                FeatureSnapshot.id.in_(snapshot_ids)
            ).update({
                FeatureSnapshot.is_used_for_training: True,
                FeatureSnapshot.training_session_id: training_session_id
            })
            db.commit()
            logger.info(
                f"标记 {updated} 条特征快照用于训练: session={training_session_id}"
            )
            return updated


_feature_store_instance: Optional[FeatureStore] = None


def get_feature_store() -> FeatureStore:
    """获取特征存储单例实例"""
    global _feature_store_instance
    if _feature_store_instance is None:
        _feature_store_instance = FeatureStore()
    return _feature_store_instance
