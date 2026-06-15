"""
NotificationChannel API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class NotificationChannelClient(BaseAPIClient):
    """NotificationChannel API 客户端"""

    async def list_notification_channels_api_v1_notification_channels_get(
        self
) -> List[NotificationChannelResponse]:
        """
        查询通知渠道列表

        查询所有通知渠道
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/notification/channels",
        )

        return response

    async def create_notification_channel_api_v1_notification_channels_post(
        self,
        body: NotificationChannelCreate
) -> NotificationChannelResponse:
        """
        创建通知渠道

        创建通知渠道
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/notification/channels",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def update_notification_channel_api_v1_notification_channels_channel_id_put(
        self,
        channel_id: int,
        body: NotificationChannelUpdate
) -> NotificationChannelResponse:
        """
        更新通知渠道

        更新通知渠道
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/notification/channels/{channel_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_notification_channel_api_v1_notification_channels_channel_id_delete(
        self,
        channel_id: int
) -> Dict[str, Any]:
        """
        删除通知渠道

        删除通知渠道
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/notification/channels/{channel_id}",
        )

        return response

    async def list_notification_logs_api_v1_notification_logs_get(
        self,
        alert_id: Optional[Any] = None,
        status: Optional[Any] = None,
        limit: Optional[int] = None
) -> List[NotificationLogResponse]:
        """
        查询通知发送日志

        查询通知发送日志
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/notification/logs",
            params={
                "alert_id": alert_id,
                "status": status,
                "limit": limit,
            },
        )

        return response
