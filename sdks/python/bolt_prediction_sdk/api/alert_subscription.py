"""
AlertSubscription API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class AlertSubscriptionClient(BaseAPIClient):
    """AlertSubscription API 客户端"""

    async def list_alert_subscriptions_api_v1_alert_subscriptions_get(
        self,
        subscriber_type: Optional[Any] = None,
        subscriber_id: Optional[Any] = None,
        enabled: Optional[Any] = None
) -> List[AlertSubscriptionResponse]:
        """
        查询订阅列表

        查询告警订阅列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/alert/subscriptions",
            params={
                "subscriber_type": subscriber_type,
                "subscriber_id": subscriber_id,
                "enabled": enabled,
            },
        )

        return response

    async def create_alert_subscription_api_v1_alert_subscriptions_post(
        self,
        body: AlertSubscriptionCreate
) -> AlertSubscriptionResponse:
        """
        创建订阅

        创建告警订阅
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/alert/subscriptions",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_alert_subscription_api_v1_alert_subscriptions_sub_id_get(
        self,
        sub_id: int
) -> AlertSubscriptionResponse:
        """
        获取订阅详情

        获取单个订阅详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/alert/subscriptions/{sub_id}",
        )

        return response

    async def update_alert_subscription_api_v1_alert_subscriptions_sub_id_put(
        self,
        sub_id: int,
        body: AlertSubscriptionUpdate
) -> AlertSubscriptionResponse:
        """
        更新订阅

        更新告警订阅
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/alert/subscriptions/{sub_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_alert_subscription_api_v1_alert_subscriptions_sub_id_delete(
        self,
        sub_id: int
) -> Dict[str, Any]:
        """
        删除订阅

        删除告警订阅
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/alert/subscriptions/{sub_id}",
        )

        return response
