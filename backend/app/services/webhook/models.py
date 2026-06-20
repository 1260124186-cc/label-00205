import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import Column, BigInteger, String, Float, DateTime, Index, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base

from app.utils.database import Base


class WebhookSubscription(Base):
    __tablename__ = 'sc_webhook_subscriptions'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    name = Column(String(200), nullable=False, comment='订阅名称')
    url = Column(String(500), nullable=False, comment='Webhook URL')
    secret = Column(String(200), comment='HMAC签名密钥')
    event_types = Column(Text, comment='订阅事件类型 JSON: ["status_changed","risk_high","fault_detected"]')
    filter_node_types = Column(Text, comment='节点类型过滤 JSON: ["bolt","flange"]')
    filter_node_ids = Column(Text, comment='节点ID范围过滤 JSON: ["B001","B002"]')
    min_level = Column(Integer, default=0, comment='最低等级过滤 (0=不过滤, 1-4)')
    enabled = Column(Boolean, default=True, comment='是否启用')
    max_retries = Column(Integer, default=5, comment='最大重试次数')
    timeout_seconds = Column(Integer, default=10, comment='HTTP超时秒数')
    enable_digest = Column(Boolean, default=False, comment='是否启用批量合并')
    digest_window_seconds = Column(Integer, default=300, comment='合并窗口秒数（默认5分钟）')
    description = Column(String(500), comment='描述')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_whsub_tenant', 'tenant_id'),
        Index('idx_whsub_enabled', 'enabled'),
        Index('idx_whsub_tenant_enabled', 'tenant_id', 'enabled'),
    )

    def get_event_types(self) -> List[str]:
        if self.event_types:
            try:
                return json.loads(self.event_types)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def get_filter_node_types(self) -> List[str]:
        if self.filter_node_types:
            try:
                return json.loads(self.filter_node_types)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def get_filter_node_ids(self) -> List[str]:
        if self.filter_node_ids:
            try:
                return json.loads(self.filter_node_ids)
            except (json.JSONDecodeError, TypeError):
                return []
        return []


class WebhookDeliveryLog(Base):
    __tablename__ = 'sc_webhook_delivery_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    subscription_id = Column(BigInteger, nullable=False, comment='关联订阅ID')
    event_id = Column(String(64), comment='事件ID')
    event_type = Column(String(50), comment='事件类型')
    node_type = Column(String(20), comment='节点类型')
    node_id = Column(String(100), comment='节点ID')
    payload = Column(Text, comment='请求体 JSON')
    hmac_signature = Column(String(128), comment='HMAC-SHA256签名')
    status = Column(String(20), default='pending', comment='状态 pending/success/failed/dead_letter')
    http_status_code = Column(Integer, comment='HTTP响应状态码')
    response_body = Column(Text, comment='HTTP响应体（截断）')
    retry_count = Column(Integer, default=0, comment='已重试次数')
    next_retry_at = Column(DateTime, comment='下次重试时间')
    error_message = Column(Text, comment='错误信息')
    is_digest = Column(Boolean, default=False, comment='是否为合并推送')
    digest_event_count = Column(Integer, default=0, comment='合并的事件数量')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_whlog_tenant', 'tenant_id'),
        Index('idx_whlog_sub', 'subscription_id'),
        Index('idx_whlog_status', 'status'),
        Index('idx_whlog_event', 'event_id'),
        Index('idx_whlog_node', 'node_type', 'node_id'),
        Index('idx_whlog_tenant_sub', 'tenant_id', 'subscription_id'),
        Index('idx_whlog_tenant_status', 'tenant_id', 'status'),
        Index('idx_whlog_retry', 'status', 'next_retry_at'),
        Index('idx_whlog_time', 'create_time'),
    )


class WebhookDeadLetter(Base):
    __tablename__ = 'sc_webhook_dead_letters'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(BigInteger, comment='租户ID')
    subscription_id = Column(BigInteger, nullable=False, comment='关联订阅ID')
    event_id = Column(String(64), comment='原始事件ID')
    event_type = Column(String(50), comment='事件类型')
    node_type = Column(String(20), comment='节点类型')
    node_id = Column(String(100), comment='节点ID')
    original_payload = Column(Text, comment='原始请求体 JSON')
    last_error = Column(Text, comment='最后一次错误信息')
    total_retries = Column(Integer, default=0, comment='总重试次数')
    dead_letter_reason = Column(String(200), comment='进入死信队列原因')
    original_created_at = Column(DateTime, comment='原始事件创建时间')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_whdl_tenant', 'tenant_id'),
        Index('idx_whdl_sub', 'subscription_id'),
        Index('idx_whdl_event', 'event_id'),
        Index('idx_whdl_node', 'node_type', 'node_id'),
        Index('idx_whdl_time', 'create_time'),
    )
