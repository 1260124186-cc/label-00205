"""
ApiKeyManagement API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class ApiKeyManagementClient(BaseAPIClient):
    """ApiKeyManagement API 客户端"""

    async def list_api_keys_api_v1_auth_keys_get(
        self
) -> ApiKeyListResponse:
        """
        列出所有API密钥
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/auth/keys",
        )

        return response

    async def create_api_key_api_v1_auth_keys_post(
        self,
        body: ApiKeyCreateRequest
) -> ApiKeyCreateResponse:
        """
        创建API密钥
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/auth/keys",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def rotate_api_key_api_v1_auth_keys_key_id_rotate_post(
        self,
        key_id: str
) -> ApiKeyRotateResponse:
        """
        轮换API密钥
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/auth/keys/{key_id}/rotate",
        )

        return response

    async def revoke_api_key_api_v1_auth_keys_key_id_delete(
        self,
        key_id: str
) -> ApiKeyRevokeResponse:
        """
        吊销API密钥
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/auth/keys/{key_id}",
        )

        return response

    async def get_rate_limit_status_api_v1_auth_keys_key_id_rate_limit_get(
        self,
        key_id: str
) -> RateLimitStatusResponse:
        """
        查询密钥限流状态
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/auth/keys/{key_id}/rate-limit",
        )

        return response
