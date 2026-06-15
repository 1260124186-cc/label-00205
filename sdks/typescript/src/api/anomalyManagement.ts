/** AnomalyManagement API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class AnomalyManagementClient extends BaseAPIClient {

  /**
   * 查询异常数据
   */
  async queryAnomaliesApiV1AnomalyQueryPost(
    body: Models.AnomalyQueryRequest
  ): Promise<Models.AnomalyListResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/anomaly/query`,
      params,
      body
    );
  }

  /**
   * 获取异常详情
   */
  async getAnomalyDetailApiV1AnomalyAnomalyIdGet(
    anomalyId: number
  ): Promise<Models.AnomalyDataResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/anomaly/${anomalyId}`,
      params,
      undefined
    );
  }

  /**
   * 确认异常（真实异常）
   */
  async confirmAnomalyApiV1AnomalyConfirmPost(
    body: Models.AnomalyConfirmRequest
  ): Promise<Models.AnomalyDataResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/anomaly/confirm`,
      params,
      body
    );
  }

  /**
   * 标注异常为误报
   */
  async markAnomalyFalsePositiveApiV1AnomalyFalsePositivePost(
    body: Models.AnomalyFalsePositiveRequest
  ): Promise<Models.AnomalyDataResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/anomaly/false-positive`,
      params,
      body
    );
  }

  /**
   * 批量确认异常
   */
  async batchConfirmAnomaliesApiV1AnomalyBatchConfirmPost(
    body: Models.AnomalyBatchConfirmRequest
  ): Promise<Models.AnomalyBatchResultResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/anomaly/batch-confirm`,
      params,
      body
    );
  }

  /**
   * 批量标注误报
   */
  async batchMarkFalsePositivesApiV1AnomalyBatchFalsePositivePost(
    body: Models.AnomalyBatchFalsePositiveRequest
  ): Promise<Models.AnomalyBatchResultResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/anomaly/batch-false-positive`,
      params,
      body
    );
  }

  /**
   * 获取异常统计信息
   */
  async getAnomalyStatisticsApiV1AnomalyStatisticsSummaryGet(
    sensorId?: any,
    startTime?: any,
    endTime?: any
  ): Promise<Models.AnomalyStatisticsResponse> {
    const params: Record<string, any> = {};
    if (sensorId !== undefined) params['sensor_id'] = sensorId;
    if (startTime !== undefined) params['start_time'] = startTime;
    if (endTime !== undefined) params['end_time'] = endTime;

    return this._request(
      "GET",
      `/api/v1/api/v1/anomaly/statistics/summary`,
      params,
      undefined
    );
  }

  /**
   * 检查异常对预警等级的影响
   */
  async checkAnomalyWarningImpactApiV1AnomalyWarningImpactSensorIdGet(
    sensorId: string,
    currentLevel?: number
  ): Promise<Models.AnomalyWarningImpactResponse> {
    const params: Record<string, any> = {};
    if (currentLevel !== undefined) params['current_level'] = currentLevel;

    return this._request(
      "GET",
      `/api/v1/api/v1/anomaly/warning-impact/${sensorId}`,
      params,
      undefined
    );
  }
}