"""
AlertManagement API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class AlertManagementClient(BaseAPIClient):
    """AlertManagement API 客户端"""

    async def list_alert_rules_api_v1_alert_rules_get(
        self,
        enabled: Optional[Any] = None,
        alert_level: Optional[Any] = None
) -> List[AlertRuleResponse]:
        """
        查询告警规则列表

        查询告警规则列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/alert/rules",
            params={
                "enabled": enabled,
                "alert_level": alert_level,
            },
        )

        return response

    async def create_alert_rule_api_v1_alert_rules_post(
        self,
        body: AlertRuleCreate
) -> AlertRuleResponse:
        """
        创建告警规则

        创建告警规则
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/alert/rules",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def update_alert_rule_api_v1_alert_rules_rule_id_put(
        self,
        rule_id: int,
        body: AlertRuleUpdate
) -> AlertRuleResponse:
        """
        更新告警规则

        更新告警规则
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/alert/rules/{rule_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_alert_rule_api_v1_alert_rules_rule_id_delete(
        self,
        rule_id: int
) -> Dict[str, Any]:
        """
        删除告警规则

        删除告警规则
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/alert/rules/{rule_id}",
        )

        return response

    async def list_alert_events_api_v1_alert_events_get(
        self,
        status: Optional[Any] = None,
        alert_level: Optional[Any] = None,
        node_type: Optional[Any] = None,
        node_id: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> AlertListResponse:
        """
        查询告警事件列表

        查询告警事件列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/alert/events",
            params={
                "status": status,
                "alert_level": alert_level,
                "node_type": node_type,
                "node_id": node_id,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def get_alert_event_api_v1_alert_events_alert_id_get(
        self,
        alert_id: int
) -> AlertEventResponse:
        """
        获取告警详情

        获取单条告警详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/alert/events/{alert_id}",
        )

        return response

    async def handle_alert_event_api_v1_alert_events_alert_id_handle_post(
        self,
        alert_id: int,
        body: AlertHandleRequest
) -> AlertEventResponse:
        """
        处理告警

        处理告警
        
        action:
        - acknowledge: 确认（状态变为 processing）
        - resolve: 解决（状态变为 resolved）
        - ignore: 忽略（状态变为 ignored，可选静默期）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/alert/events/{alert_id}/handle",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def trigger_alert_upgrade_api_v1_alert_upgrade_trigger_post(
        self
) -> AlertUpgradeTriggerResponse:
        """
        手动触发告警升级检查

        手动触发告警升级检查
        
        扫描所有待处理告警，对超时未处理的告警执行自动升级。
        调度器默认每5分钟执行一次。
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/alert/upgrade/trigger",
        )

        return response
