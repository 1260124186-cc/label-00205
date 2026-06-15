"""
QuotaManagement API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class QuotaManagementClient(BaseAPIClient):
    """QuotaManagement API 客户端"""

    async def get_tenant_quota_api_v1_tenants_tenant_id_quota_get(
        self,
        tenant_id: int
) -> QuotaResponse:
        """
        获取租户配额

        获取租户的配额和当前用量
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/quota",
        )

        return response

    async def update_tenant_quota_api_v1_tenants_tenant_id_quota_put(
        self,
        tenant_id: int,
        body: QuotaUpdateRequest
) -> QuotaResponse:
        """
        更新租户配额

        更新租户配额上限
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/quota",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response
