/** TenantApiKey API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class TenantApiKeyClient extends BaseAPIClient {

  /**
   * 创建租户API Key
   */
  async createTenantApiKeyApiV1TenantsTenantIdApiKeysPost(
    tenantId: number,
    body: Models.TenantApiKeyCreateRequest
  ): Promise<Models.TenantApiKeyCreateResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/tenants/${tenantId}/api-keys`,
      params,
      body
    );
  }

  /**
   * 查询租户API Key列表
   */
  async listTenantApiKeysApiV1TenantsTenantIdApiKeysGet(
    tenantId: number,
    status?: any
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (status !== undefined) params['status'] = status;

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/api-keys`,
      params,
      undefined
    );
  }

  /**
   * 获取API Key详情
   */
  async getTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdGet(
    tenantId: number,
    keyId: number
  ): Promise<Models.TenantApiKeyResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/api-keys/${keyId}`,
      params,
      undefined
    );
  }

  /**
   * 更新API Key
   */
  async updateTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdPut(
    tenantId: number,
    keyId: number,
    body: Models.TenantApiKeyUpdateRequest
  ): Promise<Models.TenantApiKeyResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/tenants/${tenantId}/api-keys/${keyId}`,
      params,
      body
    );
  }

  /**
   * 吊销API Key
   */
  async revokeTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdDelete(
    tenantId: number,
    keyId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/tenants/${tenantId}/api-keys/${keyId}`,
      params,
      undefined
    );
  }
}