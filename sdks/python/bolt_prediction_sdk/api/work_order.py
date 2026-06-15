"""
WorkOrder API 客户端
"""

from typing import Optional, Dict, Any, List, AsyncIterator
import json

from ..core.client import BaseAPIClient
from ..core.pagination import CursorPaginator
from ..models import *


class WorkOrderClient(BaseAPIClient):
    """WorkOrder API 客户端"""

    async def list_work_orders_api_v1_work_orders_get(
        self,
        status: Optional[Any] = None,
        priority: Optional[Any] = None,
        assignee_id: Optional[Any] = None,
        alert_id: Optional[Any] = None,
        node_type: Optional[Any] = None,
        node_id: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> WorkOrderListResponse:
        """
        查询工单列表

        查询工单列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders",
            params={
                "status": status,
                "priority": priority,
                "assignee_id": assignee_id,
                "alert_id": alert_id,
                "node_type": node_type,
                "node_id": node_id,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def create_work_order_api_v1_work_orders_post(
        self,
        body: WorkOrderCreate
) -> WorkOrderResponse:
        """
        手动创建工单

        手动创建工单
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_work_order_api_v1_work_orders_work_order_id_get(
        self,
        work_order_id: int
) -> WorkOrderResponse:
        """
        获取工单详情

        获取工单详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}",
        )

        return response

    async def update_work_order_api_v1_work_orders_work_order_id_put(
        self,
        work_order_id: int,
        body: WorkOrderUpdate
) -> WorkOrderResponse:
        """
        更新工单信息

        更新工单信息
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def assign_work_order_api_v1_work_orders_work_order_id_assign_post(
        self,
        work_order_id: int,
        body: WorkOrderAssignRequest
) -> WorkOrderResponse:
        """
        指派工单

        指派工单处理人
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}/assign",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def update_work_order_status_api_v1_work_orders_work_order_id_status_post(
        self,
        work_order_id: int,
        body: WorkOrderStatusUpdateRequest
) -> WorkOrderResponse:
        """
        更新工单状态

        更新工单状态
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}/status",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def resolve_work_order_api_v1_work_orders_work_order_id_resolve_post(
        self,
        work_order_id: int,
        body: WorkOrderResolveRequest
) -> WorkOrderResponse:
        """
        解决工单

        解决工单（便捷接口）
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}/resolve",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def list_work_order_disposals_api_v1_work_orders_work_order_id_disposals_get(
        self,
        work_order_id: int,
        disposal_type: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> DisposalRecordListResponse:
        """
        查询工单处置记录列表

        查询工单处置记录列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}/disposals",
            params={
                "disposal_type": disposal_type,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def create_disposal_record_api_v1_work_orders_disposals_post(
        self,
        body: DisposalRecordCreate
) -> DisposalRecordResponse:
        """
        创建处置记录

        创建工单处置记录
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders/disposals",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_disposal_record_api_v1_work_orders_disposals_record_id_get(
        self,
        record_id: int
) -> DisposalRecordResponse:
        """
        获取处置记录详情

        获取处置记录详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/disposals/{record_id}",
        )

        return response

    async def update_disposal_record_api_v1_work_orders_disposals_record_id_put(
        self,
        record_id: int,
        body: DisposalRecordUpdate
) -> DisposalRecordResponse:
        """
        更新处置记录

        更新处置记录
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/work-orders/disposals/{record_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def delete_disposal_record_api_v1_work_orders_disposals_record_id_delete(
        self,
        record_id: int
) -> Dict[str, Any]:
        """
        删除处置记录

        删除处置记录
        """

        response = await self._request(
            method="DELETE",
            path=f"/api/v1/api/v1/work-orders/disposals/{record_id}",
        )

        return response

    async def list_work_order_retests_api_v1_work_orders_work_order_id_retests_get(
        self,
        work_order_id: int,
        retest_result: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> RetestRecordListResponse:
        """
        查询工单复测记录列表

        查询工单复测记录列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}/retests",
            params={
                "retest_result": retest_result,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def create_retest_record_api_v1_work_orders_retests_post(
        self,
        body: RetestRecordCreate
) -> RetestRecordResponse:
        """
        创建复测记录

        创建工单复测记录，支持自动再预测
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders/retests",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def get_retest_record_api_v1_work_orders_retests_record_id_get(
        self,
        record_id: int
) -> RetestRecordResponse:
        """
        获取复测记录详情

        获取复测记录详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/retests/{record_id}",
        )

        return response

    async def update_retest_record_api_v1_work_orders_retests_record_id_put(
        self,
        record_id: int,
        body: RetestRecordUpdate
) -> RetestRecordResponse:
        """
        更新复测记录

        更新复测记录
        """

        response = await self._request(
            method="PUT",
            path=f"/api/v1/api/v1/work-orders/retests/{record_id}",
            json=body.to_dict() if hasattr(body, 'to_dict') else body,
        )

        return response

    async def trigger_retest_repredict_api_v1_work_orders_retests_record_id_repredict_post(
        self,
        record_id: int
) -> PredictionCompareResponse:
        """
        触发复测后再预测

        手动触发复测后再预测及对比
        """

        response = await self._request(
            method="POST",
            path=f"/api/v1/api/v1/work-orders/retests/{record_id}/repredict",
        )

        return response

    async def list_work_order_prediction_compares_api_v1_work_orders_work_order_id_prediction_compares_get(
        self,
        work_order_id: int,
        is_false_positive: Optional[Any] = None,
        is_recurring: Optional[Any] = None,
        risk_change: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> PredictionCompareListResponse:
        """
        查询工单预测对比列表

        查询工单预测对比列表
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/{work_order_id}/prediction-compares",
            params={
                "is_false_positive": is_false_positive,
                "is_recurring": is_recurring,
                "risk_change": risk_change,
                "limit": limit,
                "offset": offset,
            },
        )

        return response

    async def get_prediction_compare_api_v1_work_orders_prediction_compares_compare_id_get(
        self,
        compare_id: int
) -> PredictionCompareResponse:
        """
        获取预测对比详情

        获取预测对比详情
        """

        response = await self._request(
            method="GET",
            path=f"/api/v1/api/v1/work-orders/prediction-compares/{compare_id}",
        )

        return response
