"""
CMMSIntegration API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class CmmsIntegrationClient(BaseAPIClient):
    """CMMSIntegration API 客户端"""

    async def list_cmms_configs_api_v1_cmms_configs_get(
        self,
        enabled: Optional[Any] = None,
        system_type: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> CmmsConfigListResponse:
        """
        查询CMMS配置列表

        查询 CMMS/EAM 集成配置列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/cmms/configs",
            params={
                "enabled": enabled,
                "system_type": system_type,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def create_cmms_config_api_v1_cmms_configs_post(
        self,
        body: CmmsConfigCreate
) -> CmmsConfigResponse:
        """
        创建CMMS配置

        创建 CMMS/EAM 集成配置
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/cmms/configs",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_cmms_config_api_v1_cmms_configs_config_id_get(
        self,
        config_id: int
) -> CmmsConfigResponse:
        """
        获取CMMS配置详情

        获取 CMMS 配置详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/cmms/configs/{config_id}",
        )

        return response

    async def update_cmms_config_api_v1_cmms_configs_config_id_put(
        self,
        config_id: int,
        body: CmmsConfigUpdate
) -> CmmsConfigResponse:
        """
        更新CMMS配置

        更新 CMMS 配置
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/cmms/configs/{config_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_cmms_config_api_v1_cmms_configs_config_id_delete(
        self,
        config_id: int
) -> Dict[str, Any]:
        """
        删除CMMS配置

        删除 CMMS 配置
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/cmms/configs/{config_id}",
        )

        return response

    async def sync_work_order_to_cmms_api_v1_cmms_sync_work_order_post(
        self,
        body: CmmsSyncRequest
) -> CmmsSyncResponse:
        """
        同步工单到CMMS

        手动同步工单到 CMMS/EAM 系统
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/cmms/sync/work-order",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def cmms_webhook_callback_api_v1_cmms_webhook_config_id_post(
        self,
        config_id: int,
        body: Dict[str, Any],
        x_signature: Optional[Any] = None
) -> CmmsWebhookResponse:
        """
        CMMS Webhook回调

        接收 CMMS 系统的 Webhook 回调
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/cmms/webhook/{config_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
            params={
                "X-Signature": x_signature,
            },
        )

        return response

    async def list_cmms_sync_logs_api_v1_cmms_sync_logs_get(
        self,
        config_id: Optional[Any] = None,
        work_order_id: Optional[Any] = None,
        status: Optional[Any] = None,
        sync_direction: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> CmmsSyncLogListResponse:
        """
        查询CMMS同步日志

        查询 CMMS 同步日志
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/cmms/sync-logs",
            params={
                "config_id": config_id,
                "work_order_id": work_order_id,
                "status": status,
                "sync_direction": sync_direction,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def retry_cmms_sync_api_v1_cmms_sync_logs_log_id_retry_post(
        self,
        log_id: int
) -> CmmsSyncResponse:
        """
        重试CMMS同步

        重试失败的 CMMS 同步
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/cmms/sync-logs/{log_id}/retry",
        )

        return response
