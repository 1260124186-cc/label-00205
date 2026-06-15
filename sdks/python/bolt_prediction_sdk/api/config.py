"""
Config API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class ConfigClient(BaseAPIClient):
    """Config API 客户端"""

    async def get_strategy_config_api_v1_strategy_config_get(
        self,
        node_type: Optional[Any] = None,
        node_id: Optional[Any] = None
) -> EffectiveStrategyResponse:
        """
        查询当前生效策略

        查询当前生效的预警策略
        
        - 不传参数：返回全局策略
        - 传入 node_type + node_id：返回该节点的生效策略（含节点覆盖）
        - 节点级覆盖优先于全局策略
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/strategy/config",
            params={
                "node_type": node_type,
                "node_id": node_id,
            },
        )

        return response

    async def update_strategy_config_api_v1_strategy_config_post(
        self,
        body: StrategyConfigUpdateRequest
) -> StrategyConfigItemResponse:
        """
        更新预警策略（立即生效）

        更新预警策略配置，更新后立即生效
        
        - scope=global: 更新全局策略
        - scope=bolt/flange/production_line + node_type + node_id: 创建/更新节点级覆盖
        - 节点级覆盖优先于全局策略
        - 每次更新自动生成新版本，旧版本保留可回滚
        - 所有变更记录审计日志
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/strategy/config",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_strategy_configs_api_v1_strategy_config_list_get(
        self,
        scope: Optional[Any] = None,
        node_type: Optional[Any] = None,
        node_id: Optional[Any] = None,
        is_active: Optional[Any] = None,
        limit: Optional[int] = None
) -> StrategyConfigListResponse:
        """
        列出策略配置（含历史版本）
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/strategy/config/list",
            params={
                "scope": scope,
                "node_type": node_type,
                "node_id": node_id,
                "is_active": is_active,
                "limit": limit,
            },
        )

        return response

    async def rollback_strategy_config_api_v1_strategy_config_rollback_post(
        self,
        body: StrategyRollbackRequest
) -> StrategyConfigItemResponse:
        """
        回滚策略到历史版本

        回滚策略配置到指定版本
        
        - 回滚基于历史版本创建新版本（版本号自增）
        - 操作记录审计日志
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/strategy/config/rollback",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_strategy_audit_logs_api_v1_strategy_config_audit_get(
        self,
        scope: Optional[Any] = None,
        node_type: Optional[Any] = None,
        node_id: Optional[Any] = None,
        action: Optional[Any] = None,
        operator_id: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> StrategyAuditLogListResponse:
        """
        查询策略变更审计日志
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/strategy/config/audit",
            params={
                "scope": scope,
                "node_type": node_type,
                "node_id": node_id,
                "action": action,
                "operator_id": operator_id,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def delete_strategy_override_api_v1_strategy_config_override_delete(
        self,
        body: StrategyNodeOverrideDeleteRequest
) -> Dict[str, Any]:
        """
        删除节点级策略覆盖

        删除节点级策略覆盖，该节点回退到全局策略
        
        - 仅删除节点级覆盖，不影响全局策略
        - 操作记录审计日志
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/strategy/config/override",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response
