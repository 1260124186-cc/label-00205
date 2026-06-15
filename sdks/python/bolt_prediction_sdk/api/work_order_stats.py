"""
WorkOrderStats API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class WorkOrderStatsClient(BaseAPIClient):
    """WorkOrderStats API 客户端"""

    async def get_work_order_stats_api_v1_work_orders_stats_summary_get(
        self,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        node_type: Optional[Any] = None,
        priority: Optional[Any] = None
) -> WorkOrderStatsResponse:
        """
        工单统计指标概览

        获取工单统计指标：MTTR、误报率、重复故障率等
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/stats/summary",
            params={
                "start_time": start_time,
                "end_time": end_time,
                "node_type": node_type,
                "priority": priority,
            },
        )

        return response

    async def get_mttr_trend_api_v1_work_orders_stats_mttr_trend_get(
        self,
        days: Optional[int] = None,
        node_type: Optional[Any] = None,
        priority: Optional[Any] = None
) -> MttrTrendResponse:
        """
        MTTR趋势

        获取 MTTR 趋势数据
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/stats/mttr-trend",
            params={
                "days": days,
                "node_type": node_type,
                "priority": priority,
            },
        )

        return response
