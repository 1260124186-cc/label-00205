"""
Organization API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class OrganizationClient(BaseAPIClient):
    """Organization API 客户端"""

    async def create_org_node_api_v1_tenants_tenant_id_org_nodes_post(
        self,
        tenant_id: int,
        body: OrgNodeCreateRequest
) -> OrgNodeResponse:
        """
        创建组织节点

        创建组织节点
        
        层级: 集团(group) → 工厂(factory) → 装置(unit) → 法兰面(flange) → 螺栓(bolt)
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_org_nodes_api_v1_tenants_tenant_id_org_nodes_get(
        self,
        tenant_id: int,
        parent_id: Optional[Any] = None,
        node_type: Optional[Any] = None,
        status: Optional[Any] = None
) -> Dict[str, Any]:
        """
        查询组织节点列表

        查询组织节点列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes",
            params={
                "parent_id": parent_id,
                "node_type": node_type,
                "status": status,
            },
        )

        return response

    async def get_org_tree_api_v1_tenants_tenant_id_org_tree_get(
        self,
        tenant_id: int
) -> OrgTreeResponse:
        """
        获取组织架构树

        获取租户的完整组织架构树
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/tree",
        )

        return response

    async def get_org_node_api_v1_tenants_tenant_id_org_nodes_node_id_get(
        self,
        tenant_id: int,
        node_id: int
) -> OrgNodeResponse:
        """
        获取组织节点详情

        获取组织节点详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes/{node_id}",
        )

        return response

    async def update_org_node_api_v1_tenants_tenant_id_org_nodes_node_id_put(
        self,
        tenant_id: int,
        node_id: int,
        body: OrgNodeUpdateRequest
) -> OrgNodeResponse:
        """
        更新组织节点

        更新组织节点
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes/{node_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_org_node_api_v1_tenants_tenant_id_org_nodes_node_id_delete(
        self,
        tenant_id: int,
        node_id: int
) -> Dict[str, Any]:
        """
        删除组织节点

        删除组织节点(存在子节点时不可删除)
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes/{node_id}",
        )

        return response

    async def get_org_ancestors_api_v1_tenants_tenant_id_org_nodes_node_id_ancestors_get(
        self,
        tenant_id: int,
        node_id: int
) -> Dict[str, Any]:
        """
        获取祖先节点

        获取指定节点的所有祖先节点(从集团到父节点)
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes/{node_id}/ancestors",
        )

        return response

    async def get_org_descendants_api_v1_tenants_tenant_id_org_nodes_node_id_descendants_get(
        self,
        tenant_id: int,
        node_id: int
) -> Dict[str, Any]:
        """
        获取后代节点

        获取指定节点的所有后代节点
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/tenants/{tenant_id}/org/nodes/{node_id}/descendants",
        )

        return response
