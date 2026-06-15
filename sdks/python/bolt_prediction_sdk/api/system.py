"""
System API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class SystemClient(BaseAPIClient):
    """System API 客户端"""

    async def health_check_health_get(
        self
) -> HealthResponse:
        """
        健康检查（公开免鉴权）
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/health",
        )

        return response
