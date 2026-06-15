"""
ApiAuditLog API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class ApiAuditLogClient(BaseAPIClient):
    """ApiAuditLog API 客户端"""

    async def query_audit_logs_api_v1_auth_audit_logs_get(
        self,
        key_id: Optional[Any] = None,
        path: Optional[Any] = None,
        method: Optional[Any] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> ApiAuditLogListResponse:
        """
        查询API审计日志
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/auth/audit-logs",
            params={
                "key_id": key_id,
                "path": path,
                "method": method,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
                "offset": offset,
            },
        )

        return response
