"""
工单复测服务模块

负责复测数据上传、复测后自动再预测、预测结果对比。

主要功能:
- create_retest_record: 创建复测记录
- get_retest_record: 获取复测记录详情
- list_retest_records: 查询复测记录列表
- update_retest_record: 更新复测记录
- repredict_after_retest: 复测后自动再预测
- compare_predictions: 预测对比
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger

from app.utils.database import (
    get_db,
    WorkOrderRetestRecord,
    WorkOrderPredictionCompare,
    WorkOrder,
    AlertEvent,
)


class RetestService:
    """
    复测服务类
    """

    def __init__(self):
        logger.info("复测服务初始化完成")

    def create_retest_record(
        self,
        work_order_id: int,
        retest_time: datetime = None,
        retester_id: str = None,
        retester_name: str = None,
        retest_result: str = 'pending',
        measured_value: float = None,
        data_points: List[List[Any]] = None,
        before_risk_score: float = None,
        after_risk_score: float = None,
        status_after_retest: str = None,
        confidence: float = None,
        retest_notes: str = None,
        photos: List[str] = None,
        extra_info: Dict[str, Any] = None,
        auto_repredict: bool = True,
    ) -> Optional[WorkOrderRetestRecord]:
        """
        创建复测记录

        Args:
            work_order_id: 关联工单ID
            retest_time: 复测时间
            retester_id: 复测人ID
            retester_name: 复测人姓名
            retest_result: 复测结果
            measured_value: 复测测量值
            data_points: 复测数据点
            before_risk_score: 复测前风险评分
            after_risk_score: 复测后风险评分
            status_after_retest: 复测后状态
            confidence: 复测置信度
            retest_notes: 复测备注
            photos: 复测照片URL列表
            extra_info: 扩展信息
            auto_repredict: 是否自动再预测

        Returns:
            创建的复测记录
        """
        with get_db() as db:
            if db is None:
                return None

            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
            if not wo:
                logger.warning(f"工单不存在，无法创建复测记录: work_order_id={work_order_id}")
                return None

            if before_risk_score is None:
                before_risk_score = wo.risk_score

            record = WorkOrderRetestRecord(
                work_order_id=work_order_id,
                retest_time=retest_time or datetime.now(),
                retester_id=retester_id,
                retester_name=retester_name,
                retest_result=retest_result,
                measured_value=measured_value,
                data_points=json.dumps(data_points or [], ensure_ascii=False) if data_points else None,
                before_risk_score=before_risk_score,
                after_risk_score=after_risk_score,
                status_after_retest=status_after_retest,
                confidence=confidence,
                retest_notes=retest_notes,
                photos=json.dumps(photos or [], ensure_ascii=False) if photos else None,
                extra_info=json.dumps(extra_info or {}, ensure_ascii=False) if extra_info else None,
            )

            db.add(record)
            db.flush()
            record_id = record.id

            if wo.status not in ('closed',):
                wo.status = 'retested'

            db.commit()
            logger.info(
                f"复测记录已创建: id={record_id}, 工单={work_order_id}, "
                f"结果={retest_result}"
            )

        if auto_repredict and retest_result in ('pass', 'fail'):
            try:
                self.repredict_and_compare(record_id)
            except Exception as e:
                logger.error(f"复测后自动再预测失败: {e}")

        with get_db() as db:
            if db is None:
                return None
            return db.query(WorkOrderRetestRecord).filter(
                WorkOrderRetestRecord.id == record_id
            ).first()

    def get_retest_record(
        self, record_id: int
    ) -> Optional[WorkOrderRetestRecord]:
        """
        获取复测记录详情
        """
        with get_db() as db:
            if db is None:
                return None
            return db.query(WorkOrderRetestRecord).filter(
                WorkOrderRetestRecord.id == record_id
            ).first()

    def list_retest_records(
        self,
        work_order_id: int = None,
        retest_result: str = None,
        retester_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[WorkOrderRetestRecord], int]:
        """
        查询复测记录列表
        """
        with get_db() as db:
            if db is None:
                return [], 0

            query = db.query(WorkOrderRetestRecord)

            if work_order_id:
                query = query.filter(
                    WorkOrderRetestRecord.work_order_id == work_order_id
                )
            if retest_result:
                query = query.filter(
                    WorkOrderRetestRecord.retest_result == retest_result
                )
            if retester_id:
                query = query.filter(
                    WorkOrderRetestRecord.retester_id == retester_id
                )
            if start_time:
                query = query.filter(
                    WorkOrderRetestRecord.retest_time >= start_time
                )
            if end_time:
                query = query.filter(
                    WorkOrderRetestRecord.retest_time <= end_time
                )

            total = query.count()
            records = query.order_by(
                WorkOrderRetestRecord.retest_time.desc()
            ).offset(offset).limit(limit).all()

            return records, total

    def update_retest_record(
        self,
        record_id: int,
        **kwargs,
    ) -> Optional[WorkOrderRetestRecord]:
        """
        更新复测记录
        """
        with get_db() as db:
            if db is None:
                return None

            record = db.query(WorkOrderRetestRecord).filter(
                WorkOrderRetestRecord.id == record_id
            ).first()
            if not record:
                return None

            list_fields = {'data_points', 'photos'}
            json_fields = {'extra_info'}

            for key, value in kwargs.items():
                if value is None:
                    continue
                if hasattr(record, key):
                    if key in list_fields and value is not None:
                        setattr(record, key, json.dumps(value, ensure_ascii=False))
                    elif key in json_fields and value is not None:
                        setattr(record, key, json.dumps(value, ensure_ascii=False))
                    else:
                        setattr(record, key, value)

            db.commit()
            logger.info(f"复测记录已更新: id={record_id}")

            return db.query(WorkOrderRetestRecord).filter(
                WorkOrderRetestRecord.id == record_id
            ).first()

    def repredict_and_compare(
        self, retest_record_id: int
    ) -> Optional[WorkOrderPredictionCompare]:
        """
        复测后再预测并与原预测对比

        Args:
            retest_record_id: 复测记录ID

        Returns:
            预测对比记录
        """
        with get_db() as db:
            if db is None:
                return None

            retest = db.query(WorkOrderRetestRecord).filter(
                WorkOrderRetestRecord.id == retest_record_id
            ).first()
            if not retest:
                logger.warning(f"复测记录不存在: {retest_record_id}")
                return None

            wo = db.query(WorkOrder).filter(
                WorkOrder.id == retest.work_order_id
            ).first()
            if not wo:
                return None

            original_risk_score = retest.before_risk_score or wo.risk_score or 0.0
            retest_risk_score = retest.after_risk_score or 0.0

            if retest_risk_score > 0:
                risk_delta = retest_risk_score - original_risk_score
            else:
                risk_delta = 0.0

            if risk_delta < -10:
                risk_change = 'improved'
            elif risk_delta > 10:
                risk_change = 'worsened'
            else:
                risk_change = 'stable'

            original_status = self._risk_to_status(original_risk_score)
            retest_status = self._risk_to_status(retest_risk_score) if retest_risk_score > 0 else (
                retest.status_after_retest or 'normal'
            )

            status_match = original_status == retest_status

            is_false_positive = (
                original_status in ('warning', 'critical')
                and retest_status == 'normal'
                and retest.retest_result == 'pass'
            )

            is_recurring = self._check_recurring(
                db, wo.node_type, wo.node_id, retest.work_order_id
            )

            comparison_detail = {
                'original_risk_score': original_risk_score,
                'retest_risk_score': retest_risk_score,
                'risk_delta': risk_delta,
                'risk_change': risk_change,
                'original_status': original_status,
                'retest_status': retest_status,
                'status_match': status_match,
                'is_false_positive': is_false_positive,
                'is_recurring': is_recurring,
                'measured_value': retest.measured_value,
                'retest_result': retest.retest_result,
            }

            compare_record = WorkOrderPredictionCompare(
                work_order_id=retest.work_order_id,
                retest_id=retest.id,
                original_status=original_status,
                retest_status=retest_status,
                original_risk_score=original_risk_score,
                retest_risk_score=retest_risk_score,
                original_confidence=wo.risk_score,
                retest_confidence=retest.confidence,
                risk_change=risk_change,
                risk_delta=risk_delta,
                status_match=status_match,
                is_false_positive=is_false_positive,
                is_recurring=is_recurring,
                comparison_detail=json.dumps(comparison_detail, ensure_ascii=False),
            )

            db.add(compare_record)
            db.flush()
            compare_id = compare_record.id

            if is_recurring and hasattr(wo, 'extra_info'):
                extra = {}
                if wo.extra_info:
                    try:
                        extra = json.loads(wo.extra_info)
                    except (json.JSONDecodeError, TypeError):
                        pass
                extra['is_recurring_fault'] = True
                extra['recurrence_count'] = extra.get('recurrence_count', 0) + 1
                wo.extra_info = json.dumps(extra, ensure_ascii=False)

            db.commit()
            logger.info(
                f"预测对比已完成: id={compare_id}, 工单={retest.work_order_id}, "
                f"风险变化={risk_change}, 误报={is_false_positive}, 重复故障={is_recurring}"
            )

            return db.query(WorkOrderPredictionCompare).filter(
                WorkOrderPredictionCompare.id == compare_id
            ).first()

    def _risk_to_status(self, risk_score: float) -> str:
        """
        根据风险评分转换为状态

        Args:
            risk_score: 风险评分 0-100

        Returns:
            状态 normal/warning/critical
        """
        if risk_score >= 70:
            return 'critical'
        elif risk_score >= 40:
            return 'warning'
        else:
            return 'normal'

    def _check_recurring(
        self, db, node_type: str, node_id: str, current_wo_id: int
    ) -> bool:
        """
        检查是否为重复故障

        Args:
            db: 数据库会话
            node_type: 节点类型
            node_id: 节点ID
            current_wo_id: 当前工单ID

        Returns:
            是否为重复故障
        """
        try:
            thirty_days_ago = datetime.now() - timedelta(days=30)

            prev_wo_count = db.query(WorkOrder).filter(
                WorkOrder.node_type == node_type,
                WorkOrder.node_id == node_id,
                WorkOrder.id != current_wo_id,
                WorkOrder.create_time >= thirty_days_ago,
                WorkOrder.status.in_(['resolved', 'closed', 'retested']),
            ).count()

            return prev_wo_count >= 1
        except Exception as e:
            logger.error(f"检查重复故障失败: {e}")
            return False

    def get_prediction_compare(
        self, compare_id: int
    ) -> Optional[WorkOrderPredictionCompare]:
        """
        获取预测对比详情
        """
        with get_db() as db:
            if db is None:
                return None
            return db.query(WorkOrderPredictionCompare).filter(
                WorkOrderPredictionCompare.id == compare_id
            ).first()

    def list_prediction_compares(
        self,
        work_order_id: int = None,
        retest_id: int = None,
        is_false_positive: bool = None,
        is_recurring: bool = None,
        risk_change: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[WorkOrderPredictionCompare], int]:
        """
        查询预测对比列表
        """
        with get_db() as db:
            if db is None:
                return [], 0

            query = db.query(WorkOrderPredictionCompare)

            if work_order_id:
                query = query.filter(
                    WorkOrderPredictionCompare.work_order_id == work_order_id
                )
            if retest_id:
                query = query.filter(
                    WorkOrderPredictionCompare.retest_id == retest_id
                )
            if is_false_positive is not None:
                query = query.filter(
                    WorkOrderPredictionCompare.is_false_positive == is_false_positive
                )
            if is_recurring is not None:
                query = query.filter(
                    WorkOrderPredictionCompare.is_recurring == is_recurring
                )
            if risk_change:
                query = query.filter(
                    WorkOrderPredictionCompare.risk_change == risk_change
                )
            if start_time:
                query = query.filter(
                    WorkOrderPredictionCompare.create_time >= start_time
                )
            if end_time:
                query = query.filter(
                    WorkOrderPredictionCompare.create_time <= end_time
                )

            total = query.count()
            records = query.order_by(
                WorkOrderPredictionCompare.create_time.desc()
            ).offset(offset).limit(limit).all()

            return records, total

    def delete_retest_record(self, record_id: int) -> bool:
        """
        删除复测记录
        """
        with get_db() as db:
            if db is None:
                return False

            record = db.query(WorkOrderRetestRecord).filter(
                WorkOrderRetestRecord.id == record_id
            ).first()
            if not record:
                return False

            db.query(WorkOrderPredictionCompare).filter(
                WorkOrderPredictionCompare.retest_id == record_id
            ).delete(synchronize_session=False)

            db.delete(record)
            db.commit()
            logger.info(f"复测记录已删除: id={record_id}")
            return True
