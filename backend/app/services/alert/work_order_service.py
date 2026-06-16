"""
工单服务模块

负责与告警联动的工单管理，紧急预警自动建单并通知。

主要功能:
- create_from_alert: 从告警事件自动创建工单
- assign_work_order: 指派工单
- resolve_work_order: 解决工单
- list_work_orders: 查询工单列表
- update_work_order: 更新工单信息
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from app.utils.database import (
    get_db,
    WorkOrder,
    AlertEvent,
)
from app.utils.config import config


ALERT_LEVEL_PRIORITY_MAP = {
    1: 'low',
    2: 'medium',
    3: 'high',
    4: 'urgent',
}

LEVEL_DUE_HOURS = {
    1: 72,
    2: 48,
    3: 24,
    4: 4,
}


class WorkOrderService:
    """
    工单服务类

    与告警联动，紧急预警自动建单并通知相关人员。
    """

    def __init__(self):
        wo_config = config.get('work_order', {})
        self.auto_create_level = wo_config.get('auto_create_level', 3)
        self.default_assignee = wo_config.get('default_assignee_id')
        self.default_assignee_name = wo_config.get('default_assignee_name')
        logger.info("工单服务初始化完成")

    # ---------- 从告警创建工单 ----------

    def create_from_alert(
        self,
        alert: AlertEvent,
        extra_info: Dict[str, Any] = None,
    ) -> Optional[WorkOrder]:
        """
        从告警事件自动创建工单

        Args:
            alert: 告警事件
            extra_info: 扩展信息

        Returns:
            新创建的 WorkOrder
        """
        with get_db() as db:
            if db is None:
                return None

            if alert.work_order_id:
                existing = db.query(WorkOrder).filter(
                    WorkOrder.id == alert.work_order_id
                ).first()
                if existing:
                    return existing

            order_no = self._generate_order_no(db)
            priority = ALERT_LEVEL_PRIORITY_MAP.get(
                alert.alert_level, 'medium'
            )
            due_hours = LEVEL_DUE_HOURS.get(alert.alert_level, 48)
            due_time = datetime.now() + timedelta(hours=due_hours)

            node_label = '螺栓' if alert.node_type == 'bolt' else (
                '法兰面' if alert.node_type == 'flange' else '节点'
            )
            description_parts = [
                f"关联告警编号: {alert.alert_no}",
                f"节点类型: {node_label}",
                f"节点ID: {alert.node_id}",
                f"告警级别: {alert.alert_level}",
                f"置信度: {alert.confidence:.2%}" if alert.confidence else '',
                f"风险评分: {alert.risk_score:.2f}" if alert.risk_score else '',
                f"告警内容:\n{alert.content}" if alert.content else '',
            ]
            description = '\n'.join(p for p in description_parts if p)

            work_order = WorkOrder(
                order_no=order_no,
                alert_id=alert.id,
                title=alert.title,
                description=description,
                priority=priority,
                status='open',
                node_type=alert.node_type,
                node_id=str(alert.node_id),
                alert_level=alert.alert_level,
                risk_score=alert.risk_score,
                assignee_id=self.default_assignee,
                assignee_name=self.default_assignee_name,
                creator_id='system',
                creator_name='系统自动',
                due_time=due_time,
                recommendations=alert.recommendations,
                extra_info=json.dumps(extra_info or {}, ensure_ascii=False),
            )

            db.add(work_order)
            db.flush()
            wo_id = work_order.id
            db.commit()

            logger.info(
                f"工单已创建: {order_no}, 来源告警={alert.alert_no}, "
                f"优先级={priority}"
            )

            try:
                self._notify_work_order_created(work_order)
            except Exception as e:
                logger.error(f"发送工单创建通知失败: {e}")

            return db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()

    def _generate_order_no(self, db) -> str:
        """生成唯一工单编号"""
        now = datetime.now()
        prefix = now.strftime('WO%Y%m%d%H%M%S')
        for i in range(100):
            candidate = f"{prefix}{i:02d}"
            exists = db.query(WorkOrder).filter(
                WorkOrder.order_no == candidate
            ).first()
            if not exists:
                return candidate
        raise RuntimeError("生成工单编号失败")

    def _notify_work_order_created(self, work_order: WorkOrder) -> None:
        """工单创建通知（通过通知服务）"""
        try:
            from app.services.alert import NotificationService
            notif_service = NotificationService()

            title = f"[工单] {work_order.title}"
            content = (
                f"工单编号: {work_order.order_no}\n"
                f"优先级: {work_order.priority}\n"
                f"状态: {work_order.status}\n"
                f"截止时间: {work_order.due_time}\n"
                f"处理人: {work_order.assignee_name or '未指派'}\n\n"
                f"描述:\n{work_order.description}"
            )

            if work_order.assignee_id:
                with get_db() as db:
                    if db:
                        from app.utils.database import AlertSubscription
                        subs = db.query(AlertSubscription).filter(
                            AlertSubscription.subscriber_type == 'user',
                            AlertSubscription.subscriber_id == work_order.assignee_id,
                            AlertSubscription.enabled == True,
                        ).all()
                        for sub in subs:
                            channels = notif_service._get_subscriber_channels(sub)
                            targets = notif_service._get_subscriber_targets(sub)
                            for channel in channels:
                                for target in targets.get(channel, []):
                                    notif_service._send_notification(
                                        alert=type('DummyAlert', (), {
                                            'id': work_order.alert_id or 0
                                        })(),
                                        channel_type=channel,
                                        subscriber=sub,
                                        target=target,
                                        title=title,
                                        content=content,
                                    )

            logger.info(
                f"工单 {work_order.order_no} 创建通知已派发"
            )
        except Exception as e:
            logger.error(f"派发工单通知失败: {e}")

    # ---------- 工单管理 ----------

    def get_work_order(self, work_order_id: int) -> Optional[WorkOrder]:
        """获取工单详情"""
        with get_db() as db:
            if db is None:
                return None
            return db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()

    def list_work_orders(
        self,
        status: str = None,
        priority: str = None,
        assignee_id: str = None,
        alert_id: int = None,
        node_type: str = None,
        node_id: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorkOrder]:
        """查询工单列表"""
        with get_db() as db:
            if db is None:
                return []
            query = db.query(WorkOrder)
            if status:
                query = query.filter(WorkOrder.status == status)
            if priority:
                query = query.filter(WorkOrder.priority == priority)
            if assignee_id:
                query = query.filter(WorkOrder.assignee_id == assignee_id)
            if alert_id:
                query = query.filter(WorkOrder.alert_id == alert_id)
            if node_type:
                query = query.filter(WorkOrder.node_type == node_type)
            if node_id:
                query = query.filter(WorkOrder.node_id == node_id)
            return query.order_by(
                WorkOrder.create_time.desc()
            ).offset(offset).limit(limit).all()

    def assign_work_order(
        self,
        work_order_id: int,
        assignee_id: str,
        assignee_name: str,
        assigner_id: str = None,
        assigner_name: str = None,
    ) -> Optional[WorkOrder]:
        """
        指派工单处理人

        Args:
            work_order_id: 工单ID
            assignee_id: 处理人ID
            assignee_name: 处理人姓名
            assigner_id: 指派人ID
            assigner_name: 指派人姓名

        Returns:
            更新后的工单
        """
        with get_db() as db:
            if db is None:
                return None
            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
            if not wo:
                return None

            wo.assignee_id = assignee_id
            wo.assignee_name = assignee_name
            if wo.status == 'open':
                wo.status = 'assigned'

            extra = {}
            if wo.extra_info:
                try:
                    extra = json.loads(wo.extra_info)
                except (json.JSONDecodeError, TypeError):
                    pass
            extra['assign_history'] = extra.get('assign_history', [])
            extra['assign_history'].append({
                'assigner_id': assigner_id,
                'assigner_name': assigner_name,
                'assignee_id': assignee_id,
                'assignee_name': assignee_name,
                'time': datetime.now().isoformat(),
            })
            wo.extra_info = json.dumps(extra, ensure_ascii=False)

            db.commit()
            logger.info(
                f"工单 {wo.order_no} 已指派给 {assignee_name}"
            )
            return db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()

    def update_work_order_status(
        self,
        work_order_id: int,
        status: str,
        operator_id: str = None,
        operator_name: str = None,
        note: str = None,
        skip_compliance_check: bool = False,
    ) -> Optional[WorkOrder]:
        """
        更新工单状态

        Args:
            work_order_id: 工单ID
            status: 新状态 (open/assigned/in_progress/resolved/closed)
            operator_id: 操作人ID
            operator_name: 操作人姓名
            note: 备注
            skip_compliance_check: 是否跳过合规检验检查（关闭工单时）

        Returns:
            更新后的工单
        """
        valid_statuses = ('open', 'assigned', 'in_progress', 'resolved', 'closed')
        if status not in valid_statuses:
            raise ValueError(f"无效的工单状态: {status}")

        with get_db() as db:
            if db is None:
                return None
            wo = db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()
            if not wo:
                return None

            if status == 'closed' and not skip_compliance_check:
                try:
                    from app.services.compliance import ComplianceInspectionService
                    compliance_service = ComplianceInspectionService()
                    close_check = compliance_service.can_close_work_order(work_order_id)
                    if not close_check['can_close']:
                        raise ValueError(
                            f"工单无法关闭: {close_check['reason']}"
                        )
                except ValueError:
                    raise
                except Exception as e:
                    logger.warning(f"合规检验关闭检查失败，跳过: {e}")

            wo.status = status
            if note:
                existing_note = wo.resolve_note or ''
                sep = '\n---\n' if existing_note else ''
                wo.resolve_note = (
                    f"{existing_note}{sep}"
                    f"[{operator_name or '系统'}] {datetime.now().isoformat()}\n"
                    f"{note}"
                )

            if status == 'resolved':
                wo.resolve_time = datetime.now()

                if wo.alert_id:
                    try:
                        from app.services.alert import AlertService
                        alert_service = AlertService()
                        alert_service.handle_alert(
                            alert_id=wo.alert_id,
                            action='resolve',
                            handler_id=operator_id,
                            handler_name=operator_name,
                            handle_note=note,
                        )
                    except Exception as e:
                        logger.error(f"同步解决关联告警失败: {e}")

            db.commit()
            logger.info(
                f"工单 {wo.order_no} 状态更新为 {status}"
            )
            return db.query(WorkOrder).filter(
                WorkOrder.id == work_order_id
            ).first()

    def resolve_work_order(
        self,
        work_order_id: int,
        resolve_note: str,
        resolver_id: str = None,
        resolver_name: str = None,
    ) -> Optional[WorkOrder]:
        """
        解决工单（便捷方法）
        """
        return self.update_work_order_status(
            work_order_id=work_order_id,
            status='resolved',
            operator_id=resolver_id,
            operator_name=resolver_name,
            note=resolve_note,
        )

    def create_manual_work_order(
        self,
        title: str,
        description: str = '',
        priority: str = 'medium',
        node_type: str = None,
        node_id: str = None,
        alert_level: int = None,
        risk_score: float = None,
        assignee_id: str = None,
        assignee_name: str = None,
        creator_id: str = 'manual',
        creator_name: str = '人工创建',
        due_hours: int = 48,
        recommendations: List[str] = None,
        extra_info: Dict[str, Any] = None,
    ) -> Optional[WorkOrder]:
        """
        手动创建工单（非告警来源）
        """
        with get_db() as db:
            if db is None:
                return None

            order_no = self._generate_order_no(db)
            due_time = datetime.now() + timedelta(hours=due_hours)

            work_order = WorkOrder(
                order_no=order_no,
                title=title,
                description=description,
                priority=priority,
                status='open',
                node_type=node_type,
                node_id=str(node_id) if node_id else None,
                alert_level=alert_level,
                risk_score=risk_score,
                assignee_id=assignee_id,
                assignee_name=assignee_name,
                creator_id=creator_id,
                creator_name=creator_name,
                due_time=due_time,
                recommendations=json.dumps(
                    recommendations or [], ensure_ascii=False
                ) if recommendations else None,
                extra_info=json.dumps(
                    extra_info or {}, ensure_ascii=False
                ),
            )

            db.add(work_order)
            db.commit()

            logger.info(f"人工工单已创建: {order_no}")
            return db.query(WorkOrder).filter(
                WorkOrder.id == work_order.id
            ).first()
