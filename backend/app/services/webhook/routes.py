import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from loguru import logger

from app.api.auth import verify_api_key
from app.services.webhook.schemas import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionListResponse,
    WebhookDeliveryLogListResponse,
    WebhookDeadLetterListResponse,
    WebhookTestResponse,
)
from app.services.webhook import get_webhook_subscription_service, get_webhook_delivery_service

router = APIRouter(prefix="/webhooks", dependencies=[Depends(verify_api_key)])


@router.post(
    "/subscriptions",
    response_model=WebhookSubscriptionResponse,
    tags=["Webhook出站"],
)
async def create_subscription(body: WebhookSubscriptionCreate):
    try:
        service = get_webhook_subscription_service()
        result = service.create_subscription(body.model_dump())
        if result is None:
            raise HTTPException(status_code=500, detail="创建订阅失败")
        return WebhookSubscriptionResponse.from_orm(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建Webhook订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subscriptions",
    response_model=WebhookSubscriptionListResponse,
    tags=["Webhook出站"],
)
async def list_subscriptions(
    tenant_id: int = Query(..., description="租户ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = Query(None),
):
    try:
        service = get_webhook_subscription_service()
        enabled_only = enabled if enabled is not None else True
        items, total = service.list_subscriptions(
            tenant_id=tenant_id, page=page, page_size=page_size, enabled_only=enabled_only
        )
        response_items = [WebhookSubscriptionResponse.from_orm(item) for item in items]
        return WebhookSubscriptionListResponse(items=response_items, total=total, page=page, page_size=page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询Webhook订阅列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    tags=["Webhook出站"],
)
async def get_subscription(subscription_id: int):
    try:
        service = get_webhook_subscription_service()
        result = service.get_subscription(subscription_id)
        if result is None:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return WebhookSubscriptionResponse.from_orm(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询Webhook订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    tags=["Webhook出站"],
)
async def update_subscription(subscription_id: int, body: WebhookSubscriptionUpdate):
    try:
        service = get_webhook_subscription_service()
        data = body.model_dump(exclude_unset=True)
        result = service.update_subscription(subscription_id, data)
        if result is None:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return WebhookSubscriptionResponse.from_orm(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新Webhook订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/subscriptions/{subscription_id}",
    tags=["Webhook出站"],
)
async def delete_subscription(subscription_id: int):
    try:
        service = get_webhook_subscription_service()
        success = service.delete_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="订阅不存在")
        return {"success": True, "message": "订阅已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除Webhook订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/delivery-logs",
    response_model=WebhookDeliveryLogListResponse,
    tags=["Webhook出站"],
)
async def list_delivery_logs(
    subscription_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        service = get_webhook_delivery_service()
        items, total = service.get_delivery_logs(
            subscription_id=subscription_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        return WebhookDeliveryLogListResponse(items=items, total=total, page=page, page_size=page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询Webhook投递日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/dead-letters",
    response_model=WebhookDeadLetterListResponse,
    tags=["Webhook出站"],
)
async def list_dead_letters(
    subscription_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        service = get_webhook_delivery_service()
        items, total = service.get_dead_letters(
            subscription_id=subscription_id,
            page=page,
            page_size=page_size,
        )
        return WebhookDeadLetterListResponse(items=items, total=total, page=page, page_size=page_size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询Webhook死信队列失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/subscriptions/{subscription_id}/test",
    response_model=WebhookTestResponse,
    tags=["Webhook出站"],
)
async def test_subscription(subscription_id: int):
    try:
        service = get_webhook_subscription_service()
        subscription = service.get_subscription(subscription_id)
        if subscription is None:
            raise HTTPException(status_code=404, detail="订阅不存在")

        delivery_service = get_webhook_delivery_service()
        import asyncio
        test_event = {
            "event_id": "test-" + str(uuid.uuid4())[:8],
            "event_type": "test",
            "node_type": "test_node",
            "node_id": "test_device",
            "timestamp": datetime.now().isoformat(),
            "data": {"test": True},
            "source": "webhook_test",
            "metadata": {},
        }
        result = await delivery_service.deliver_to_subscription(subscription, test_event)

        last_log = delivery_service.get_delivery_logs(subscription_id=subscription_id, page=1, page_size=1)
        log_item = last_log[0][0] if last_log[0] else None

        return WebhookTestResponse(
            success=log_item.status == 'success' if log_item else False,
            http_status_code=log_item.http_status_code if log_item else None,
            error_message=log_item.error_message if log_item else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试Webhook订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/retries/process",
    tags=["Webhook出站"],
)
async def process_retries():
    try:
        service = get_webhook_delivery_service()
        await service.process_pending_retries()
        return {"success": True, "message": "重试处理已执行"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动触发重试处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
