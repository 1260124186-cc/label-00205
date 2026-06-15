"""
异常检测增强与闭环服务

提供异常数据的查询、确认、误报标注功能，
以及异常与预测关联（超阈值提升预警等级）。

主要功能:
- query_anomalies: 按 sensor_id、时间范围、类型查询异常
- confirm_anomaly: 确认异常为真实异常
- mark_false_positive: 标注异常为误报
- get_anomaly_statistics: 获取异常统计信息
- check_anomaly_impact_on_warning: 检查同一时段异常数是否超阈值，决定是否提升预警等级

使用示例:
    from app.services.anomaly_service import AnomalyService
    
    service = AnomalyService()
    anomalies = service.query_anomalies(sensor_id='B001')
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
from sqlalchemy import and_, or_

from app.utils.database import get_db, AnomalyData
from app.utils.config import config


class AnomalyService:
    """
    异常检测增强与闭环服务类

    提供异常数据的完整管理闭环：
    1. 异常查询与统计
    2. 异常确认与误报标注
    3. 异常与预警等级关联
    """

    def __init__(self):
        anomaly_config = config.get('anomaly_detection', {})
        self.warning_upgrade_threshold = anomaly_config.get(
            'warning_upgrade_threshold', 5
        )
        self.warning_upgrade_window_minutes = anomaly_config.get(
            'warning_upgrade_window_minutes', 60
        )
        self.max_warning_level = anomaly_config.get(
            'max_warning_level', 4
        )
        logger.info("异常检测增强服务初始化完成")

    # ---------- 异常查询 ----------

    def query_anomalies(
        self,
        sensor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        anomaly_type: Optional[str] = None,
        classification: Optional[str] = None,
        is_confirmed: Optional[bool] = None,
        is_false_positive: Optional[bool] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = 'original_time',
        sort_order: str = 'desc',
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        查询异常数据

        Args:
            sensor_id: 传感器/螺栓ID
            start_time: 开始时间
            end_time: 结束时间
            anomaly_type: 异常类型
            classification: 异常分类
            is_confirmed: 是否已确认
            is_false_positive: 是否为误报
            min_score: 最低异常评分
            max_score: 最高异常评分
            limit: 返回数量限制
            offset: 偏移量
            sort_by: 排序字段
            sort_order: 排序方向 asc/desc

        Returns:
            Tuple[int, List[Dict]]: (总数, 异常列表)
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法查询异常数据")
                    return 0, []

                query = db.query(AnomalyData)

                if sensor_id:
                    query = query.filter(AnomalyData.sensor_id == str(sensor_id))

                if start_time:
                    query = query.filter(AnomalyData.original_time >= start_time)

                if end_time:
                    query = query.filter(AnomalyData.original_time <= end_time)

                if anomaly_type:
                    query = query.filter(AnomalyData.anomaly_type == anomaly_type)

                if classification:
                    query = query.filter(AnomalyData.classification == classification)

                if is_confirmed is not None:
                    query = query.filter(AnomalyData.is_confirmed == is_confirmed)

                if is_false_positive is not None:
                    query = query.filter(AnomalyData.is_false_positive == is_false_positive)

                if min_score is not None:
                    query = query.filter(AnomalyData.anomaly_score >= min_score)

                if max_score is not None:
                    query = query.filter(AnomalyData.anomaly_score <= max_score)

                total = query.count()

                sort_column = getattr(AnomalyData, sort_by, AnomalyData.original_time)
                if sort_order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                anomalies = query.offset(offset).limit(limit).all()

                result = [self._anomaly_to_dict(a) for a in anomalies]

                logger.info(
                    f"异常查询完成: sensor_id={sensor_id}, "
                    f"总数={total}, 返回={len(result)}"
                )

                return total, result

        except Exception as e:
            logger.error(f"查询异常数据失败: {e}")
            return 0, []

    def get_anomaly_by_id(self, anomaly_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单条异常记录

        Args:
            anomaly_id: 异常记录ID

        Returns:
            Optional[Dict]: 异常记录详情
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                anomaly = db.query(AnomalyData).filter(
                    AnomalyData.id == anomaly_id
                ).first()

                if anomaly:
                    return self._anomaly_to_dict(anomaly)
                return None

        except Exception as e:
            logger.error(f"获取异常详情失败: {e}")
            return None

    # ---------- 异常确认与误报标注 ----------

    def confirm_anomaly(
        self,
        anomaly_id: int,
        confirmed_by: Optional[str] = None,
        confirm_note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        确认异常为真实异常

        Args:
            anomaly_id: 异常记录ID
            confirmed_by: 确认人ID
            confirm_note: 确认备注

        Returns:
            Optional[Dict]: 更新后的异常记录
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法确认异常")
                    return None

                anomaly = db.query(AnomalyData).filter(
                    AnomalyData.id == anomaly_id
                ).first()

                if not anomaly:
                    logger.warning(f"异常记录不存在: {anomaly_id}")
                    return None

                anomaly.is_confirmed = True
                anomaly.is_false_positive = False
                anomaly.confirmed_by = confirmed_by
                anomaly.confirmed_time = datetime.now()
                anomaly.confirm_note = confirm_note

                db.commit()
                db.refresh(anomaly)

                logger.info(
                    f"异常已确认: id={anomaly_id}, "
                    f"confirmed_by={confirmed_by}"
                )

                return self._anomaly_to_dict(anomaly)

        except Exception as e:
            logger.error(f"确认异常失败: {e}")
            return None

    def mark_false_positive(
        self,
        anomaly_id: int,
        confirmed_by: Optional[str] = None,
        confirm_note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        标注异常为误报

        Args:
            anomaly_id: 异常记录ID
            confirmed_by: 标注人ID
            confirm_note: 标注备注

        Returns:
            Optional[Dict]: 更新后的异常记录
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法标注误报")
                    return None

                anomaly = db.query(AnomalyData).filter(
                    AnomalyData.id == anomaly_id
                ).first()

                if not anomaly:
                    logger.warning(f"异常记录不存在: {anomaly_id}")
                    return None

                anomaly.is_confirmed = True
                anomaly.is_false_positive = True
                anomaly.confirmed_by = confirmed_by
                anomaly.confirmed_time = datetime.now()
                anomaly.confirm_note = confirm_note

                db.commit()
                db.refresh(anomaly)

                logger.info(
                    f"异常已标注为误报: id={anomaly_id}, "
                    f"confirmed_by={confirmed_by}"
                )

                return self._anomaly_to_dict(anomaly)

        except Exception as e:
            logger.error(f"标注误报失败: {e}")
            return None

    def batch_confirm_anomalies(
        self,
        anomaly_ids: List[int],
        confirmed_by: Optional[str] = None,
        confirm_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        批量确认异常

        Args:
            anomaly_ids: 异常记录ID列表
            confirmed_by: 确认人ID
            confirm_note: 确认备注

        Returns:
            Dict: 批量操作结果
        """
        success_count = 0
        failed_ids = []

        for anomaly_id in anomaly_ids:
            result = self.confirm_anomaly(anomaly_id, confirmed_by, confirm_note)
            if result:
                success_count += 1
            else:
                failed_ids.append(anomaly_id)

        return {
            'total': len(anomaly_ids),
            'success': success_count,
            'failed': len(failed_ids),
            'failed_ids': failed_ids,
        }

    def batch_mark_false_positives(
        self,
        anomaly_ids: List[int],
        confirmed_by: Optional[str] = None,
        confirm_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        批量标注误报

        Args:
            anomaly_ids: 异常记录ID列表
            confirmed_by: 标注人ID
            confirm_note: 标注备注

        Returns:
            Dict: 批量操作结果
        """
        success_count = 0
        failed_ids = []

        for anomaly_id in anomaly_ids:
            result = self.mark_false_positive(anomaly_id, confirmed_by, confirm_note)
            if result:
                success_count += 1
            else:
                failed_ids.append(anomaly_id)

        return {
            'total': len(anomaly_ids),
            'success': success_count,
            'failed': len(failed_ids),
            'failed_ids': failed_ids,
        }

    # ---------- 异常统计 ----------

    def get_anomaly_statistics(
        self,
        sensor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        获取异常统计信息

        Args:
            sensor_id: 传感器ID（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）

        Returns:
            Dict: 统计信息
        """
        try:
            with get_db() as db:
                if db is None:
                    return {}

                query = db.query(AnomalyData)

                if sensor_id:
                    query = query.filter(AnomalyData.sensor_id == str(sensor_id))

                if start_time:
                    query = query.filter(AnomalyData.original_time >= start_time)

                if end_time:
                    query = query.filter(AnomalyData.original_time <= end_time)

                total_count = query.count()

                confirmed_count = query.filter(
                    AnomalyData.is_confirmed == True
                ).count()

                false_positive_count = query.filter(
                    AnomalyData.is_false_positive == True
                ).count()

                true_anomaly_count = query.filter(
                    AnomalyData.is_confirmed == True,
                    AnomalyData.is_false_positive == False
                ).count()

                unconfirmed_count = total_count - confirmed_count

                type_stats = {}
                type_query = db.query(
                    AnomalyData.anomaly_type,
                    db.query(AnomalyData).filter(
                        AnomalyData.anomaly_type == AnomalyData.anomaly_type
                    ).label('count')
                ).group_by(AnomalyData.anomaly_type).all()

                for row in type_query:
                    type_stats[row[0]] = row[1] if row[1] else 0

                type_distribution = {}
                types = db.query(AnomalyData.anomaly_type).distinct().all()
                for (atype,) in types:
                    cnt = query.filter(AnomalyData.anomaly_type == atype).count()
                    type_distribution[atype] = cnt

                classification_distribution = {}
                classifications = db.query(AnomalyData.classification).distinct().all()
                for (cls,) in classifications:
                    if cls:
                        cnt = query.filter(AnomalyData.classification == cls).count()
                        classification_distribution[cls] = cnt

                stats = {
                    'total_count': total_count,
                    'confirmed_count': confirmed_count,
                    'unconfirmed_count': unconfirmed_count,
                    'false_positive_count': false_positive_count,
                    'true_anomaly_count': true_anomaly_count,
                    'false_positive_rate': (
                        false_positive_count / confirmed_count
                        if confirmed_count > 0 else 0.0
                    ),
                    'type_distribution': type_distribution,
                    'classification_distribution': classification_distribution,
                    'time_range': {
                        'start_time': start_time,
                        'end_time': end_time,
                    },
                }

                return stats

        except Exception as e:
            logger.error(f"获取异常统计失败: {e}")
            return {}

    # ---------- 异常与预警等级关联 ----------

    def get_anomaly_count_in_window(
        self,
        sensor_id: str,
        reference_time: Optional[datetime] = None,
        window_minutes: Optional[int] = None,
    ) -> int:
        """
        获取指定时间窗口内的异常数量

        Args:
            sensor_id: 传感器ID
            reference_time: 参考时间，默认当前时间
            window_minutes: 时间窗口（分钟），默认使用配置值

        Returns:
            int: 异常数量
        """
        if reference_time is None:
            reference_time = datetime.now()

        if window_minutes is None:
            window_minutes = self.warning_upgrade_window_minutes

        start_time = reference_time - timedelta(minutes=window_minutes)

        try:
            with get_db() as db:
                if db is None:
                    return 0

                count = db.query(AnomalyData).filter(
                    AnomalyData.sensor_id == str(sensor_id),
                    AnomalyData.original_time >= start_time,
                    AnomalyData.original_time <= reference_time,
                ).count()

                return count

        except Exception as e:
            logger.error(f"获取时间窗口内异常数失败: {e}")
            return 0

    def check_anomaly_impact_on_warning(
        self,
        sensor_id: str,
        current_warning_level: int,
        reference_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        检查异常数量对预警等级的影响

        如果同一时段异常数超过阈值，自动提升预警等级。

        Args:
            sensor_id: 传感器ID
            current_warning_level: 当前预警等级 (1-4)
            reference_time: 参考时间，默认当前时间

        Returns:
            Dict: 影响分析结果
                - should_upgrade: 是否需要提升预警等级
                - original_level: 原始预警等级
                - upgraded_level: 提升后的预警等级
                - anomaly_count: 时间窗口内的异常数
                - threshold: 阈值
                - window_minutes: 时间窗口（分钟）
        """
        anomaly_count = self.get_anomaly_count_in_window(
            sensor_id=sensor_id,
            reference_time=reference_time,
        )

        threshold = self.warning_upgrade_threshold
        should_upgrade = anomaly_count >= threshold and current_warning_level < self.max_warning_level

        if should_upgrade:
            upgraded_level = min(current_warning_level + 1, self.max_warning_level)
        else:
            upgraded_level = current_warning_level

        result = {
            'should_upgrade': should_upgrade,
            'original_level': current_warning_level,
            'upgraded_level': upgraded_level,
            'anomaly_count': anomaly_count,
            'threshold': threshold,
            'window_minutes': self.warning_upgrade_window_minutes,
            'sensor_id': sensor_id,
        }

        if should_upgrade:
            logger.info(
                f"预警等级提升: sensor_id={sensor_id}, "
                f"原等级={current_warning_level}, "
                f"提升后={upgraded_level}, "
                f"异常数={anomaly_count}/{threshold}"
            )

        return result

    def upgrade_warning_by_anomalies(
        self,
        sensor_id: str,
        current_warning_level: int,
        reference_time: Optional[datetime] = None,
    ) -> int:
        """
        根据异常数量提升预警等级（简便方法）

        Args:
            sensor_id: 传感器ID
            current_warning_level: 当前预警等级
            reference_time: 参考时间

        Returns:
            int: 调整后的预警等级
        """
        impact = self.check_anomaly_impact_on_warning(
            sensor_id=sensor_id,
            current_warning_level=current_warning_level,
            reference_time=reference_time,
        )
        return impact['upgraded_level']

    # ---------- 辅助方法 ----------

    def _anomaly_to_dict(self, anomaly: AnomalyData) -> Dict[str, Any]:
        """
        将异常ORM对象转换为字典

        Args:
            anomaly: 异常数据ORM对象

        Returns:
            Dict: 异常数据字典
        """
        details = None
        if anomaly.details:
            try:
                details = json.loads(anomaly.details)
            except (json.JSONDecodeError, TypeError):
                details = anomaly.details

        classification_evidence = None
        if anomaly.classification_evidence:
            try:
                classification_evidence = json.loads(anomaly.classification_evidence)
            except (json.JSONDecodeError, TypeError):
                classification_evidence = anomaly.classification_evidence

        return {
            'id': anomaly.id,
            'sensor_id': anomaly.sensor_id,
            'anomaly_value': anomaly.anomaly_value,
            'anomaly_type': anomaly.anomaly_type,
            'anomaly_score': anomaly.anomaly_score,
            'original_time': anomaly.original_time,
            'details': details,
            'classification': anomaly.classification,
            'classification_confidence': anomaly.classification_confidence,
            'collection_subtype': anomaly.collection_subtype,
            'true_anomaly_subtype': anomaly.true_anomaly_subtype,
            'classification_evidence': classification_evidence,
            'is_confirmed': anomaly.is_confirmed if anomaly.is_confirmed is not None else False,
            'is_false_positive': anomaly.is_false_positive if anomaly.is_false_positive is not None else False,
            'confirmed_by': anomaly.confirmed_by,
            'confirmed_time': anomaly.confirmed_time,
            'confirm_note': anomaly.confirm_note,
            'tenant_id': anomaly.tenant_id,
            'create_time': anomaly.create_time,
            'update_time': anomaly.update_time,
        }


_anomaly_service_instance = None


def get_anomaly_service() -> AnomalyService:
    """
    获取异常服务单例

    Returns:
        AnomalyService: 异常服务实例
    """
    global _anomaly_service_instance
    if _anomaly_service_instance is None:
        _anomaly_service_instance = AnomalyService()
    return _anomaly_service_instance
