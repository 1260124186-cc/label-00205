"""
TenantUser API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class TenantUserClient(BaseAPIClient):
    """TenantUser API 客户端"""

    async def create_tenant_user_api_v1_tenants_tenant_id_users_post(
        self,
        tenant_id: int,
        body: TenantUserCreateRequest
) -> TenantUserResponse:
        """
        创建租户用户

        租户管理员自助创建子账号
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/users",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_tenant_users_api_v1_tenants_tenant_id_users_get(
        self,
        tenant_id: int,
        role: Optional[Any] = None,
        status: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> TenantUserListResponse:
        """
        查询租户用户列表

        查询租户下的用户列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/users",
            params={
                "role": role,
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def get_tenant_user_api_v1_tenants_tenant_id_users_user_id_get(
        self,
        tenant_id: int,
        user_id: int
) -> TenantUserResponse:
        """
        获取租户用户详情

        获取租户用户详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/users/{user_id}",
        )

        return response

    async def update_tenant_user_api_v1_tenants_tenant_id_users_user_id_put(
        self,
        tenant_id: int,
        user_id: int,
        body: TenantUserUpdateRequest
) -> TenantUserResponse:
        """
        更新租户用户

        更新租户用户信息(角色、状态等)
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/users/{user_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_tenant_user_api_v1_tenants_tenant_id_users_user_id_delete(
        self,
        tenant_id: int,
        user_id: int
) -> Dict[str, Any]:
        """
        禁用租户用户

        禁用租户用户(软删除)
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/users/{user_id}",
        )

        return response

    async def change_tenant_user_password_api_v1_tenants_tenant_id_users_user_id_password_put(
        self,
        tenant_id: int,
        user_id: int,
        body: TenantUserPasswordRequest
) -> Dict[str, Any]:
        """
        修改租户用户密码

        修改租户用户密码
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/users/{user_id}/password",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response
