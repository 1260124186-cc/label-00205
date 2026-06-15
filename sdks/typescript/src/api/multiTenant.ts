/** MultiTenant API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class MultiTenantClient extends BaseAPIClient {

  /**
   * 租户用户登录
   */
  async tenantLoginApiV1TenantLoginPost(
    body: Models.TenantLoginRequest
  ): Promise<Models.TenantLoginResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/tenant/login`,
      params,
      body
    );
  }

  /**
   * 获取当前登录用户信息
   */
  async getCurrentTenantUserApiV1TenantMeGet(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenant/me`,
      params,
      undefined
    );
  }

  /**
   * 租户用户登出
   */
  async tenantLogoutApiV1TenantLogoutPost(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/tenant/logout`,
      params,
      undefined
    );
  }

  /**
   * 创建租户
   */
  async createTenantApiV1TenantsPost(
    body: Models.TenantCreateRequest
  ): Promise<Models.TenantResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/tenants`,
      params,
      body
    );
  }

  /**
   * 查询租户列表
   */
  async listTenantsApiV1TenantsGet(
    status?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.TenantListResponse> {
    const params: Record<string, any> = {};
    if (status !== undefined) params['status'] = status;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants`,
      params,
      undefined
    );
  }

  /**
   * 获取租户详情
   */
  async getTenantApiV1TenantsTenantIdGet(
    tenantId: number
  ): Promise<Models.TenantResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}`,
      params,
      undefined
    );
  }

  /**
   * 更新租户
   */
  async updateTenantApiV1TenantsTenantIdPut(
    tenantId: number,
    body: Models.TenantUpdateRequest
  ): Promise<Models.TenantResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/tenants/${tenantId}`,
      params,
      body
    );
  }

  /**
   * 删除租户
   */
  async deleteTenantApiV1TenantsTenantIdDelete(
    tenantId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/tenants/${tenantId}`,
      params,
      undefined
    );
  }
}