/** HealthScore API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class HealthScoreClient extends BaseAPIClient {

  /**
   * 计算螺栓健康度指数 HI
   */
  async calculateHealthIndexApiV1HealthCalculatePost(
    body: Models.HealthIndexCalculateRequest
  ): Promise<Models.HealthIndexResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/health/calculate`,
      params,
      body
    );
  }

  /**
   * 批量计算螺栓健康度
   */
  async calculateHealthIndexBatchApiV1HealthCalculateBatchPost(
    body: Models.HealthIndexBatchCalculateRequest
  ): Promise<Models.HealthIndexBatchResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/health/calculate/batch`,
      params,
      body
    );
  }

  /**
   * 查询健康度历史记录
   */
  async getHealthHistoryApiV1HealthHistoryGet(
    nodeId: string,
    nodeType?: string,
    startTime?: any,
    endTime?: any,
    limit?: number
  ): Promise<Models.HealthIndexHistoryResponse> {
    const params: Record<string, any> = {};
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (startTime !== undefined) params['start_time'] = startTime;
    if (endTime !== undefined) params['end_time'] = endTime;
    if (limit !== undefined) params['limit'] = limit;

    return this._request(
      "GET",
      `/api/v1/api/v1/health/history`,
      params,
      undefined
    );
  }

  /**
   * 预测剩余使用寿命 RUL
   */
  async predictRulApiV1HealthRulPredictPost(
    body: Models.RulPredictionRequest
  ): Promise<Models.RulPredictionResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/health/rul/predict`,
      params,
      body
    );
  }

  /**
   * 生成产线/装置级健康度汇总报表
   */
  async generateHealthRollupApiV1HealthRollupPost(
    body: Models.HealthRollupRequest
  ): Promise<Models.HealthRollupResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/health/rollup`,
      params,
      body
    );
  }
}