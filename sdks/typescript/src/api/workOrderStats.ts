/** WorkOrderStats API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class WorkOrderStatsClient extends BaseAPIClient {

  /**
   * 工单统计指标概览
   */
  async getWorkOrderStatsApiV1WorkOrdersStatsSummaryGet(
    startTime?: any,
    endTime?: any,
    nodeType?: any,
    priority?: any
  ): Promise<Models.WorkOrderStatsResponse> {
    const params: Record<string, any> = {};
    if (startTime !== undefined) params['start_time'] = startTime;
    if (endTime !== undefined) params['end_time'] = endTime;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (priority !== undefined) params['priority'] = priority;

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/stats/summary`,
      params,
      undefined
    );
  }

  /**
   * MTTR趋势
   */
  async getMttrTrendApiV1WorkOrdersStatsMttrTrendGet(
    days?: number,
    nodeType?: any,
    priority?: any
  ): Promise<Models.MttrTrendResponse> {
    const params: Record<string, any> = {};
    if (days !== undefined) params['days'] = days;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (priority !== undefined) params['priority'] = priority;

    return this._request(
      "GET",
      `/api/v1/api/v1/work-orders/stats/mttr-trend`,
      params,
      undefined
    );
  }
}