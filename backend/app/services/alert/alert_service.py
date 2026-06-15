"""
告警核心服务模块

负责告警规则匹配、静默期检查、告警事件创建和告警升级处理。

主要功能:
- evaluate_prediction: 根据预测结果评估是否触发告警
- check_silence: 检查同节点同级别是否在静默期内
- create_alert: 创建告警事件
- upgrade_alert: 告警升级（30分钟未处理自动升级）
- handle_alert: 处理告警（确认、解决、忽略）
- list_alerts: 查询告警列表
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger
from sqlalchemy import and_, or_

from app.utils.database import (
    get_db,
    AlertRule,
    AlertEvent,
)
from app.utils.config import config


ALERT_LEVEL_LABELS = {
    1: '关注级预警',
    2: '检查级预警',
    3: '紧急级预警',
    4: '故障',
}


class AlertService:
    """
    告警核心服务类

    Attributes:
        auto_create_work_order_level: 自动创建工单的最低告警级别（默认3，紧急级以上）
    """

    def __init__(self):
        alert_config = config.get('alert', {})
        self.auto_create_work_order_level = alert_config.get(
            'auto_create_work_order_level', 3
        )
        self.default_upgrade_minutes = alert_config.get(
            'default_upgrade_minutes', 30
        )
        logger.info("告警核心服务初始化完成")

    # ---------- 规则匹配与告警评估 ----------

    def evaluate_prediction(
        self,
        node_type: str,
        node_id: str,
        status_code: int,
        confidence: float,
        risk_score: float = 0.0,
        diagnosis: str = '',
        recommendations: List[str] = None,
        source_prediction_id: int = None,
    ) -> Optional[AlertEvent]:
        """
        根据预测结果评估是否触发告警

        Args:
            node_type: 节点类型 bolt/flange
            node_id: 节点ID
            status_code: 状态码 (0-4)
            confidence: 置信度
            risk_score: 风险评分
            diagnosis: 诊断信息
            recommendations: 推荐措施
            source_prediction_id: 来源预测记录ID

        Returns:
            AlertEvent 或 None（未触发告警）
        """
        if status_code <= 0:
            return None

        alert_level = status_code

        # 异常与预测关联：同一时段异常数超阈值时自动提升预警等级
        try:
            from app.services.anomaly_service import get_anomaly_service
            anomaly_service = get_anomaly_service()
            upgrade_result = anomaly_service.upgrade_warning_by_anomalies(
                sensor_id=str(node_id),
                current_warning_level=alert_level,
            )
            if upgrade_result.get('should_upgrade', False):
                new_level = upgrade_result.get('new_level', alert_level)
                if new_level > alert_level:
                    logger.info(
                        f"预警等级因异常数量自动提升: node={node_type}/{node_id}, "
                        f"原等级={alert_level}, 新等级={new_level}, "
                        f"异常数={upgrade_result.get('anomaly_count', 0)}"
                    )
                    alert_level = new_level
        except Exception as e:
            logger.warning(f"异常预警等级提升检查失败，跳过: {e}")

        matched_rule = self._match_rule(
            node_type=node_type,
            node_id=node_id,
            alert_level=alert_level,
            confidence=confidence,
        )
        if matched_rule is None:
            logger.debug(
                f"未匹配到告警规则: node={node_type}/{node_id}, "
                f"level={alert_level}, confidence={confidence}"
            )
            return None

        effective_level = matched_rule.alert_level
        silence_period = matched_rule.silence_period or 0
        if self.check_silence(node_type, node_id, effective_level, silence_period):
            logger.info(
                f"告警被静默期抑制: node={node_type}/{node_id}, "
                f"level={effective_level}"
            )
            return None

        alert = self.create_alert(
            rule=matched_rule,
            node_type=node_type,
            node_id=node_id,
            alert_level=effective_level,
            confidence=confidence,
            risk_score=risk_score,
            diagnosis=diagnosis,
            recommendations=recommendations or [],
            source_prediction_id=source_prediction_id,
        )

        return alert

    def _match_rule(
        self,
        node_type: str,
        node_id: str,
        alert_level: int,
        confidence: float,
    ) -> Optional[AlertRule]:
        """
        匹配合适的告警规则
        """
        with get_db() as db:
            if db is None:
                return None

            rules = db.query(AlertRule).filter(
                AlertRule.enabled == True,
                AlertRule.alert_level <= alert_level,
            ).order_by(AlertRule.alert_level.desc()).all()

            for rule in rules:
                if rule.node_type != 'all' and rule.node_type != node_type:
                    continue
                if rule.min_confidence and confidence < rule.min_confidence:
                    continue
                if rule.node_ids:
                    try:
                        ids = json.loads(rule.node_ids)
                        if str(node_id) not in ids:
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass

                return rule

            return None

    # ---------- 静默期 ----------

    def check_silence(
        self,
        node_type: str,
        node_id: str,
        alert_level: int,
        silence_minutes: int,
    ) -> bool:
        """
        检查是否在静默期内

        Returns:
            True 表示仍在静默期，不应重复告警
        """
        if silence_minutes <= 0:
            return False

        cutoff = datetime.now() - timedelta(minutes=silence_minutes)

        with get_db() as db:
            if db is None:
                return False

            existing = db.query(AlertEvent).filter(
                AlertEvent.node_type == node_type,
                AlertEvent.node_id == str(node_id),
                AlertEvent.alert_level == alert_level,
                AlertEvent.create_time >= cutoff,
                AlertEvent.status.in_(['pending', 'processing']),
            ).first()

            if existing:
                return True

            silenced = db.query(AlertEvent).filter(
                AlertEvent.node_type == node_type,
                AlertEvent.node_id == str(node_id),
                AlertEvent.alert_level == alert_level,
                AlertEvent.silence_until >= datetime.now(),
            ).first()

            return silenced is not None

    # ---------- 创建告警 ----------

    def create_alert(
        self,
        rule: AlertRule,
        node_type: str,
        node_id: str,
        alert_level: int,
        confidence: float,
        risk_score: float = 0.0,
        diagnosis: str = '',
        recommendations: List[str] = None,
        source_prediction_id: int = None,
    ) -> AlertEvent:
        """
        创建告警事件

        Args:
            rule: 匹配的告警规则
            node_type: 节点类型
            node_id: 节点ID
            alert_level: 告警级别
            confidence: 置信度
            risk_score: 风险评分
            diagnosis: 诊断信息
            recommendations: 推荐措施
            source_prediction_id: 来源预测ID

        Returns:
            新创建的 AlertEvent
        """
        with get_db() as db:
            if db is None:
                raise RuntimeError("数据库不可用")

            alert_no = self._generate_alert_no(db)
            level_label = ALERT_LEVEL_LABELS.get(alert_level, f'级别{alert_level}')
            node_label = '螺栓' if node_type == 'bolt' else (
                '法兰面' if node_type == 'flange' else '节点'
            )

            title = f"[{level_label}] {node_label}{node_id} 告警"
            content_parts = [f"{node_label}{node_id} 触发 {level_label}"]
            if diagnosis:
                content_parts.append(f"诊断: {diagnosis}")
            if confidence:
                content_parts.append(f"置信度: {confidence:.2%}")
            if risk_score:
                content_parts.append(f"风险评分: {risk_score:.2f}")
            content = '\n'.join(content_parts)

            silence_until = None
            if rule.silence_period:
                silence_until = datetime.now() + timedelta(
                    minutes=rule.silence_period
                )

            alert = AlertEvent(
                alert_no=alert_no,
                rule_id=rule.id,
                alert_level=alert_level,
                original_level=alert_level,
                node_type=node_type,
                node_id=str(node_id),
                title=title,
                content=content,
                confidence=confidence,
                risk_score=risk_score,
                recommendations=json.dumps(recommendations or [], ensure_ascii=False),
                status='pending',
                is_upgraded=False,
                upgrade_count=0,
                source_prediction_id=source_prediction_id,
                silence_until=silence_until,
            )

            db.add(alert)
            db.flush()
            alert_id = alert.id
            db.commit()

            logger.info(
                f"告警已创建: {alert_no}, level={alert_level}, "
                f"node={node_type}/{node_id}"
            )

            created = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()

            if created and created.alert_level >= self.auto_create_work_order_level:
                try:
                    from app.services.alert import WorkOrderService
                    wo_service = WorkOrderService()
                    wo = wo_service.create_from_alert(created)
                    if wo:
                        created.work_order_id = wo.id
                        db.commit()
                        logger.info(
                            f"已为告警 {created.alert_no} 自动创建工单: {wo.order_no}"
                        )
                except Exception as e:
                    logger.error(f"自动创建工单失败: {e}")

            try:
                from app.services.alert import NotificationService
                notif_service = NotificationService()
                notif_service.dispatch_alert_notifications(created)
            except Exception as e:
                logger.error(f"发送告警通知失败: {e}")

            return created

    def _generate_alert_no(self, db) -> str:
        """生成唯一告警编号"""
        now = datetime.now()
        prefix = now.strftime('ALT%Y%m%d%H%M%S')
        for i in range(100):
            candidate = f"{prefix}{i:02d}"
            exists = db.query(AlertEvent).filter(
                AlertEvent.alert_no == candidate
            ).first()
            if not exists:
                return candidate
        raise RuntimeError("生成告警编号失败")

    # ---------- 告警升级 ----------

    def process_pending_upgrades(self) -> int:
        """
        处理所有待升级的告警（超时未处理自动升级）

        扫描所有 pending/processing 且启用了升级的告警，
        如果超过规则设定的升级时间仍未处理，则自动升级。

        Returns:
            成功升级的告警数量
        """
        upgraded_count = 0

        with get_db() as db:
            if db is None:
                return 0

            pending_alerts = db.query(AlertEvent).filter(
                AlertEvent.status.in_(['pending', 'processing']),
                AlertEvent.alert_level < 4,
            ).all()

            for alert in pending_alerts:
                try:
                    if self._try_upgrade_alert(db, alert):
                        upgraded_count += 1
                except Exception as e:
                    logger.error(f"处理告警升级失败 alert_id={alert.id}: {e}")

        if upgraded_count > 0:
            logger.info(f"自动升级告警 {upgraded_count} 条")
        return upgraded_count

    def _try_upgrade_alert(self, db, alert: AlertEvent) -> bool:
        """
        尝试升级单个告警

        Returns:
            True 表示已升级
        """
        if alert.alert_level >= 4:
            return False

        rule = db.query(AlertRule).filter(
            AlertRule.id == alert.rule_id
        ).first() if alert.rule_id else None

        if rule is None or not rule.enable_upgrade:
            return False

        upgrade_minutes = rule.upgrade_minutes or self.default_upgrade_minutes
        if upgrade_minutes <= 0:
            return False

        ref_time = alert.last_upgrade_time or alert.create_time
        if datetime.now() - ref_time < timedelta(minutes=upgrade_minutes):
            return False

        target_level = rule.upgrade_to_level or min(alert.alert_level + 1, 4)
        if target_level <= alert.alert_level:
            target_level = min(alert.alert_level + 1, 4)

        old_level = alert.alert_level
        alert.alert_level = target_level
        alert.is_upgraded = True
        alert.upgrade_count = (alert.upgrade_count or 0) + 1
        alert.last_upgrade_time = datetime.now()

        level_label = ALERT_LEVEL_LABELS.get(target_level, f'级别{target_level}')
        alert.title = alert.title.replace(
            ALERT_LEVEL_LABELS.get(old_level, ''), level_label
        )
        alert.content = (
            f"{alert.content}\n\n[自动升级] "
            f"已从 {ALERT_LEVEL_LABELS.get(old_level, old_level)} "
            f"升级为 {level_label}（超时{upgrade_minutes}分钟未处理）"
        )

        if target_level >= self.auto_create_work_order_level and not alert.work_order_id:
            try:
                from app.services.alert import WorkOrderService
                wo_service = WorkOrderService()
                wo = wo_service.create_from_alert(alert)
                if wo:
                    alert.work_order_id = wo.id
            except Exception as e:
                logger.error(f"升级时创建工单失败: {e}")

        try:
            from app.services.alert import NotificationService
            notif_service = NotificationService()
            notif_service.dispatch_alert_notifications(alert, is_upgrade=True)
        except Exception as e:
            logger.error(f"升级通知发送失败: {e}")

        db.commit()
        logger.info(
            f"告警 {alert.alert_no} 已升级: {old_level} -> {target_level}"
        )
        return True

    # ---------- 处理告警 ----------

    def handle_alert(
        self,
        alert_id: int,
        action: str,
        handler_id: str = None,
        handler_name: str = None,
        handle_note: str = None,
        silence_minutes: int = None,
    ) -> Optional[AlertEvent]:
        """
        处理告警

        Args:
            alert_id: 告警ID
            action: 处理动作 (acknowledge/resolve/ignore)
            handler_id: 处理人ID
            handler_name: 处理人姓名
            handle_note: 处理备注
            silence_minutes: 忽略时的静默期（分钟）

        Returns:
            更新后的 AlertEvent
        """
        if action not in ('acknowledge', 'resolve', 'ignore'):
            raise ValueError(f"无效的处理动作: {action}")

        status_map = {
            'acknowledge': 'processing',
            'resolve': 'resolved',
            'ignore': 'ignored',
        }

        with get_db() as db:
            if db is None:
                return None

            alert = db.query(AlertEvent).filter(
                AlertEvent.id == alert_id
            ).first()
            if not alert:
                return None

            alert.status = status_map[action]
            alert.handler_id = handler_id
            alert.handler_name = handler_name
            alert.handle_note = handle_note

            if action == 'resolve':
                alert.handle_time = datetime.now()
            elif action == 'ignore' and silence_minutes:
                alert.silence_until = datetime.now() + timedelta(
                    minutes=silence_minutes
                )

            db.commit()

            if action == 'resolve' and alert.work_order_id:
                try:
                    from app.services.alert import WorkOrderService
                    wo_service = WorkOrderService()
                    wo_service.resolve_work_order(
                        work_order_id=alert.work_order_id,
                        resolve_note=handle_note,
                        resolver_id=handler_id,
                        resolver_name=handler_name,
                    )
                except Exception as e:
                    logger.error(f"同步关闭工单失败: {e}")

            logger.info(
                f"告警已处理: {alert.alert_no}, action={action}, "
                f"handler={handler_name}"
            )
            return db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()

    # ---------- 查询 ----------

    def list_alerts(
        self,
        status: str = None,
        alert_level: int = None,
        node_type: str = None,
        node_id: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AlertEvent]:
        """
        查询告警列表
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(AlertEvent)

            if status:
                query = query.filter(AlertEvent.status == status)
            if alert_level:
                query = query.filter(AlertEvent.alert_level == alert_level)
            if node_type:
                query = query.filter(AlertEvent.node_type == node_type)
            if node_id:
                query = query.filter(AlertEvent.node_id == node_id)

            return query.order_by(
                AlertEvent.create_time.desc()
            ).offset(offset).limit(limit).all()

    def get_alert(self, alert_id: int) -> Optional[AlertEvent]:
        """获取单条告警详情"""
        with get_db() as db:
            if db is None:
                return None
            return db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()

    # ---------- 规则管理 ----------

    def list_rules(
        self,
        enabled: bool = None,
        alert_level: int = None,
    ) -> List[AlertRule]:
        """查询告警规则列表"""
        with get_db() as db:
            if db is None:
                return []
            query = db.query(AlertRule)
            if enabled is not None:
                query = query.filter(AlertRule.enabled == enabled)
            if alert_level:
                query = query.filter(AlertRule.alert_level == alert_level)
            return query.order_by(AlertRule.alert_level).all()

    def create_rule(self, **kwargs) -> Optional[AlertRule]:
        """创建告警规则"""
        with get_db() as db:
            if db is None:
                return None
            rule = AlertRule(**kwargs)
            db.add(rule)
            db.commit()
            return db.query(AlertRule).filter(AlertRule.id == rule.id).first()

    def update_rule(self, rule_id: int, **kwargs) -> Optional[AlertRule]:
        """更新告警规则"""
        with get_db() as db:
            if db is None:
                return None
            rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
            if not rule:
                return None
            for k, v in kwargs.items():
                if hasattr(rule, k):
                    setattr(rule, k, v)
            db.commit()
            return db.query(AlertRule).filter(AlertRule.id == rule_id).first()

    def delete_rule(self, rule_id: int) -> bool:
        """删除告警规则"""
        with get_db() as db:
            if db is None:
                return False
            rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
            if not rule:
                return False
            db.delete(rule)
            db.commit()
            return True
