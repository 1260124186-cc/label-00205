"""
DataQuality API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class DataQualityClient(BaseAPIClient):
    """DataQuality API 客户端"""

    async def check_data_quality_api_v1_data_quality_check_post(
        self,
        body: DataQualityCheckRequest
) -> QualityEvaluationResponse:
        """
        评估传感器数据质量

        评估传感器数据质量（完整流程）
        
        包含:
        - 5项质量规则检查（缺失率、重复、时间倒挂、越界、漂移）
        - 多维度质量评分
        - 数据过滤建议
        - 异常分类（可选）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/data-quality/check",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def batch_check_data_quality_api_v1_data_quality_batch_check_post(
        self,
        body: DataQualityCheckBatchRequest
) -> Dict[str, Any]:
        """
        批量评估传感器数据质量

        批量评估多个传感器的数据质量
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/data-quality/batch-check",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_sensor_quality_score_api_v1_data_quality_score_sensor_id_get(
        self,
        sensor_id: str,
        recent_data_limit: Optional[int] = None
) -> SensorQualityScoreSchema:
        """
        获取传感器质量评分

        获取传感器的质量评分
        
        从数据库读取最近数据进行评估。
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/data-quality/score/{sensor_id}",
            params={
                "recent_data_limit": recent_data_limit,
            },
        )

        return response

    async def adjust_prediction_confidence_api_v1_data_quality_adjust_confidence_post(
        self,
        body: ConfidenceAdjustmentRequest
) -> ConfidenceAdjustmentResponse:
        """
        调整预测置信度

        根据数据质量调整预测置信度
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/data-quality/adjust-confidence",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def generate_quality_report_api_v1_data_quality_report_generate_post(
        self,
        body: QualityReportRequest
) -> DailyQualityReportSchema:
        """
        生成每日质量报告

        生成每日数据质量报告
        
        包含:
        - 整体质量统计
        - 问题传感器排行
        - 修复建议列表
        - 异常分类统计
        - 质量趋势分析
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/data-quality/report/generate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_latest_quality_report_api_v1_data_quality_report_latest_get(
        self
) -> DailyQualityReportSchema:
        """
        获取最新质量报告

        从数据库获取最新的质量报告
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/data-quality/report/latest",
        )

        return response

    async def get_sensor_quality_history_api_v1_data_quality_history_sensor_id_get(
        self,
        body: DataQualityHistoryRequest
) -> Dict[str, Any]:
        """
        获取传感器质量历史记录

        获取传感器的质量检查历史记录
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/data-quality/history/{sensor_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_problem_sensors_api_v1_data_quality_problem_sensors_get(
        self,
        min_score: Optional[float] = None,
        limit: Optional[int] = None
) -> Dict[str, Any]:
        """
        获取问题传感器列表

        获取问题传感器列表（按问题严重程度排序）
        
        Args:
            min_score: 低于此分数的传感器被视为问题传感器
            limit: 返回数量限制
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/data-quality/problem-sensors",
            params={
                "min_score": min_score,
                "limit": limit,
            },
        )

        return response

    async def classify_sensor_anomalies_api_v1_data_quality_anomalies_sensor_id_classify_get(
        self,
        sensor_id: str,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        recent_data_limit: Optional[int] = None
) -> Dict[str, Any]:
        """
        分类传感器异常

        分类传感器异常，区分真异常与采集异常
        
        从数据库获取异常数据和原始数据进行分析。
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/data-quality/anomalies/{sensor_id}/classify",
            params={
                "start_time": start_time,
                "end_time": end_time,
                "recent_data_limit": recent_data_limit,
            },
        )

        return response

    async def get_data_quality_summary_api_v1_data_quality_summary_get(
        self,
        days: Optional[int] = None
) -> Dict[str, Any]:
        """
        获取数据质量总览

        获取数据质量总览
        
        包含:
        - 整体质量分布
        - 质量趋势
        - 问题统计
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/data-quality/summary",
            params={
                "days": days,
            },
        )

        return response
