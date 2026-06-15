"""
MultiTenant API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class MultiTenantClient(BaseAPIClient):
    """MultiTenant API 客户端"""

    async def tenant_login_api_v1_tenant_login_post(
        self,
        body: TenantLoginRequest
) -> TenantLoginResponse:
        """
        租户用户登录

        租户用户登录, 返回令牌
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/tenant/login",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_current_tenant_user_api_v1_tenant_me_get(
        self
) -> Dict[str, Any]:
        """
        获取当前登录用户信息

        获取当前登录用户的信息（通过 X-Tenant-Token 或 X-Tenant-API-Key）
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenant/me",
        )

        return response

    async def tenant_logout_api_v1_tenant_logout_post(
        self
) -> Dict[str, Any]:
        """
        租户用户登出

        登出，撤销当前登录令牌
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/tenant/logout",
        )

        return response

    async def create_tenant_api_v1_tenants_post(
        self,
        body: TenantCreateRequest
) -> TenantResponse:
        """
        创建租户

        创建新租户, 自动创建默认配额和管理员账号
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/tenants",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_tenants_api_v1_tenants_get(
        self,
        status: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> TenantListResponse:
        """
        查询租户列表

        查询租户列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants",
            params={
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def get_tenant_api_v1_tenants_tenant_id_get(
        self,
        tenant_id: int
) -> TenantResponse:
        """
        获取租户详情

        获取租户详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}",
        )

        return response

    async def update_tenant_api_v1_tenants_tenant_id_put(
        self,
        tenant_id: int,
        body: TenantUpdateRequest
) -> TenantResponse:
        """
        更新租户

        更新租户信息
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/tenants/{tenant_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_tenant_api_v1_tenants_tenant_id_delete(
        self,
        tenant_id: int
) -> Dict[str, Any]:
        """
        删除租户

        软删除租户
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/tenants/{tenant_id}",
        )

        return response
