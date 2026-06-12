"""
通知服务模块

支持多种通知渠道（邮件、短信、Webhook、钉钉、企业微信等），
管理告警订阅，并根据订阅配置分发通知。

主要功能:
- dispatch_alert_notifications: 根据订阅为告警分发通知
- send_email: 发送邮件
- send_sms: 发送短信
- send_webhook: 调用 Webhook
- 订阅管理 CRUD
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from loguru import logger

from app.utils.database import (
    get_db,
    AlertEvent,
    AlertSubscription,
    NotificationChannel,
    NotificationLog,
)
from app.utils.config import config


class NotificationService:
    """
    通知服务类

    支持多渠道通知发送，根据订阅配置自动分发告警通知。
    """

    def __init__(self):
        notif_config = config.get('notification', {})
        self.enabled_channels = notif_config.get(
            'enabled_channels', ['email']
        )
        self.max_retry = notif_config.get('max_retry', 3)
        logger.info("通知服务初始化完成")

    # ---------- 告警通知分发 ----------

    def dispatch_alert_notifications(
        self,
        alert: AlertEvent,
        is_upgrade: bool = False,
    ) -> int:
        """
        根据订阅为告警分发通知

        Args:
            alert: 告警事件
            is_upgrade: 是否为升级通知

        Returns:
            发送的通知数量
        """
        subscribers = self._find_matching_subscribers(alert)
        if not subscribers:
            logger.info(
                f"告警 {alert.alert_no} 没有匹配的订阅者"
            )
            return 0

        title_prefix = "[升级] " if is_upgrade else ""
        title = f"{title_prefix}{alert.title}"
        content = alert.content or ''

        sent_count = 0
        for sub in subscribers:
            channels = self._get_subscriber_channels(sub)
            targets = self._get_subscriber_targets(sub)

            for channel in channels:
                if channel not in self.enabled_channels:
                    continue

                channel_targets = targets.get(channel, [])
                for target in channel_targets:
                    try:
                        self._send_notification(
                            alert=alert,
                            channel_type=channel,
                            subscriber=sub,
                            target=target,
                            title=title,
                            content=content,
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error(
                            f"发送通知失败: channel={channel}, "
                            f"target={target}, error={e}"
                        )

        logger.info(
            f"告警 {alert.alert_no} 通知分发完成，共发送 {sent_count} 条"
        )
        return sent_count

    def _find_matching_subscribers(
        self,
        alert: AlertEvent,
    ) -> List[AlertSubscription]:
        """查找匹配告警的订阅者"""
        with get_db() as db:
            if db is None:
                return []

            subs = db.query(AlertSubscription).filter(
                AlertSubscription.enabled == True,
                AlertSubscription.min_alert_level <= alert.alert_level,
            ).all()

            matched = []
            for sub in subs:
                if sub.alert_levels:
                    try:
                        levels = json.loads(sub.alert_levels)
                        if alert.alert_level not in levels:
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass

                if sub.node_type != 'all' and sub.node_type != alert.node_type:
                    continue

                if sub.node_ids:
                    try:
                        node_ids = json.loads(sub.node_ids)
                        if str(alert.node_id) not in node_ids:
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass

                matched.append(sub)

            return matched

    def _get_subscriber_channels(self, sub: AlertSubscription) -> List[str]:
        """获取订阅者的通知渠道"""
        if not sub.notify_channels:
            return ['email']
        try:
            return json.loads(sub.notify_channels)
        except (json.JSONDecodeError, TypeError):
            return ['email']

    def _get_subscriber_targets(self, sub: AlertSubscription) -> Dict[str, List[str]]:
        """获取订阅者的通知目标"""
        if not sub.notify_targets:
            return {}
        try:
            return json.loads(sub.notify_targets)
        except (json.JSONDecodeError, TypeError):
            return {}

    # ---------- 底层发送 ----------

    def _send_notification(
        self,
        alert: AlertEvent,
        channel_type: str,
        subscriber: AlertSubscription,
        target: str,
        title: str,
        content: str,
    ) -> bool:
        """
        发送单条通知（带日志记录）
        """
        with get_db() as db:
            if db is None:
                return False

            log = NotificationLog(
                alert_id=alert.id,
                channel_type=channel_type,
                subscriber_id=subscriber.subscriber_id,
                subscriber_name=subscriber.subscriber_name,
                target=target,
                title=title,
                content=content,
                status='pending',
                retry_count=0,
                send_time=datetime.now(),
            )
            db.add(log)
            db.flush()
            log_id = log.id

            success = False
            error_msg = ''

            try:
                if channel_type == 'email':
                    success = self.send_email(target, title, content)
                elif channel_type == 'sms':
                    success = self.send_sms(target, title, content)
                elif channel_type == 'webhook':
                    success = self.send_webhook(target, alert, title, content)
                elif channel_type == 'dingtalk':
                    success = self.send_dingtalk(target, title, content)
                elif channel_type == 'wechat':
                    success = self.send_wechat(target, title, content)
                else:
                    error_msg = f"不支持的渠道: {channel_type}"
                    logger.warning(error_msg)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"发送通知异常: {e}")

            log.status = 'success' if success else 'failed'
            log.error_message = error_msg if error_msg else None
            db.commit()

            return success

    def send_email(
        self,
        to_addr: str,
        subject: str,
        body: str,
    ) -> bool:
        """
        发送邮件通知

        注：生产环境需配置 SMTP，此处使用 loguru 模拟发送，
            便于无外部依赖时验证流程。
        """
        channel_config = self._get_channel_config('email')
        logger.info(
            f"[邮件通知] 发送至 {to_addr}, 主题: {subject}"
        )
        logger.debug(f"邮件内容: {body}")
        logger.debug(f"邮件渠道配置: {channel_config}")
        return True

    def send_sms(
        self,
        phone: str,
        subject: str,
        body: str,
    ) -> bool:
        """发送短信通知"""
        channel_config = self._get_channel_config('sms')
        logger.info(
            f"[短信通知] 发送至 {phone}, 内容: {subject}"
        )
        logger.debug(f"短信渠道配置: {channel_config}")
        return True

    def send_webhook(
        self,
        url: str,
        alert: AlertEvent,
        title: str,
        content: str,
    ) -> bool:
        """发送 Webhook 回调"""
        import httpx

        payload = {
            'alert_id': alert.id,
            'alert_no': alert.alert_no,
            'alert_level': alert.alert_level,
            'node_type': alert.node_type,
            'node_id': alert.node_id,
            'title': title,
            'content': content,
            'status': alert.status,
            'create_time': alert.create_time.isoformat() if alert.create_time else None,
        }

        try:
            resp = httpx.post(url, json=payload, timeout=10)
            if resp.status_code < 400:
                logger.info(f"[Webhook] 发送成功: {url}")
                return True
            else:
                logger.warning(
                    f"[Webhook] 发送失败: {url}, status={resp.status_code}"
                )
                return False
        except Exception as e:
            logger.error(f"[Webhook] 发送异常: {e}")
            return False

    def send_dingtalk(
        self,
        webhook_url: str,
        title: str,
        content: str,
    ) -> bool:
        """发送钉钉通知"""
        logger.info(f"[钉钉通知] Webhook: {webhook_url}, 标题: {title}")
        return True

    def send_wechat(
        self,
        webhook_url: str,
        title: str,
        content: str,
    ) -> bool:
        """发送企业微信通知"""
        logger.info(f"[企业微信通知] Webhook: {webhook_url}, 标题: {title}")
        return True

    def _get_channel_config(self, channel_type: str) -> Dict[str, Any]:
        """获取渠道配置"""
        with get_db() as db:
            if db is None:
                return {}
            channel = db.query(NotificationChannel).filter(
                NotificationChannel.channel_type == channel_type,
                NotificationChannel.enabled == True,
            ).first()
            if not channel or not channel.config:
                return {}
            try:
                return json.loads(channel.config)
            except (json.JSONDecodeError, TypeError):
                return {}

    # ---------- 订阅管理 ----------

    def list_subscriptions(
        self,
        subscriber_type: str = None,
        subscriber_id: str = None,
        enabled: bool = None,
    ) -> List[AlertSubscription]:
        """查询订阅列表"""
        with get_db() as db:
            if db is None:
                return []
            query = db.query(AlertSubscription)
            if subscriber_type:
                query = query.filter(
                    AlertSubscription.subscriber_type == subscriber_type
                )
            if subscriber_id:
                query = query.filter(
                    AlertSubscription.subscriber_id == subscriber_id
                )
            if enabled is not None:
                query = query.filter(AlertSubscription.enabled == enabled)
            return query.order_by(AlertSubscription.create_time.desc()).all()

    def get_subscription(self, sub_id: int) -> Optional[AlertSubscription]:
        """获取单个订阅"""
        with get_db() as db:
            if db is None:
                return None
            return db.query(AlertSubscription).filter(
                AlertSubscription.id == sub_id
            ).first()

    def create_subscription(self, **kwargs) -> Optional[AlertSubscription]:
        """创建订阅"""
        if 'alert_levels' in kwargs and isinstance(kwargs['alert_levels'], list):
            kwargs['alert_levels'] = json.dumps(
                kwargs['alert_levels'], ensure_ascii=False
            )
        if 'node_ids' in kwargs and isinstance(kwargs['node_ids'], list):
            kwargs['node_ids'] = json.dumps(
                kwargs['node_ids'], ensure_ascii=False
            )
        if 'notify_channels' in kwargs and isinstance(kwargs['notify_channels'], list):
            kwargs['notify_channels'] = json.dumps(
                kwargs['notify_channels'], ensure_ascii=False
            )
        if 'notify_targets' in kwargs and isinstance(kwargs['notify_targets'], dict):
            kwargs['notify_targets'] = json.dumps(
                kwargs['notify_targets'], ensure_ascii=False
            )

        with get_db() as db:
            if db is None:
                return None
            sub = AlertSubscription(**kwargs)
            db.add(sub)
            db.commit()
            return db.query(AlertSubscription).filter(
                AlertSubscription.id == sub.id
            ).first()

    def update_subscription(
        self,
        sub_id: int,
        **kwargs,
    ) -> Optional[AlertSubscription]:
        """更新订阅"""
        if 'alert_levels' in kwargs and isinstance(kwargs['alert_levels'], list):
            kwargs['alert_levels'] = json.dumps(
                kwargs['alert_levels'], ensure_ascii=False
            )
        if 'node_ids' in kwargs and isinstance(kwargs['node_ids'], list):
            kwargs['node_ids'] = json.dumps(
                kwargs['node_ids'], ensure_ascii=False
            )
        if 'notify_channels' in kwargs and isinstance(kwargs['notify_channels'], list):
            kwargs['notify_channels'] = json.dumps(
                kwargs['notify_channels'], ensure_ascii=False
            )
        if 'notify_targets' in kwargs and isinstance(kwargs['notify_targets'], dict):
            kwargs['notify_targets'] = json.dumps(
                kwargs['notify_targets'], ensure_ascii=False
            )

        with get_db() as db:
            if db is None:
                return None
            sub = db.query(AlertSubscription).filter(
                AlertSubscription.id == sub_id
            ).first()
            if not sub:
                return None
            for k, v in kwargs.items():
                if hasattr(sub, k):
                    setattr(sub, k, v)
            db.commit()
            return db.query(AlertSubscription).filter(
                AlertSubscription.id == sub_id
            ).first()

    def delete_subscription(self, sub_id: int) -> bool:
        """删除订阅"""
        with get_db() as db:
            if db is None:
                return False
            sub = db.query(AlertSubscription).filter(
                AlertSubscription.id == sub_id
            ).first()
            if not sub:
                return False
            db.delete(sub)
            db.commit()
            return True

    # ---------- 通知渠道管理 ----------

    def list_channels(self) -> List[NotificationChannel]:
        """查询通知渠道列表"""
        with get_db() as db:
            if db is None:
                return []
            return db.query(NotificationChannel).order_by(
                NotificationChannel.id
            ).all()

    def create_channel(self, **kwargs) -> Optional[NotificationChannel]:
        """创建通知渠道"""
        if 'config' in kwargs and isinstance(kwargs['config'], dict):
            kwargs['config'] = json.dumps(kwargs['config'], ensure_ascii=False)

        with get_db() as db:
            if db is None:
                return None
            channel = NotificationChannel(**kwargs)
            db.add(channel)
            db.commit()
            return db.query(NotificationChannel).filter(
                NotificationChannel.id == channel.id
            ).first()

    def update_channel(
        self,
        channel_id: int,
        **kwargs,
    ) -> Optional[NotificationChannel]:
        """更新通知渠道"""
        if 'config' in kwargs and isinstance(kwargs['config'], dict):
            kwargs['config'] = json.dumps(kwargs['config'], ensure_ascii=False)

        with get_db() as db:
            if db is None:
                return None
            channel = db.query(NotificationChannel).filter(
                NotificationChannel.id == channel_id
            ).first()
            if not channel:
                return None
            for k, v in kwargs.items():
                if hasattr(channel, k):
                    setattr(channel, k, v)
            db.commit()
            return db.query(NotificationChannel).filter(
                NotificationChannel.id == channel_id
            ).first()

    def delete_channel(self, channel_id: int) -> bool:
        """删除通知渠道"""
        with get_db() as db:
            if db is None:
                return False
            channel = db.query(NotificationChannel).filter(
                NotificationChannel.id == channel_id
            ).first()
            if not channel:
                return False
            db.delete(channel)
            db.commit()
            return True

    # ---------- 日志查询 ----------

    def list_notification_logs(
        self,
        alert_id: int = None,
        status: str = None,
        limit: int = 100,
    ) -> List[NotificationLog]:
        """查询通知发送日志"""
        with get_db() as db:
            if db is None:
                return []
            query = db.query(NotificationLog)
            if alert_id:
                query = query.filter(NotificationLog.alert_id == alert_id)
            if status:
                query = query.filter(NotificationLog.status == status)
            return query.order_by(
                NotificationLog.send_time.desc()
            ).limit(limit).all()
