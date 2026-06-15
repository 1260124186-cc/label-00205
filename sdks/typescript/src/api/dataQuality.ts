/** DataQuality API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class DataQualityClient extends BaseAPIClient {

  /**
   * 评估传感器数据质量
   */
  async checkDataQualityApiV1DataQualityCheckPost(
    body: Models.DataQualityCheckRequest
  ): Promise<Models.QualityEvaluationResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/data-quality/check`,
      params,
      body
    );
  }

  /**
   * 批量评估传感器数据质量
   */
  async batchCheckDataQualityApiV1DataQualityBatchCheckPost(
    body: Models.DataQualityCheckBatchRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/data-quality/batch-check`,
      params,
      body
    );
  }

  /**
   * 获取传感器质量评分
   */
  async getSensorQualityScoreApiV1DataQualityScoreSensorIdGet(
    sensorId: string,
    recentDataLimit?: number
  ): Promise<Models.SensorQualityScoreSchema> {
    const params: Record<string, any> = {};
    if (recentDataLimit !== undefined) params['recent_data_limit'] = recentDataLimit;

    return this._request(
      "GET",
      `/api/v1/api/v1/data-quality/score/${sensorId}`,
      params,
      undefined
    );
  }

  /**
   * 调整预测置信度
   */
  async adjustPredictionConfidenceApiV1DataQualityAdjustConfidencePost(
    body: Models.ConfidenceAdjustmentRequest
  ): Promise<Models.ConfidenceAdjustmentResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/data-quality/adjust-confidence`,
      params,
      body
    );
  }

  /**
   * 生成每日质量报告
   */
  async generateQualityReportApiV1DataQualityReportGeneratePost(
    body: Models.QualityReportRequest
  ): Promise<Models.DailyQualityReportSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/data-quality/report/generate`,
      params,
      body
    );
  }

  /**
   * 获取最新质量报告
   */
  async getLatestQualityReportApiV1DataQualityReportLatestGet(
  ): Promise<Models.DailyQualityReportSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/data-quality/report/latest`,
      params,
      undefined
    );
  }

  /**
   * 获取传感器质量历史记录
   */
  async getSensorQualityHistoryApiV1DataQualityHistorySensorIdGet(
    body: Models.DataQualityHistoryRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/data-quality/history/{sensor_id}`,
      params,
      body
    );
  }

  /**
   * 获取问题传感器列表
   */
  async getProblemSensorsApiV1DataQualityProblemSensorsGet(
    minScore?: number,
    limit?: number
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (minScore !== undefined) params['min_score'] = minScore;
    if (limit !== undefined) params['limit'] = limit;

    return this._request(
      "GET",
      `/api/v1/api/v1/data-quality/problem-sensors`,
      params,
      undefined
    );
  }

  /**
   * 分类传感器异常
   */
  async classifySensorAnomaliesApiV1DataQualityAnomaliesSensorIdClassifyGet(
    sensorId: string,
    startTime?: any,
    endTime?: any,
    recentDataLimit?: number
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (startTime !== undefined) params['start_time'] = startTime;
    if (endTime !== undefined) params['end_time'] = endTime;
    if (recentDataLimit !== undefined) params['recent_data_limit'] = recentDataLimit;

    return this._request(
      "GET",
      `/api/v1/api/v1/data-quality/anomalies/${sensorId}/classify`,
      params,
      undefined
    );
  }

  /**
   * 获取数据质量总览
   */
  async getDataQualitySummaryApiV1DataQualitySummaryGet(
    days?: number
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (days !== undefined) params['days'] = days;

    return this._request(
      "GET",
      `/api/v1/api/v1/data-quality/summary`,
      params,
      undefined
    );
  }
}