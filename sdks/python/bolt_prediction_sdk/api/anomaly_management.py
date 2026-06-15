"""
AnomalyManagement API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class AnomalyManagementClient(BaseAPIClient):
    """AnomalyManagement API 客户端"""

    async def query_anomalies_api_v1_anomaly_query_post(
        self,
        body: AnomalyQueryRequest
) -> AnomalyListResponse:
        """
        查询异常数据

        查询异常数据，支持多维度过滤：
        - sensor_id: 传感器/螺栓ID
        - 时间范围: start_time ~ end_time
        - anomaly_type: 异常类型
        - classification: 异常分类
        - is_confirmed: 是否已确认
        - is_false_positive: 是否为误报
        - 异常评分范围
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/anomaly/query",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_anomaly_detail_api_v1_anomaly_anomaly_id_get(
        self,
        anomaly_id: int
) -> AnomalyDataResponse:
        """
        获取异常详情

        根据ID获取单条异常记录详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/anomaly/{anomaly_id}",
        )

        return response

    async def confirm_anomaly_api_v1_anomaly_confirm_post(
        self,
        body: AnomalyConfirmRequest
) -> AnomalyDataResponse:
        """
        确认异常（真实异常）

        确认异常为真实异常。
        标记 is_confirmed=True, is_false_positive=False。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/anomaly/confirm",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def mark_anomaly_false_positive_api_v1_anomaly_false_positive_post(
        self,
        body: AnomalyFalsePositiveRequest
) -> AnomalyDataResponse:
        """
        标注异常为误报

        标注异常为误报。
        标记 is_confirmed=True, is_false_positive=True。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/anomaly/false-positive",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def batch_confirm_anomalies_api_v1_anomaly_batch_confirm_post(
        self,
        body: AnomalyBatchConfirmRequest
) -> AnomalyBatchResultResponse:
        """
        批量确认异常

        批量确认异常为真实异常
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/anomaly/batch-confirm",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def batch_mark_false_positives_api_v1_anomaly_batch_false_positive_post(
        self,
        body: AnomalyBatchFalsePositiveRequest
) -> AnomalyBatchResultResponse:
        """
        批量标注误报

        批量标注异常为误报
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/anomaly/batch-false-positive",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_anomaly_statistics_api_v1_anomaly_statistics_summary_get(
        self,
        sensor_id: Optional[Any] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None
) -> AnomalyStatisticsResponse:
        """
        获取异常统计信息

        获取异常统计信息：
        - 异常总数
        - 已确认/未确认数
        - 误报数/真实异常数
        - 误报率
        - 按类型分布
        - 按分类分布
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/anomaly/statistics/summary",
            params={
                "sensor_id": sensor_id,
                "start_time": start_time,
                "end_time": end_time,
            },
        )

        return response

    async def check_anomaly_warning_impact_api_v1_anomaly_warning_impact_sensor_id_get(
        self,
        sensor_id: str,
        current_level: Optional[int] = None
) -> AnomalyWarningImpactResponse:
        """
        检查异常对预警等级的影响

        检查同一时段异常数是否超过阈值，决定是否需要提升预警等级。
        
        - 统计指定时间窗口内的异常数量
        - 与配置的阈值比较
        - 返回是否需要提升预警等级
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/anomaly/warning-impact/{sensor_id}",
            params={
                "current_level": current_level,
            },
        )

        return response
