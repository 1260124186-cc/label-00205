"""
Monitoring API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class MonitoringClient(BaseAPIClient):
    """Monitoring API 客户端"""

    async def get_metrics_metrics_get(
        self
) -> Dict[str, Any]:
        """
        Get Metrics

        获取 Prometheus 格式的监控指标
        
        返回系统运行指标，包括：
        - HTTP 请求数和延迟
        - 预测请求数和延迟
        - 预测结果分布
        - GPU 利用率
        - 模型加载数
        - 任务成功率
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/metrics",
        )

        return response
