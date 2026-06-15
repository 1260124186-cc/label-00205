"""
KnowledgeBase API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class KnowledgeBaseClient(BaseAPIClient):
    """KnowledgeBase API 客户端"""

    async def create_knowledge_case_api_v1_knowledge_cases_post(
        self,
        body: KnowledgeCaseCreateRequest
) -> Dict[str, Any]:
        """
        创建案例

        创建新的知识库案例
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/knowledge/cases",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_knowledge_cases_api_v1_knowledge_cases_get(
        self,
        status: Optional[Any] = None,
        node_type: Optional[Any] = None,
        fault_type: Optional[Any] = None,
        fault_level: Optional[Any] = None,
        tenant_id: Optional[Any] = None,
        keyword: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> KnowledgeCaseListResponse:
        """
        查询案例列表

        查询知识库案例列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/cases",
            params={
                "status": status,
                "node_type": node_type,
                "fault_type": fault_type,
                "fault_level": fault_level,
                "tenant_id": tenant_id,
                "keyword": keyword,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def get_knowledge_case_api_v1_knowledge_cases_case_id_get(
        self,
        case_id: int
) -> Dict[str, Any]:
        """
        获取案例详情

        获取单条案例详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}",
        )

        return response

    async def update_knowledge_case_api_v1_knowledge_cases_case_id_put(
        self,
        case_id: int,
        body: KnowledgeCaseUpdateRequest
) -> Dict[str, Any]:
        """
        更新案例

        更新案例（自动创建新版本）
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_knowledge_case_api_v1_knowledge_cases_case_id_delete(
        self,
        case_id: int
) -> Dict[str, Any]:
        """
        删除案例

        删除案例及其版本和审核记录
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}",
        )

        return response

    async def submit_case_for_review_api_v1_knowledge_cases_case_id_submit_review_post(
        self,
        case_id: int,
        operator_id: Optional[Any] = None,
        operator_name: Optional[Any] = None
) -> Dict[str, Any]:
        """
        提交审核

        将案例提交审核
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/submit-review",
            params={
                "operator_id": operator_id,
                "operator_name": operator_name,
            },
        )

        return response

    async def review_knowledge_case_api_v1_knowledge_cases_case_id_review_post(
        self,
        case_id: int,
        body: CaseReviewRequest
) -> Dict[str, Any]:
        """
        审核案例

        审核案例（通过/驳回/需修改）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/review",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_case_reviews_api_v1_knowledge_cases_case_id_reviews_get(
        self,
        case_id: int
) -> Dict[str, Any]:
        """
        获取审核记录

        获取案例的审核历史记录
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/reviews",
        )

        return response

    async def list_case_versions_api_v1_knowledge_cases_case_id_versions_get(
        self,
        case_id: int
) -> Dict[str, Any]:
        """
        获取版本历史

        获取案例的版本历史
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/versions",
        )

        return response

    async def get_case_version_api_v1_knowledge_cases_case_id_versions_version_get(
        self,
        case_id: int,
        version: int
) -> Dict[str, Any]:
        """
        获取指定版本

        获取案例的指定版本详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/versions/{version}",
        )

        return response

    async def compare_case_versions_api_v1_knowledge_cases_case_id_versions_compare_get(
        self,
        case_id: int,
        version_from: int,
        version_to: int
) -> Dict[str, Any]:
        """
        对比版本差异

        对比两个版本之间的差异
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/versions/compare",
            params={
                "version_from": version_from,
                "version_to": version_to,
            },
        )

        return response

    async def revert_case_to_version_api_v1_knowledge_cases_case_id_versions_version_revert_post(
        self,
        case_id: int,
        version: int,
        operator_id: Optional[Any] = None,
        operator_name: Optional[Any] = None
) -> Dict[str, Any]:
        """
        回退到指定版本

        回退案例到指定版本（会创建新版本）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/knowledge/cases/{case_id}/versions/{version}/revert",
            params={
                "operator_id": operator_id,
                "operator_name": operator_name,
            },
        )

        return response

    async def search_similar_cases_api_v1_knowledge_cases_search_similar_post(
        self,
        body: CaseSimilaritySearchRequest
) -> Dict[str, Any]:
        """
        检索相似案例 (Top-K)

        基于特征向量检索 Top-K 相似案例
        
        相似度基于:
        - 58维传感器特征向量（余弦相似度）
        - 故障类型匹配
        - 节点类型匹配
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/knowledge/cases/search/similar",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_case_recommendations_api_v1_knowledge_cases_recommend_post(
        self,
        body: CaseSimilaritySearchRequest
) -> Dict[str, Any]:
        """
        获取案例推荐 (推荐措施 + RAG上下文)

        获取案例推荐，包含聚合推荐措施和 RAG 上下文
        
        返回:
        - Top-K 相似案例
        - 聚合推荐措施列表
        - RAG 上下文字符串（可直接传给LLM）
        - 置信度分数
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/knowledge/cases/recommend",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_knowledge_statistics_api_v1_knowledge_statistics_get(
        self,
        tenant_id: Optional[Any] = None
) -> Dict[str, Any]:
        """
        获取知识库统计

        获取知识库统计信息
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/knowledge/statistics",
            params={
                "tenant_id": tenant_id,
            },
        )

        return response
