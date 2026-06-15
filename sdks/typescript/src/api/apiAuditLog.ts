/** ApiAuditLog API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class ApiAuditLogClient extends BaseAPIClient {

  /**
   * 查询API审计日志
   */
  async queryAuditLogsApiV1AuthAuditLogsGet(
    keyId?: any,
    path?: any,
    method?: any,
    startTime?: any,
    endTime?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.ApiAuditLogListResponse> {
    const params: Record<string, any> = {};
    if (keyId !== undefined) params['key_id'] = keyId;
    if (path !== undefined) params['path'] = path;
    if (method !== undefined) params['method'] = method;
    if (startTime !== undefined) params['start_time'] = startTime;
    if (endTime !== undefined) params['end_time'] = endTime;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/auth/audit-logs`,
      params,
      undefined
    );
  }
}