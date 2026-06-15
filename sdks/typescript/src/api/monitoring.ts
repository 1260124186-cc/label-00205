/** Monitoring API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class MonitoringClient extends BaseAPIClient {

  /**
   * Get Metrics
   */
  async getMetricsMetricsGet(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/metrics`,
      params,
      undefined
    );
  }
}