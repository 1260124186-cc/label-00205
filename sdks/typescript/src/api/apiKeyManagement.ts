/** ApiKeyManagement API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class ApiKeyManagementClient extends BaseAPIClient {

  /**
   * 列出所有API密钥
   */
  async listApiKeysApiV1AuthKeysGet(
  ): Promise<Models.ApiKeyListResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/auth/keys`,
      params,
      undefined
    );
  }

  /**
   * 创建API密钥
   */
  async createApiKeyApiV1AuthKeysPost(
    body: Models.ApiKeyCreateRequest
  ): Promise<Models.ApiKeyCreateResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/auth/keys`,
      params,
      body
    );
  }

  /**
   * 轮换API密钥
   */
  async rotateApiKeyApiV1AuthKeysKeyIdRotatePost(
    keyId: string
  ): Promise<Models.ApiKeyRotateResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/auth/keys/${keyId}/rotate`,
      params,
      undefined
    );
  }

  /**
   * 吊销API密钥
   */
  async revokeApiKeyApiV1AuthKeysKeyIdDelete(
    keyId: string
  ): Promise<Models.ApiKeyRevokeResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/auth/keys/${keyId}`,
      params,
      undefined
    );
  }

  /**
   * 查询密钥限流状态
   */
  async getRateLimitStatusApiV1AuthKeysKeyIdRateLimitGet(
    keyId: string
  ): Promise<Models.RateLimitStatusResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/auth/keys/${keyId}/rate-limit`,
      params,
      undefined
    );
  }
}