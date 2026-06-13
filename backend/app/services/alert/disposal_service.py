"""
工单处置记录服务模块

负责现场人员上传处置记录、查询处置历史。

主要功能:
- create_disposal_record: 创建处置记录
- get_disposal_record: 获取处置记录详情
- list_disposal_records: 查询处置记录列表
- update_disposal_record: 更新处置记录
- delete_disposal_record: 删除处置记录
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger

from app.utils.database import (
    get_db,
    WorkOrderDisposalRecord,
    WorkOrder,
)


class DisposalService:
    """
    处置记录服务类
    """

    def __init__(self):
        logger.info("处置记录服务初始化完成")

    def create_disposal_record(
        self,
        work_order_id: int,
        disposal_type: str,
        disposal_content: str,
        disposal_time: datetime = None,
        operator_id: str = None,
        operator_name: str = None,
        before_value: float = None,
        after_value: float = None,
        materials_used: List[Dict[str, Any]] = None,
        photos: List[str] = None,
        notes: str = None,
        extra_info: Dict[str, Any] = None,
    ) -> Optional[WorkOrderDisposalRecord]:
        """
        创建处置记录

        Args:
            work_order_id: 关联工单ID
            disposal_type: 处置类型
            disposal_content: 处置内容描述
            disposal_time: 处置时间
            operator_id: 操作人ID
            operator_name: 操作人姓名
            before_value: 处置前值
            after_value: 处置后值
            materials_used: 使用材料列表
            photos: 现场照片URL列表
            notes: 备注
            extra_info: 扩展信息

        Returns:
            创建的处置记录
        """
        with get_db() as db:
            if db is None:
                return None

            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
            if not wo:
                logger.warning(f"工单不存在，无法创建处置记录: work_order_id={work_order_id}")
                return None

            record = WorkOrderDisposalRecord(
                work_order_id=work_order_id,
                disposal_type=disposal_type,
                disposal_content=disposal_content,
                disposal_time=disposal_time or datetime.now(),
                operator_id=operator_id,
                operator_name=operator_name,
                before_value=before_value,
                after_value=after_value,
                materials_used=json.dumps(materials_used or [], ensure_ascii=False) if materials_used else None,
                photos=json.dumps(photos or [], ensure_ascii=False) if photos else None,
                notes=notes,
                extra_info=json.dumps(extra_info or {}, ensure_ascii=False) if extra_info else None,
            )

            db.add(record)
            db.flush()
            record_id = record.id

            if wo.status in ('open', 'assigned', 'pending_assignment'):
                wo.status = 'in_progress'

            db.commit()

            logger.info(
                f"处置记录已创建: id={record_id}, 工单={work_order_id}, "
                f"类型={disposal_type}"
            )

            return db.query(WorkOrderDisposalRecord).filter(
                WorkOrderDisposalRecord.id == record_id
            ).first()

    def get_disposal_record(
        self, record_id: int
    ) -> Optional[WorkOrderDisposalRecord]:
        """
        获取处置记录详情

        Args:
            record_id: 处置记录ID

        Returns:
            处置记录
        """
        with get_db() as db:
            if db is None:
                return None
            return db.query(WorkOrderDisposalRecord).filter(
                WorkOrderDisposalRecord.id == record_id
            ).first()

    def list_disposal_records(
        self,
        work_order_id: int = None,
        disposal_type: str = None,
        operator_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[WorkOrderDisposalRecord], int]:
        """
        查询处置记录列表

        Args:
            work_order_id: 工单ID
            disposal_type: 处置类型
            operator_id: 操作人ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 每页数量
            offset: 偏移量

        Returns:
            (记录列表, 总数)
        """
        with get_db() as db:
            if db is None:
                return [], 0

            query = db.query(WorkOrderDisposalRecord)

            if work_order_id:
                query = query.filter(
                    WorkOrderDisposalRecord.work_order_id == work_order_id
                )
            if disposal_type:
                query = query.filter(
                    WorkOrderDisposalRecord.disposal_type == disposal_type
                )
            if operator_id:
                query = query.filter(
                    WorkOrderDisposalRecord.operator_id == operator_id
                )
            if start_time:
                query = query.filter(
                    WorkOrderDisposalRecord.disposal_time >= start_time
                )
            if end_time:
                query = query.filter(
                    WorkOrderDisposalRecord.disposal_time <= end_time
                )

            total = query.count()
            records = query.order_by(
                WorkOrderDisposalRecord.disposal_time.desc()
            ).offset(offset).limit(limit).all()

            return records, total

    def update_disposal_record(
        self,
        record_id: int,
        **kwargs,
    ) -> Optional[WorkOrderDisposalRecord]:
        """
        更新处置记录

        Args:
            record_id: 处置记录ID
            **kwargs: 要更新的字段

        Returns:
            更新后的处置记录
        """
        with get_db() as db:
            if db is None:
                return None

            record = db.query(WorkOrderDisposalRecord).filter(
                WorkOrderDisposalRecord.id == record_id
            ).first()
            if not record:
                return None

            list_fields = {'materials_used', 'photos'}
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
            logger.info(f"处置记录已更新: id={record_id}")

            return db.query(WorkOrderDisposalRecord).filter(
                WorkOrderDisposalRecord.id == record_id
            ).first()

    def delete_disposal_record(self, record_id: int) -> bool:
        """
        删除处置记录

        Args:
            record_id: 处置记录ID

        Returns:
            是否删除成功
        """
        with get_db() as db:
            if db is None:
                return False

            record = db.query(WorkOrderDisposalRecord).filter(
                WorkOrderDisposalRecord.id == record_id
            ).first()
            if not record:
                return False

            db.delete(record)
            db.commit()
            logger.info(f"处置记录已删除: id={record_id}")
            return True
