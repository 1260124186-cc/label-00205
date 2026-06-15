/** Prediction API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class PredictionClient extends BaseAPIClient {

  /**
   * 螺栓状态预测
   */
  async predictBoltApiV1PredictBoltPost(
    body: Models.BoltPredictionRequest,
    validationMode?: string,
    version?: any,
    shadowVersion?: any
  ): Promise<Models.BoltPredictionResponse> {
    const params: Record<string, any> = {};
    if (validationMode !== undefined) params['validation_mode'] = validationMode;
    if (version !== undefined) params['version'] = version;
    if (shadowVersion !== undefined) params['shadow_version'] = shadowVersion;

    return this._request(
      "POST",
      `/api/v1/api/v1/predict/bolt`,
      params,
      body
    );
  }

  /**
   * 螺栓集成学习预测调试
   */
  async predictBoltEnsembleApiV1PredictBoltEnsemblePost(
    body: Models.BoltEnsemblePredictionRequest,
    validationMode?: string
  ): Promise<Models.BoltEnsemblePredictionResponse> {
    const params: Record<string, any> = {};
    if (validationMode !== undefined) params['validation_mode'] = validationMode;

    return this._request(
      "POST",
      `/api/v1/api/v1/predict/bolt/ensemble`,
      params,
      body
    );
  }

  /**
   * 螺栓多变量耦合预测（温度/振动/扭矩等联合输入）
   */
  async predictBoltMultivariateApiV1PredictBoltMultivariatePost(
    body: Models.BoltMultivariatePredictionRequest,
    saveToDb?: boolean
  ): Promise<Models.BoltMultivariatePredictionResponse> {
    const params: Record<string, any> = {};
    if (saveToDb !== undefined) params['save_to_db'] = saveToDb;

    return this._request(
      "POST",
      `/api/v1/api/v1/predict/bolt/multivariate`,
      params,
      body
    );
  }

  /**
   * 法兰面状态预测
   */
  async predictFlangeApiV1PredictFlangePost(
    body: Models.FlangePredictionRequest,
    validationMode?: string,
    version?: any,
    shadowVersion?: any
  ): Promise<Models.FlangePredictionResponse> {
    const params: Record<string, any> = {};
    if (validationMode !== undefined) params['validation_mode'] = validationMode;
    if (version !== undefined) params['version'] = version;
    if (shadowVersion !== undefined) params['shadow_version'] = shadowVersion;

    return this._request(
      "POST",
      `/api/v1/api/v1/predict/flange`,
      params,
      body
    );
  }

  /**
   * 月度趋势预测
   */
  async forecastMonthlyApiV1ForecastMonthlyPost(
    body: Models.MonthlyForecastRequest
  ): Promise<Models.MonthlyForecastResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/forecast/monthly`,
      params,
      body
    );
  }

  /**
   * 批量预测
   */
  async batchPredictApiV1PredictBatchPost(
    nodeType: string
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (nodeType !== undefined) params['node_type'] = nodeType;

    return this._request(
      "POST",
      `/api/v1/api/v1/predict/batch`,
      params,
      undefined
    );
  }
}