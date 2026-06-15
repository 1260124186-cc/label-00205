/** QuotaManagement API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class QuotaManagementClient extends BaseAPIClient {

  /**
   * 获取租户配额
   */
  async getTenantQuotaApiV1TenantsTenantIdQuotaGet(
    tenantId: number
  ): Promise<Models.QuotaResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/quota`,
      params,
      undefined
    );
  }

  /**
   * 更新租户配额
   */
  async updateTenantQuotaApiV1TenantsTenantIdQuotaPut(
    tenantId: number,
    body: Models.QuotaUpdateRequest
  ): Promise<Models.QuotaResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/tenants/${tenantId}/quota`,
      params,
      body
    );
  }
}