/** TenantUser API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class TenantUserClient extends BaseAPIClient {

  /**
   * 创建租户用户
   */
  async createTenantUserApiV1TenantsTenantIdUsersPost(
    tenantId: number,
    body: Models.TenantUserCreateRequest
  ): Promise<Models.TenantUserResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/tenants/${tenantId}/users`,
      params,
      body
    );
  }

  /**
   * 查询租户用户列表
   */
  async listTenantUsersApiV1TenantsTenantIdUsersGet(
    tenantId: number,
    role?: any,
    status?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.TenantUserListResponse> {
    const params: Record<string, any> = {};
    if (role !== undefined) params['role'] = role;
    if (status !== undefined) params['status'] = status;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/users`,
      params,
      undefined
    );
  }

  /**
   * 获取租户用户详情
   */
  async getTenantUserApiV1TenantsTenantIdUsersUserIdGet(
    tenantId: number,
    userId: number
  ): Promise<Models.TenantUserResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/users/${userId}`,
      params,
      undefined
    );
  }

  /**
   * 更新租户用户
   */
  async updateTenantUserApiV1TenantsTenantIdUsersUserIdPut(
    tenantId: number,
    userId: number,
    body: Models.TenantUserUpdateRequest
  ): Promise<Models.TenantUserResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/tenants/${tenantId}/users/${userId}`,
      params,
      body
    );
  }

  /**
   * 禁用租户用户
   */
  async deleteTenantUserApiV1TenantsTenantIdUsersUserIdDelete(
    tenantId: number,
    userId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/tenants/${tenantId}/users/${userId}`,
      params,
      undefined
    );
  }

  /**
   * 修改租户用户密码
   */
  async changeTenantUserPasswordApiV1TenantsTenantIdUsersUserIdPasswordPut(
    tenantId: number,
    userId: number,
    body: Models.TenantUserPasswordRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/tenants/${tenantId}/users/${userId}/password`,
      params,
      body
    );
  }
}