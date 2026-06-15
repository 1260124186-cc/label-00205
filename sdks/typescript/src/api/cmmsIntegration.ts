/** CMMSIntegration API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class CmmsIntegrationClient extends BaseAPIClient {

  /**
   * 查询CMMS配置列表
   */
  async listCmmsConfigsApiV1CmmsConfigsGet(
    enabled?: any,
    systemType?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.CmmsConfigListResponse> {
    const params: Record<string, any> = {};
    if (enabled !== undefined) params['enabled'] = enabled;
    if (systemType !== undefined) params['system_type'] = systemType;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/cmms/configs`,
      params,
      undefined
    );
  }

  /**
   * 创建CMMS配置
   */
  async createCmmsConfigApiV1CmmsConfigsPost(
    body: Models.CmmsConfigCreate
  ): Promise<Models.CmmsConfigResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/cmms/configs`,
      params,
      body
    );
  }

  /**
   * 获取CMMS配置详情
   */
  async getCmmsConfigApiV1CmmsConfigsConfigIdGet(
    configId: number
  ): Promise<Models.CmmsConfigResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/cmms/configs/${configId}`,
      params,
      undefined
    );
  }

  /**
   * 更新CMMS配置
   */
  async updateCmmsConfigApiV1CmmsConfigsConfigIdPut(
    configId: number,
    body: Models.CmmsConfigUpdate
  ): Promise<Models.CmmsConfigResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/cmms/configs/${configId}`,
      params,
      body
    );
  }

  /**
   * 删除CMMS配置
   */
  async deleteCmmsConfigApiV1CmmsConfigsConfigIdDelete(
    configId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/cmms/configs/${configId}`,
      params,
      undefined
    );
  }

  /**
   * 同步工单到CMMS
   */
  async syncWorkOrderToCmmsApiV1CmmsSyncWorkOrderPost(
    body: Models.CmmsSyncRequest
  ): Promise<Models.CmmsSyncResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/cmms/sync/work-order`,
      params,
      body
    );
  }

  /**
   * CMMS Webhook回调
   */
  async cmmsWebhookCallbackApiV1CmmsWebhookConfigIdPost(
    configId: number,
    body: Record<string, any>,
    xSignature?: any
  ): Promise<Models.CmmsWebhookResponse> {
    const params: Record<string, any> = {};
    if (xSignature !== undefined) params['X-Signature'] = xSignature;

    return this._request(
      "POST",
      `/api/v1/api/v1/cmms/webhook/${configId}`,
      params,
      body
    );
  }

  /**
   * 查询CMMS同步日志
   */
  async listCmmsSyncLogsApiV1CmmsSyncLogsGet(
    configId?: any,
    workOrderId?: any,
    status?: any,
    syncDirection?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.CmmsSyncLogListResponse> {
    const params: Record<string, any> = {};
    if (configId !== undefined) params['config_id'] = configId;
    if (workOrderId !== undefined) params['work_order_id'] = workOrderId;
    if (status !== undefined) params['status'] = status;
    if (syncDirection !== undefined) params['sync_direction'] = syncDirection;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/cmms/sync-logs`,
      params,
      undefined
    );
  }

  /**
   * 重试CMMS同步
   */
  async retryCmmsSyncApiV1CmmsSyncLogsLogIdRetryPost(
    logId: number
  ): Promise<Models.CmmsSyncResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/cmms/sync-logs/${logId}/retry`,
      params,
      undefined
    );
  }
}