"""
TenantApiKey API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class TenantApiKeyClient(BaseAPIClient):
    """TenantApiKey API 客户端"""

    async def create_tenant_api_key_api_v1_tenants_tenant_id_api_keys_post(
        self,
        tenant_id: int,
        body: TenantApiKeyCreateRequest
) -> TenantApiKeyCreateResponse:
        """
        创建租户API Key

        创建租户 API Key
        
        明文密钥仅在创建时返回一次, 之后无法再查看。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/api-keys",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_tenant_api_keys_api_v1_tenants_tenant_id_api_keys_get(
        self,
        tenant_id: int,
        status: Optional[Any] = None
) -> Dict[str, Any]:
        """
        查询租户API Key列表

        查询租户下的API Key列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/api-keys",
            params={
                "status": status,
            },
        )

        return response

    async def get_tenant_api_key_api_v1_tenants_tenant_id_api_keys_key_id_get(
        self,
        tenant_id: int,
        key_id: int
) -> TenantApiKeyResponse:
        """
        获取API Key详情

        获取API Key详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/api-keys/{key_id}",
        )

        return response

    async def update_tenant_api_key_api_v1_tenants_tenant_id_api_keys_key_id_put(
        self,
        tenant_id: int,
        key_id: int,
        body: TenantApiKeyUpdateRequest
) -> TenantApiKeyResponse:
        """
        更新API Key

        更新API Key(名称、权限、速率限制等)
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/api-keys/{key_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def revoke_tenant_api_key_api_v1_tenants_tenant_id_api_keys_key_id_delete(
        self,
        tenant_id: int,
        key_id: int
) -> Dict[str, Any]:
        """
        吊销API Key

        吊销API Key
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/api-keys/{key_id}",
        )

        return response
