"""
下游增量同步服务层

提供基于游标的增量数据拉取服务：
1. GET /sync/predictions - 预测结果增量同步
2. GET /sync/bolt-data - 原始螺栓数据增量同步
3. GET /sync/status - 同步游标状态查询

核心特性：
- 基于单调递增 id 的游标（since_id）或基于时间的游标（since_time）
- 租户级数据隔离
- ETag / If-None-Match 缓存机制减少带宽
- SLA 监控：增量延迟 < 1 分钟
- 数据脱敏选项（bolt-data）
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import text, and_

from app.utils.database import get_db, AbnormalPrediction, BoltData
from app.utils.config import config


@dataclass
class SyncResult:
    """同步查询结果"""
    items: List[Dict[str, Any]]
    next_since_id: int
    next_since_time: Optional[datetime]
    has_more: bool
    returned_count: int
    latest_create_time: Optional[datetime]
    data_source: str


class SyncService:
    """
    增量同步服务

    处理预测结果和原始螺栓数据的增量同步逻辑，
    包括游标管理、租户隔离、ETag生成和SLA监控。
    """

    SLA_TARGET_SECONDS = 60

    def __init__(self):
        pass

    # ---------- 预测结果增量同步 ----------

    def sync_predictions(
        self,
        tenant_id: Optional[int],
        since_id: int = 0,
        since_time: Optional[datetime] = None,
        limit: int = 500,
        node_type: Optional[str] = None,
    ) -> SyncResult:
        """
        获取预测结果增量数据

        Args:
            tenant_id: 租户ID（None表示不限制，依赖外部鉴权）
            since_id: 起始记录ID（单调递增游标）
            since_time: 起始时间（可选，基于时间的游标）
            limit: 返回记录数上限（1-10000）
            node_type: 可选按节点类型过滤 bolt/flange

        Returns:
            SyncResult: 同步结果
        """
        limit = max(1, min(limit, 10000))

        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，返回空同步结果")
                    return SyncResult(
                        items=[],
                        next_since_id=since_id,
                        next_since_time=since_time,
                        has_more=False,
                        returned_count=0,
                        latest_create_time=None,
                        data_source="mysql",
                    )

                query = db.query(AbnormalPrediction)

                conditions = []
                if tenant_id is not None:
                    conditions.append(AbnormalPrediction.tenant_id == tenant_id)

                if since_id and since_id > 0:
                    conditions.append(AbnormalPrediction.id > since_id)

                if since_time:
                    conditions.append(AbnormalPrediction.create_time > since_time)

                if node_type:
                    cn_type = "螺栓" if node_type == "bolt" else "法兰面" if node_type == "flange" else node_type
                    conditions.append(AbnormalPrediction.node_type == cn_type)

                if conditions:
                    query = query.filter(and_(*conditions))

                query = query.order_by(AbnormalPrediction.id.asc()).limit(limit + 1)

                rows = query.all()

                has_more = len(rows) > limit
                if has_more:
                    rows = rows[:limit]

                items: List[Dict[str, Any]] = []
                max_id = since_id
                latest_ct: Optional[datetime] = None

                for row in rows:
                    item = self._prediction_row_to_dict(row)
                    items.append(item)
                    if row.id > max_id:
                        max_id = row.id
                    if row.create_time and (latest_ct is None or row.create_time > latest_ct):
                        latest_ct = row.create_time

                return SyncResult(
                    items=items,
                    next_since_id=max_id,
                    next_since_time=latest_ct,
                    has_more=has_more,
                    returned_count=len(items),
                    latest_create_time=latest_ct,
                    data_source="mysql",
                )

        except Exception as e:
            logger.error(f"预测结果增量同步失败: {e}")
            return SyncResult(
                items=[],
                next_since_id=since_id,
                next_since_time=since_time,
                has_more=False,
                returned_count=0,
                latest_create_time=None,
                data_source="mysql",
            )

    @staticmethod
    def _prediction_row_to_dict(row: AbnormalPrediction) -> Dict[str, Any]:
        """将预测结果行转换为字典"""
        fault_evidence = None
        if row.fault_evidence:
            try:
                fault_evidence = json.loads(row.fault_evidence)
            except (json.JSONDecodeError, TypeError):
                fault_evidence = None

        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "bolt_id": row.bolt_id,
            "flm_id": row.flm_id,
            "node_type": row.node_type,
            "year_month": row.year_month,
            "pw_type": row.pw_type,
            "begin_time": row.begin_time,
            "end_time": row.end_time,
            "confidence": row.confidence,
            "rec_measures": row.rec_measures,
            "recent_time": row.recent_time,
            "fault_type": row.fault_type,
            "fault_confidence": row.fault_confidence,
            "fault_evidence": fault_evidence,
            "create_time": row.create_time,
        }

    # ---------- 螺栓原始数据增量同步 ----------

    def sync_bolt_data(
        self,
        tenant_id: Optional[int],
        since_id: int = 0,
        since_time: Optional[datetime] = None,
        limit: int = 500,
        desensitize: bool = False,
        sensor_ids: Optional[List[int]] = None,
    ) -> SyncResult:
        """
        获取螺栓原始数据增量

        Args:
            tenant_id: 租户ID
            since_id: 起始记录ID
            since_time: 起始时间
            limit: 返回记录数上限
            desensitize: 是否脱敏（隐藏/哈希敏感字段）
            sensor_ids: 可选按传感器ID过滤

        Returns:
            SyncResult: 同步结果
        """
        limit = max(1, min(limit, 10000))

        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，返回空螺栓数据同步结果")
                    return SyncResult(
                        items=[],
                        next_since_id=since_id,
                        next_since_time=since_time,
                        has_more=False,
                        returned_count=0,
                        latest_create_time=None,
                        data_source="mysql",
                    )

                query = db.query(BoltData)

                conditions = []
                if tenant_id is not None:
                    conditions.append(BoltData.tenant_id == tenant_id)

                if since_id and since_id > 0:
                    conditions.append(BoltData.id > since_id)

                if since_time:
                    conditions.append(BoltData.create_time > since_time)

                if sensor_ids:
                    conditions.append(BoltData.sensor_id.in_(sensor_ids))

                if conditions:
                    query = query.filter(and_(*conditions))

                query = query.order_by(BoltData.id.asc()).limit(limit + 1)

                rows = query.all()

                has_more = len(rows) > limit
                if has_more:
                    rows = rows[:limit]

                items: List[Dict[str, Any]] = []
                max_id = since_id
                latest_ct: Optional[datetime] = None

                for row in rows:
                    item = self._bolt_data_row_to_dict(row, desensitize)
                    items.append(item)
                    if row.id > max_id:
                        max_id = row.id
                    if row.create_time and (latest_ct is None or row.create_time > latest_ct):
                        latest_ct = row.create_time

                return SyncResult(
                    items=items,
                    next_since_id=max_id,
                    next_since_time=latest_ct,
                    has_more=has_more,
                    returned_count=len(items),
                    latest_create_time=latest_ct,
                    data_source="mysql",
                )

        except Exception as e:
            logger.error(f"螺栓原始数据增量同步失败: {e}")
            return SyncResult(
                items=[],
                next_since_id=since_id,
                next_since_time=since_time,
                has_more=False,
                returned_count=0,
                latest_create_time=None,
                data_source="mysql",
            )

    @staticmethod
    def _bolt_data_row_to_dict(row: BoltData, desensitize: bool = False) -> Dict[str, Any]:
        """将螺栓原始数据行转换为字典（支持脱敏）"""
        missing_channels = None
        if row.missing_channels:
            try:
                missing_channels = json.loads(row.missing_channels)
            except (json.JSONDecodeError, TypeError):
                missing_channels = None

        item = {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "sensor_id": row.sensor_id,
            "collector_id": row.collector_id,
            "splitter_num": row.splitter_num,
            "position": row.position,
            "ptf": row.ptf,
            "temperature": row.temperature,
            "humidity": row.humidity,
            "vibration": row.vibration,
            "torque": row.torque,
            "pressure": row.pressure,
            "data_quality": row.data_quality,
            "missing_channels": missing_channels,
            "create_time": row.create_time,
        }

        if desensitize:
            if row.collector_id is not None:
                item["collector_id"] = int(hashlib.md5(str(row.collector_id).encode()).hexdigest()[:8], 16) % 1000000
            if row.splitter_num is not None:
                item["splitter_num"] = int(hashlib.md5(str(row.splitter_num).encode()).hexdigest()[:8], 16) % 1000000
            if row.position:
                item["position"] = hashlib.sha256(row.position.encode()).hexdigest()[:16]

        return item

    # ---------- ETag 生成 ----------

    @staticmethod
    def generate_etag(
        resource: str,
        tenant_id: Optional[int],
        next_since_id: int,
        returned_count: int,
    ) -> str:
        """
        生成 ETag 值

        ETag 基于资源名、租户ID、游标位置和返回记录数生成，
        用于 If-None-Match 缓存机制。

        Args:
            resource: 资源类型 predictions / bolt-data
            tenant_id: 租户ID
            next_since_id: 下次游标位置
            returned_count: 返回记录数

        Returns:
            str: ETag 值（带引号的格式）
        """
        raw = f"{resource}:{tenant_id}:{next_since_id}:{returned_count}:{datetime.now().strftime('%Y%m%d%H%M')}"
        etag = hashlib.sha256(raw.encode()).hexdigest()[:32]
        return f'"{etag}"'

    # ---------- SLA 计算 ----------

    @staticmethod
    def calculate_sla_latency(latest_create_time: Optional[datetime]) -> Optional[float]:
        """
        计算增量延迟（秒）

        Args:
            latest_create_time: 最新记录的创建时间

        Returns:
            Optional[float]: 延迟秒数，无法计算时返回 None
        """
        if not latest_create_time:
            return None
        delta = datetime.now() - latest_create_time
        latency = delta.total_seconds()
        if latency < 0:
            return 0.0
        return round(latency, 2)

    # ---------- 游标状态查询 ----------

    def get_sync_status(
        self,
        tenant_id: Optional[int],
    ) -> Dict[str, Any]:
        """
        获取租户的同步状态概览

        返回预测结果和原始数据的最新游标位置，用于监控。
        """
        result: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "server_time": datetime.now(),
            "sla_target_seconds": self.SLA_TARGET_SECONDS,
            "predictions_cursor": None,
            "bolt_data_cursor": None,
        }

        try:
            with get_db() as db:
                if db is None:
                    return result

                pred_cursor = self._get_resource_cursor(db, AbnormalPrediction, tenant_id, "predictions")
                bolt_cursor = self._get_resource_cursor(db, BoltData, tenant_id, "bolt-data")

                result["predictions_cursor"] = pred_cursor
                result["bolt_data_cursor"] = bolt_cursor

        except Exception as e:
            logger.warning(f"获取同步状态失败: {e}")

        return result

    @staticmethod
    def _get_resource_cursor(db, model, tenant_id: Optional[int], resource: str) -> Optional[Dict[str, Any]]:
        """查询单个资源的游标状态"""
        try:
            query = db.query(model)
            if tenant_id is not None:
                query = query.filter(model.tenant_id == tenant_id)

            total_count = query.count()

            latest = query.order_by(model.id.desc()).first()

            cursor = {
                "tenant_id": tenant_id,
                "resource": resource,
                "last_since_id": latest.id if latest else None,
                "last_since_time": latest.create_time if latest and hasattr(latest, 'create_time') else None,
                "last_sync_time": datetime.now(),
                "total_consumed": total_count,
            }
            return cursor
        except Exception as e:
            logger.warning(f"获取 {resource} 游标失败: {e}")
            return None


_sync_service_instance: Optional[SyncService] = None


def get_sync_service() -> SyncService:
    """获取同步服务单例"""
    global _sync_service_instance
    if _sync_service_instance is None:
        _sync_service_instance = SyncService()
    return _sync_service_instance
