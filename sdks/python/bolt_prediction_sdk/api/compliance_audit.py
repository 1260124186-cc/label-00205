"""
ComplianceAudit API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class ComplianceAuditClient(BaseAPIClient):
    """ComplianceAudit API 客户端"""

    async def list_audit_records_api_v1_audit_records_get(
        self,
        node_type: Optional[Any] = None,
        node_id: Optional[Any] = None,
        model_version: Optional[Any] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> AuditListResponse:
        """
        查询审计记录列表

        查询预测审计记录列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/audit/records",
            params={
                "node_type": node_type,
                "node_id": node_id,
                "model_version": model_version,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def get_audit_record_api_v1_audit_records_audit_id_get(
        self,
        audit_id: int
) -> AuditRecordResponse:
        """
        获取审计记录详情

        获取单条审计记录详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/audit/records/{audit_id}",
        )

        return response

    async def update_audit_retention_api_v1_audit_records_audit_id_retention_put(
        self,
        audit_id: int,
        body: AuditRetentionUpdateRequest
) -> AuditRecordResponse:
        """
        更新审计记录保留年限

        更新审计记录的保留年限（可配置 N 年保留）
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/audit/records/{audit_id}/retention",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def cleanup_expired_audits_api_v1_audit_cleanup_post(
        self
) -> AuditCleanupResponse:
        """
        清理过期审计记录

        清理已过期的审计记录
        
        根据每条记录的 expire_time 判断是否过期，自动删除。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/audit/cleanup",
        )

        return response

    async def export_audit_package_api_v1_audit_export_post(
        self,
        body: AuditExportRequest
) -> Dict[str, Any]:
        """
        导出审计包

        按时间范围导出审计包
        
        支持 CSV 和 PDF 格式:
        - CSV: 返回纯文本 CSV 数据
        - PDF: 返回 HTML 格式（可转 PDF）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/audit/export",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_explainability_report_api_v1_audit_records_audit_id_explainability_get(
        self,
        audit_id: int
) -> ExplainabilityReportResponse:
        """
        获取可解释性报告

        获取指定审计记录的可解释性报告
        
        包含:
        - LSTM 注意力权重
        - 关键时间步
        - 风险因子分解
        - 规则命中项
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/audit/records/{audit_id}/explainability",
        )

        return response
