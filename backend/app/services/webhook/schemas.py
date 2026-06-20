from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class WebhookSubscriptionCreate(BaseModel):
    name: str = Field(..., max_length=200)
    url: str = Field(...)
    secret: Optional[str] = None
    event_types: List[str] = Field(...)
    filter_node_types: Optional[List[str]] = None
    filter_node_ids: Optional[List[str]] = None
    min_level: int = Field(default=0, ge=0, le=4)
    enabled: bool = True
    max_retries: int = Field(default=5, ge=0)
    timeout_seconds: int = Field(default=10, ge=1)
    enable_digest: bool = False
    digest_window_seconds: int = Field(default=300, ge=1)
    description: Optional[str] = None


class WebhookSubscriptionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    url: Optional[str] = None
    secret: Optional[str] = None
    event_types: Optional[List[str]] = None
    filter_node_types: Optional[List[str]] = None
    filter_node_ids: Optional[List[str]] = None
    min_level: Optional[int] = Field(None, ge=0, le=4)
    enabled: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    enable_digest: Optional[bool] = None
    digest_window_seconds: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None


class WebhookSubscriptionResponse(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    name: str
    url: str
    secret: Optional[str] = None
    event_types: Optional[List[str]] = []
    filter_node_types: Optional[List[str]] = []
    filter_node_ids: Optional[List[str]] = []
    min_level: int = 0
    enabled: bool = True
    max_retries: int = 5
    timeout_seconds: int = 10
    enable_digest: bool = False
    digest_window_seconds: int = 300
    description: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            tenant_id=obj.tenant_id,
            name=obj.name,
            url=obj.url,
            secret=obj.secret,
            event_types=obj.get_event_types() if hasattr(obj, 'get_event_types') else [],
            filter_node_types=obj.get_filter_node_types() if hasattr(obj, 'get_filter_node_types') else [],
            filter_node_ids=obj.get_filter_node_ids() if hasattr(obj, 'get_filter_node_ids') else [],
            min_level=obj.min_level or 0,
            enabled=obj.enabled if obj.enabled is not None else True,
            max_retries=obj.max_retries if obj.max_retries is not None else 5,
            timeout_seconds=obj.timeout_seconds if obj.timeout_seconds is not None else 10,
            enable_digest=obj.enable_digest if obj.enable_digest is not None else False,
            digest_window_seconds=obj.digest_window_seconds if obj.digest_window_seconds is not None else 300,
            description=obj.description,
            create_time=obj.create_time,
            update_time=obj.update_time,
        )

    class Config:
        from_attributes = True


class WebhookSubscriptionListResponse(BaseModel):
    items: List[WebhookSubscriptionResponse]
    total: int
    page: int
    page_size: int


class WebhookDeliveryLogResponse(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    subscription_id: int
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    status: str
    http_status_code: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    is_digest: bool = False
    digest_event_count: int = 0
    create_time: datetime
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookDeliveryLogListResponse(BaseModel):
    items: List[WebhookDeliveryLogResponse]
    total: int
    page: int
    page_size: int


class WebhookDeadLetterResponse(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    subscription_id: int
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    node_type: Optional[str] = None
    node_id: Optional[str] = None
    last_error: Optional[str] = None
    total_retries: int = 0
    dead_letter_reason: Optional[str] = None
    original_created_at: Optional[datetime] = None
    create_time: datetime

    class Config:
        from_attributes = True


class WebhookDeadLetterListResponse(BaseModel):
    items: List[WebhookDeadLetterResponse]
    total: int
    page: int
    page_size: int


class WebhookTestResponse(BaseModel):
    success: bool
    http_status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
