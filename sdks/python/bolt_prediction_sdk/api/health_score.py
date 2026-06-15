"""
HealthScore API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class HealthScoreClient(BaseAPIClient):
    """HealthScore API 客户端"""

    async def calculate_health_index_api_v1_health_calculate_post(
        self,
        body: HealthIndexCalculateRequest
) -> HealthIndexResponse:
        """
        计算螺栓健康度指数 HI

        计算单个螺栓的健康度指数 HI（0-100）
        
        综合评估维度：
        - 预紧力稳定性（30%）
        - 预警频率（20%）
        - 故障历史（20%）
        - 环境应力（15%）
        - 使用年限（15%）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/health/calculate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def calculate_health_index_batch_api_v1_health_calculate_batch_post(
        self,
        body: HealthIndexBatchCalculateRequest
) -> HealthIndexBatchResponse:
        """
        批量计算螺栓健康度

        批量计算多个螺栓的健康度，或计算整个法兰面的健康度
        
        支持两种模式：
        1. 批量螺栓计算：传入多个螺栓数据
        2. 法兰面聚合计算：传入法兰面ID和螺栓数据，自动聚合
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/health/calculate/batch",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_health_history_api_v1_health_history_get(
        self,
        node_id: str,
        node_type: Optional[str] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: Optional[int] = None
) -> HealthIndexHistoryResponse:
        """
        查询健康度历史记录

        查询螺栓或法兰面的健康度历史记录，包含趋势分析
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/health/history",
            params={
                "node_id": node_id,
                "node_type": node_type,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            },
        )

        return response

    async def predict_rul_api_v1_health_rul_predict_post(
        self,
        body: RulPredictionRequest
) -> RulPredictionResponse:
        """
        预测剩余使用寿命 RUL

        基于历史健康度序列预测剩余使用寿命（RUL）
        
        支持的劣化模型：
        - linear: 线性模型（默认，数据不足时使用）
        - exponential: 指数模型
        - polynomial: 多项式模型
        - auto: 自动选择最优模型（根据R²拟合优度）
        
        返回结果包含：
        - RUL 预测值及置信区间
        - 劣化曲线预测序列
        - 到达预警阈值的时间
        - 模型拟合优度 R²
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/health/rul/predict",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def generate_health_rollup_api_v1_health_rollup_post(
        self,
        body: HealthRollupRequest
) -> HealthRollupResponse:
        """
        生成产线/装置级健康度汇总报表

        生成产线或装置级的健康度汇总报表
        
        包含：
        - 整体健康度评分和等级
        - 各法兰面健康度统计
        - 风险汇总分析
        - 维护优先级排序
        - 劣化速率统计
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/health/rollup",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response
