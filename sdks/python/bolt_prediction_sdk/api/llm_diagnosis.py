"""
LLMDiagnosis API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class LlmDiagnosisClient(BaseAPIClient):
    """LLMDiagnosis API 客户端"""

    async def generate_diagnosis_report_api_v1_report_diagnosis_post(
        self,
        body: DiagnosisReportRequest
) -> DiagnosisReportResponse:
        """
        生成单次诊断报告

        生成单次诊断报告（可选调用 LLM）
        
        输入结构化数据，输出诊断摘要、推荐措施和紧急程度。
        LLM 不可用时自动降级到模板生成。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/report/diagnosis",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def generate_periodic_report_api_v1_report_generate_post(
        self,
        body: ReportGenerateRequest
) -> PeriodicReportResponse:
        """
        生成周期报告（周报/月报）

        按 bolt_id/flange_id 聚合近期预测生成周报/月报
        
        - report_type: weekly（周报）/ monthly（月报）
        - use_llm: 是否使用 LLM 生成（默认 True，不可用时自动降级）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/report/generate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def batch_generate_periodic_reports_api_v1_report_batch_generate_post(
        self,
        body: BatchReportGenerateRequest
) -> BatchReportResponse:
        """
        批量生成周期报告

        批量生成多个节点的周期报告（周报/月报）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/report/batch-generate",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_llm_config_status_api_v1_report_config_get(
        self
) -> Dict[str, Any]:
        """
        获取 LLM 配置状态

        获取 LLM 配置状态，包括是否启用、当前 provider、支持的功能等
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/report/config",
        )

        return response
