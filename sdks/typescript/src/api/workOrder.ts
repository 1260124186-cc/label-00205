/** WorkOrder API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class WorkOrderClient extends BaseAPIClient {

  /**
   * 查询工单列表
   */
  async listWorkOrdersApiV1WorkOrdersGet(
    status?: any,
    priority?: any,
    assigneeId?: any,
    alertId?: any,
    nodeType?: any,
    nodeId?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.WorkOrderListResponse> {
    const params: Record<string, any> = {};
    if (status !== undefined) params['status'] = status;
    if (priority !== undefined) params['priority'] = priority;
    if (assigneeId !== undefined) params['assignee_id'] = assigneeId;
    if (alertId !== undefined) params['alert_id'] = alertId;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders`,
      params,
      undefined
    );
  }

  /**
   * 手动创建工单
   */
  async createWorkOrderApiV1WorkOrdersPost(
    body: Models.WorkOrderCreate
  ): Promise<Models.WorkOrderResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders`,
      params,
      body
    );
  }

  /**
   * 获取工单详情
   */
  async getWorkOrderApiV1WorkOrdersWorkOrderIdGet(
    workOrderId: number
  ): Promise<Models.WorkOrderResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/${workOrderId}`,
      params,
      undefined
    );
  }

  /**
   * 更新工单信息
   */
  async updateWorkOrderApiV1WorkOrdersWorkOrderIdPut(
    workOrderId: number,
    body: Models.WorkOrderUpdate
  ): Promise<Models.WorkOrderResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/work-orders/${workOrderId}`,
      params,
      body
    );
  }

  /**
   * 指派工单
   */
  async assignWorkOrderApiV1WorkOrdersWorkOrderIdAssignPost(
    workOrderId: number,
    body: Models.WorkOrderAssignRequest
  ): Promise<Models.WorkOrderResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders/${workOrderId}/assign`,
      params,
      body
    );
  }

  /**
   * 更新工单状态
   */
  async updateWorkOrderStatusApiV1WorkOrdersWorkOrderIdStatusPost(
    workOrderId: number,
    body: Models.WorkOrderStatusUpdateRequest
  ): Promise<Models.WorkOrderResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders/${workOrderId}/status`,
      params,
      body
    );
  }

  /**
   * 解决工单
   */
  async resolveWorkOrderApiV1WorkOrdersWorkOrderIdResolvePost(
    workOrderId: number,
    body: Models.WorkOrderResolveRequest
  ): Promise<Models.WorkOrderResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders/${workOrderId}/resolve`,
      params,
      body
    );
  }

  /**
   * 查询工单处置记录列表
   */
  async listWorkOrderDisposalsApiV1WorkOrdersWorkOrderIdDisposalsGet(
    workOrderId: number,
    disposalType?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.DisposalRecordListResponse> {
    const params: Record<string, any> = {};
    if (disposalType !== undefined) params['disposal_type'] = disposalType;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/${workOrderId}/disposals`,
      params,
      undefined
    );
  }

  /**
   * 创建处置记录
   */
  async createDisposalRecordApiV1WorkOrdersDisposalsPost(
    body: Models.DisposalRecordCreate
  ): Promise<Models.DisposalRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders/disposals`,
      params,
      body
    );
  }

  /**
   * 获取处置记录详情
   */
  async getDisposalRecordApiV1WorkOrdersDisposalsRecordIdGet(
    recordId: number
  ): Promise<Models.DisposalRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/disposals/${recordId}`,
      params,
      undefined
    );
  }

  /**
   * 更新处置记录
   */
  async updateDisposalRecordApiV1WorkOrdersDisposalsRecordIdPut(
    recordId: number,
    body: Models.DisposalRecordUpdate
  ): Promise<Models.DisposalRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/work-orders/disposals/${recordId}`,
      params,
      body
    );
  }

  /**
   * 删除处置记录
   */
  async deleteDisposalRecordApiV1WorkOrdersDisposalsRecordIdDelete(
    recordId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/work-orders/disposals/${recordId}`,
      params,
      undefined
    );
  }

  /**
   * 查询工单复测记录列表
   */
  async listWorkOrderRetestsApiV1WorkOrdersWorkOrderIdRetestsGet(
    workOrderId: number,
    retestResult?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.RetestRecordListResponse> {
    const params: Record<string, any> = {};
    if (retestResult !== undefined) params['retest_result'] = retestResult;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/${workOrderId}/retests`,
      params,
      undefined
    );
  }

  /**
   * 创建复测记录
   */
  async createRetestRecordApiV1WorkOrdersRetestsPost(
    body: Models.RetestRecordCreate
  ): Promise<Models.RetestRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders/retests`,
      params,
      body
    );
  }

  /**
   * 获取复测记录详情
   */
  async getRetestRecordApiV1WorkOrdersRetestsRecordIdGet(
    recordId: number
  ): Promise<Models.RetestRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/retests/${recordId}`,
      params,
      undefined
    );
  }

  /**
   * 更新复测记录
   */
  async updateRetestRecordApiV1WorkOrdersRetestsRecordIdPut(
    recordId: number,
    body: Models.RetestRecordUpdate
  ): Promise<Models.RetestRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/work-orders/retests/${recordId}`,
      params,
      body
    );
  }

  /**
   * 触发复测后再预测
   */
  async triggerRetestRepredictApiV1WorkOrdersRetestsRecordIdRepredictPost(
    recordId: number
  ): Promise<Models.PredictionCompareResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/work-orders/retests/${recordId}/repredict`,
      params,
      undefined
    );
  }

  /**
   * 查询工单预测对比列表
   */
  async listWorkOrderPredictionComparesApiV1WorkOrdersWorkOrderIdPredictionComparesGet(
    workOrderId: number,
    isFalsePositive?: any,
    isRecurring?: any,
    riskChange?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.PredictionCompareListResponse> {
    const params: Record<string, any> = {};
    if (isFalsePositive !== undefined) params['is_false_positive'] = isFalsePositive;
    if (isRecurring !== undefined) params['is_recurring'] = isRecurring;
    if (riskChange !== undefined) params['risk_change'] = riskChange;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/${workOrderId}/prediction-compares`,
      params,
      undefined
    );
  }

  /**
   * 获取预测对比详情
   */
  async getPredictionCompareApiV1WorkOrdersPredictionComparesCompareIdGet(
    compareId: number
  ): Promise<Models.PredictionCompareResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/prediction-compares/${compareId}`,
      params,
      undefined
    );
  }
}