import hashlib
import hmac
import json
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import httpx
from loguru import logger

from app.streaming.event_publisher import StreamEvent
from app.utils.database import get_db
from app.services.webhook.models import WebhookSubscription, WebhookDeliveryLog, WebhookDeadLetter


class WebhookSubscriptionService:

    def list_subscriptions(self, tenant_id: int, page: int = 1, page_size: int = 20, enabled_only: bool = True):
        with get_db() as db:
            if db is None:
                return [], 0
            query = db.query(WebhookSubscription).filter(WebhookSubscription.tenant_id == tenant_id)
            if enabled_only:
                query = query.filter(WebhookSubscription.enabled == True)
            total = query.count()
            offset = (page - 1) * page_size
            items = query.order_by(WebhookSubscription.create_time.desc()).offset(offset).limit(page_size).all()
            return items, total

    def get_subscription(self, subscription_id: int) -> Optional[WebhookSubscription]:
        with get_db() as db:
            if db is None:
                return None
            return db.query(WebhookSubscription).filter(WebhookSubscription.id == subscription_id).first()

    def create_subscription(self, data: dict, tenant_id: int = None) -> Optional[WebhookSubscription]:
        with get_db() as db:
            if db is None:
                return None
            subscription = WebhookSubscription(
                tenant_id=tenant_id or data.get('tenant_id'),
                name=data.get('name', ''),
                url=data.get('url', ''),
                secret=data.get('secret', ''),
                event_types=json.dumps(data.get('event_types', [])),
                filter_node_types=json.dumps(data.get('filter_node_types', [])),
                filter_node_ids=json.dumps(data.get('filter_node_ids', [])),
                min_level=data.get('min_level', 0),
                enabled=data.get('enabled', True),
                max_retries=data.get('max_retries', 5),
                timeout_seconds=data.get('timeout_seconds', 10),
                enable_digest=data.get('enable_digest', False),
                digest_window_seconds=data.get('digest_window_seconds', 300),
                description=data.get('description', ''),
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            return subscription

    def update_subscription(self, subscription_id: int, data: dict) -> Optional[WebhookSubscription]:
        with get_db() as db:
            if db is None:
                return None
            subscription = db.query(WebhookSubscription).filter(WebhookSubscription.id == subscription_id).first()
            if subscription is None:
                return None
            for key, value in data.items():
                if key in ('event_types', 'filter_node_types', 'filter_node_ids'):
                    value = json.dumps(value) if not isinstance(value, str) else value
                if hasattr(subscription, key):
                    setattr(subscription, key, value)
            db.commit()
            db.refresh(subscription)
            return subscription

    def delete_subscription(self, subscription_id: int) -> bool:
        with get_db() as db:
            if db is None:
                return False
            subscription = db.query(WebhookSubscription).filter(WebhookSubscription.id == subscription_id).first()
            if subscription is None:
                return False
            subscription.enabled = False
            db.commit()
            return True

    def get_matching_subscriptions(self, event_type: str, node_type: str, node_id: str, level: int = None) -> List[WebhookSubscription]:
        with get_db() as db:
            if db is None:
                return []
            subscriptions = db.query(WebhookSubscription).filter(WebhookSubscription.enabled == True).all()
            matched = []
            for sub in subscriptions:
                event_types = sub.get_event_types()
                if event_type not in event_types:
                    continue
                filter_node_types = sub.get_filter_node_types()
                if filter_node_types and node_type not in filter_node_types:
                    continue
                filter_node_ids = sub.get_filter_node_ids()
                if filter_node_ids and node_id not in filter_node_ids:
                    continue
                if sub.min_level and sub.min_level > 0 and level is not None and level < sub.min_level:
                    continue
                matched.append(sub)
            return matched


class WebhookDeliveryService:

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        self._subscription_service = None

    @property
    def subscription_service(self):
        if self._subscription_service is None:
            self._subscription_service = get_webhook_subscription_service()
        return self._subscription_service

    def on_stream_event(self, event: StreamEvent):
        webhook_event_type = self._map_event_type(event)
        if webhook_event_type is None:
            return
        level = self._extract_level(event)
        subscriptions = self.subscription_service.get_matching_subscriptions(
            event_type=webhook_event_type,
            node_type=event.node_type,
            node_id=event.node_id,
            level=level,
        )
        event_dict = {
            'event_id': event.event_id,
            'event_type': webhook_event_type,
            'node_type': event.node_type,
            'node_id': event.node_id,
            'timestamp': event.timestamp,
            'data': event.data,
            'source': event.source,
            'metadata': event.metadata,
        }
        digest_manager = get_webhook_digest_manager()
        for sub in subscriptions:
            if sub.enable_digest:
                digest_manager.add_event(sub, event_dict)
            else:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.deliver_to_subscription(sub, event_dict))
                except RuntimeError:
                    asyncio.run(self.deliver_to_subscription(sub, event_dict))

    def _map_event_type(self, event: StreamEvent) -> Optional[str]:
        if event.event_type == 'status_change':
            return 'status_changed'
        if event.event_type == 'alert':
            data = event.data or {}
            alert_data = data.get('alert', data)
            risk_level = alert_data.get('risk_level', '')
            if risk_level == 'high':
                return 'risk_high'
            fault_type = alert_data.get('fault_type', '')
            if fault_type:
                return 'fault_detected'
            if alert_data.get('fault_confidence') is not None:
                return 'fault_detected'
            return 'risk_high' if risk_level in ('high', 'critical') else None
        return None

    def _extract_level(self, event: StreamEvent) -> Optional[int]:
        data = event.data or {}
        alert_data = data.get('alert', data)
        level = alert_data.get('alert_level') or alert_data.get('level')
        if level is not None:
            return int(level)
        return None

    async def deliver_to_subscription(self, subscription: WebhookSubscription, event_dict: dict):
        payload_json = json.dumps(event_dict, ensure_ascii=False)
        hmac_signature = self._compute_hmac(payload_json, subscription.secret) if subscription.secret else ''
        delivery_log = None
        with get_db() as db:
            if db is None:
                return
            is_digest = event_dict.get('is_digest', False)
            digest_event_count = event_dict.get('digest_event_count', 0)
            delivery_log = WebhookDeliveryLog(
                tenant_id=subscription.tenant_id,
                subscription_id=subscription.id,
                event_id=event_dict.get('event_id', ''),
                event_type=event_dict.get('event_type', ''),
                node_type=event_dict.get('node_type', ''),
                node_id=event_dict.get('node_id', ''),
                payload=payload_json,
                hmac_signature=hmac_signature,
                status='pending',
                is_digest=is_digest,
                digest_event_count=digest_event_count,
            )
            db.add(delivery_log)
            db.commit()
            db.refresh(delivery_log)

        status_code, response_text, error = await self._send_webhook(
            url=subscription.url,
            payload=payload_json,
            hmac_signature=hmac_signature,
            timeout=subscription.timeout_seconds,
        )

        with get_db() as db:
            if db is None:
                return
            log = db.query(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == delivery_log.id).first()
            if log is None:
                return
            if error is None and status_code is not None and 200 <= status_code < 300:
                log.status = 'success'
                log.http_status_code = status_code
                log.response_body = (response_text or '')[:2000]
            else:
                log.status = 'failed'
                log.http_status_code = status_code
                log.response_body = (response_text or '')[:2000]
                log.error_message = str(error)[:2000] if error else f'HTTP {status_code}'
                self._schedule_retry(log.id, log.retry_count, subscription.max_retries)
            db.commit()

    @staticmethod
    def _compute_hmac(payload_json: str, secret: str) -> str:
        return hmac.new(
            secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

    async def _send_webhook(self, url: str, payload: str, hmac_signature: str, timeout: int) -> Tuple[Optional[int], Optional[str], Optional[Exception]]:
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': hmac_signature,
        }
        try:
            response = await self._client.post(
                url,
                content=payload,
                headers=headers,
                timeout=float(timeout),
            )
            return response.status_code, response.text, None
        except httpx.TimeoutException as e:
            logger.warning(f"Webhook timeout: {url}, error: {e}")
            return None, None, e
        except httpx.HTTPError as e:
            logger.warning(f"Webhook HTTP error: {url}, error: {e}")
            return None, None, e
        except Exception as e:
            logger.error(f"Webhook send error: {url}, error: {e}")
            return None, None, e

    def _schedule_retry(self, delivery_log_id: int, retry_count: int, max_retries: int):
        if retry_count >= max_retries:
            self._move_to_dead_letter(delivery_log_id, 'max_retries_exceeded')
            return
        base_delay = 1
        delay_seconds = min(base_delay * (2 ** retry_count), 300)
        next_retry_at = datetime.now() + timedelta(seconds=delay_seconds)
        with get_db() as db:
            if db is None:
                return
            log = db.query(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == delivery_log_id).first()
            if log is None:
                return
            log.next_retry_at = next_retry_at
            log.retry_count = retry_count + 1
            db.commit()
        logger.info(f"Webhook retry scheduled: log_id={delivery_log_id}, retry_count={retry_count + 1}, next_retry_at={next_retry_at}")

    def _move_to_dead_letter(self, delivery_log_id: int, reason: str):
        with get_db() as db:
            if db is None:
                return
            log = db.query(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == delivery_log_id).first()
            if log is None:
                return
            dead_letter = WebhookDeadLetter(
                tenant_id=log.tenant_id,
                subscription_id=log.subscription_id,
                event_id=log.event_id,
                event_type=log.event_type,
                node_type=log.node_type,
                node_id=log.node_id,
                original_payload=log.payload,
                last_error=log.error_message,
                total_retries=log.retry_count,
                dead_letter_reason=reason,
                original_created_at=log.create_time,
            )
            db.add(dead_letter)
            log.status = 'dead_letter'
            db.commit()
        logger.warning(f"Webhook moved to dead letter: log_id={delivery_log_id}, reason={reason}")

    async def process_pending_retries(self):
        now = datetime.now()
        with get_db() as db:
            if db is None:
                return
            pending = db.query(WebhookDeliveryLog).filter(
                WebhookDeliveryLog.status == 'failed',
                WebhookDeliveryLog.next_retry_at <= now,
            ).all()
            if not pending:
                return
            log_ids = [l.id for l in pending]

        for log_id in log_ids:
            with get_db() as db:
                if db is None:
                    continue
                log = db.query(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == log_id).first()
                if log is None or log.status != 'failed':
                    continue
                subscription = db.query(WebhookSubscription).filter(WebhookSubscription.id == log.subscription_id).first()
                if subscription is None:
                    continue
                event_dict = json.loads(log.payload) if log.payload else {}
                event_dict['is_retry'] = True

            hmac_signature = log.hmac_signature or ''
            if subscription.secret and log.payload:
                hmac_signature = self._compute_hmac(log.payload, subscription.secret)

            status_code, response_text, error = await self._send_webhook(
                url=subscription.url,
                payload=log.payload,
                hmac_signature=hmac_signature,
                timeout=subscription.timeout_seconds,
            )

            with get_db() as db:
                if db is None:
                    continue
                log = db.query(WebhookDeliveryLog).filter(WebhookDeliveryLog.id == log_id).first()
                if log is None:
                    continue
                if error is None and status_code is not None and 200 <= status_code < 300:
                    log.status = 'success'
                    log.http_status_code = status_code
                    log.response_body = (response_text or '')[:2000]
                else:
                    log.http_status_code = status_code
                    log.response_body = (response_text or '')[:2000]
                    log.error_message = str(error)[:2000] if error else f'HTTP {status_code}'
                    self._schedule_retry(log.id, log.retry_count, subscription.max_retries)
                db.commit()

    def get_delivery_logs(self, tenant_id: int = None, subscription_id: int = None, status: str = None, page: int = 1, page_size: int = 20):
        with get_db() as db:
            if db is None:
                return [], 0
            query = db.query(WebhookDeliveryLog)
            if tenant_id is not None:
                query = query.filter(WebhookDeliveryLog.tenant_id == tenant_id)
            if subscription_id is not None:
                query = query.filter(WebhookDeliveryLog.subscription_id == subscription_id)
            if status is not None:
                query = query.filter(WebhookDeliveryLog.status == status)
            total = query.count()
            offset = (page - 1) * page_size
            items = query.order_by(WebhookDeliveryLog.create_time.desc()).offset(offset).limit(page_size).all()
            return items, total

    def get_dead_letters(self, tenant_id: int = None, subscription_id: int = None, page: int = 1, page_size: int = 20):
        with get_db() as db:
            if db is None:
                return [], 0
            query = db.query(WebhookDeadLetter)
            if tenant_id is not None:
                query = query.filter(WebhookDeadLetter.tenant_id == tenant_id)
            if subscription_id is not None:
                query = query.filter(WebhookDeadLetter.subscription_id == subscription_id)
            total = query.count()
            offset = (page - 1) * page_size
            items = query.order_by(WebhookDeadLetter.create_time.desc()).offset(offset).limit(page_size).all()
            return items, total


class WebhookDigestManager:

    def __init__(self):
        self._buffer: Dict[Tuple[int, str], list] = {}
        self._timers: Dict[Tuple[int, str], threading.Timer] = {}
        self._lock = threading.Lock()
        self._delivery_service = None

    @property
    def delivery_service(self):
        if self._delivery_service is None:
            self._delivery_service = get_webhook_delivery_service()
        return self._delivery_service

    def add_event(self, subscription: WebhookSubscription, event_dict: dict):
        key = (subscription.id, event_dict.get('node_id', ''))
        with self._lock:
            if key not in self._buffer:
                self._buffer[key] = []
            self._buffer[key].append(event_dict)

            if key in self._timers:
                self._timers[key].cancel()

            window = subscription.digest_window_seconds or 300
            timer = threading.Timer(window, self._flush_digest, args=[key])
            timer.daemon = True
            self._timers[key] = timer
            timer.start()

    def _flush_digest(self, key: Tuple[int, str]):
        with self._lock:
            events = self._buffer.pop(key, [])
            self._timers.pop(key, None)

        if not events:
            return

        subscription_id = key[0]
        subscription_service = get_webhook_subscription_service()
        subscription = subscription_service.get_subscription(subscription_id)
        if subscription is None:
            return

        digest_payload = {
            'event_id': str(uuid.uuid4()),
            'event_type': events[0].get('event_type', ''),
            'node_type': events[0].get('node_type', ''),
            'node_id': key[1],
            'timestamp': datetime.now().isoformat(),
            'is_digest': True,
            'digest_event_count': len(events),
            'events': events,
            'source': 'webhook_digest',
            'metadata': {},
        }

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.delivery_service.deliver_to_subscription(subscription, digest_payload))
        except RuntimeError:
            asyncio.run(self.delivery_service.deliver_to_subscription(subscription, digest_payload))

    def stop(self):
        with self._lock:
            for key, timer in self._timers.items():
                timer.cancel()
            self._timers.clear()

            remaining_keys = list(self._buffer.keys())
            buffer_copy = dict(self._buffer)
            self._buffer.clear()

        for key in remaining_keys:
            events = buffer_copy.get(key, [])
            if not events:
                continue
            subscription_id = key[0]
            subscription_service = get_webhook_subscription_service()
            subscription = subscription_service.get_subscription(subscription_id)
            if subscription is None:
                continue
            digest_payload = {
                'event_id': str(uuid.uuid4()),
                'event_type': events[0].get('event_type', ''),
                'node_type': events[0].get('node_type', ''),
                'node_id': key[1],
                'timestamp': datetime.now().isoformat(),
                'is_digest': True,
                'digest_event_count': len(events),
                'events': events,
                'source': 'webhook_digest',
                'metadata': {},
            }
            import asyncio
            try:
                asyncio.run(self.delivery_service.deliver_to_subscription(subscription, digest_payload))
            except Exception as e:
                logger.error(f"Failed to flush digest on stop: {e}")


_webhook_subscription_service: Optional[WebhookSubscriptionService] = None
_webhook_delivery_service: Optional[WebhookDeliveryService] = None
_webhook_digest_manager: Optional[WebhookDigestManager] = None


def get_webhook_subscription_service() -> WebhookSubscriptionService:
    global _webhook_subscription_service
    if _webhook_subscription_service is None:
        _webhook_subscription_service = WebhookSubscriptionService()
    return _webhook_subscription_service


def get_webhook_delivery_service() -> WebhookDeliveryService:
    global _webhook_delivery_service
    if _webhook_delivery_service is None:
        _webhook_delivery_service = WebhookDeliveryService()
    return _webhook_delivery_service


def get_webhook_digest_manager() -> WebhookDigestManager:
    global _webhook_digest_manager
    if _webhook_digest_manager is None:
        _webhook_digest_manager = WebhookDigestManager()
    return _webhook_digest_manager
