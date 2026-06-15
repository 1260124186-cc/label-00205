/** System API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class SystemClient extends BaseAPIClient {

  /**
   * 健康检查（公开免鉴权）
   */
  async healthCheckHealthGet(
  ): Promise<Models.HealthResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/health`,
      params,
      undefined
    );
  }
}