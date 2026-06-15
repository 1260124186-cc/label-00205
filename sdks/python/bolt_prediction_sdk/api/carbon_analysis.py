"""
CarbonAnalysis API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class CarbonAnalysisClient(BaseAPIClient):
    """CarbonAnalysis API 客户端"""

    async def get_carbon_monthly_ranking_api_v1_carbon_ranking_monthly_post(
        self,
        body: CarbonMonthlyRankingRequest
) -> CarbonMonthlyRankingResponse:
        """
        装置级月度碳排风险贡献排行

        生成装置级月度碳排风险贡献排行
        
        基于预紧力劣化、估算泄漏率、能耗/碳排增量简化模型，
        对各装置进行碳排风险评分与优先级排序。
        
        不强制精确计量，强调趋势与优先级。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/carbon/ranking/monthly",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_hi_carbon_dual_view_api_v1_carbon_hi_dual_view_post(
        self,
        body: HiCarbonDualViewRequest
) -> HiCarbonDualViewResponse:
        """
        HI rollup 与碳排并列展示

        生成健康指数(HI)与碳排风险并列展示数据
        
        每个装置同时展示：
        - HI 分数、等级、趋势
        - 预紧力劣化速率
        - 估算泄漏率
        - 月度碳排增量、碳排风险等级、趋势
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/carbon/hi-dual-view",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def export_esg_report_fragment_api_v1_carbon_esg_export_post(
        self,
        body: EsgReportExportRequest
) -> EsgReportFragmentResponse:
        """
        导出 ESG 报表片段

        导出适用于企业 ESG 报告 / 温室气体排放清单的片段内容
        
        - 支持 json / csv 格式输出
        - 包含汇总数据、Top 高风险装置、趋势分析、建议措施
        - 可选择包含方法学说明
        - 不强制精确计量，强调趋势与优先级
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/carbon/esg/export",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_carbon_model_config_api_v1_carbon_config_get(
        self
) -> CarbonModelConfigResponse:
        """
        获取碳排模型系数配置

        获取当前生效的碳排与能效分析模型系数配置
        
        包含：
        - 预紧力劣化模型参数
        - 泄漏率估算模型参数
        - 能耗与碳排增量模型参数
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/carbon/config",
        )

        return response

    async def update_carbon_model_config_api_v1_carbon_config_post(
        self,
        body: CarbonModelConfigUpdateRequest
) -> CarbonModelConfigResponse:
        """
        更新碳排模型系数配置

        更新碳排与能效分析模型系数配置
        
        支持部分更新，仅传需要修改的参数即可。
        更新后会持久化到数据库配置表，下次启动自动加载。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/carbon/config",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response
