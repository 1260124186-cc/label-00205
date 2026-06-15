/** RiskAssessment API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class RiskAssessmentClient extends BaseAPIClient {

  /**
   * 风险评估
   */
  async assessRiskApiV1RiskAssessPost(
    body: Models.RiskAssessmentRequest,
    validationMode?: string
  ): Promise<Models.RiskAssessmentResponse> {
    const params: Record<string, any> = {};
    if (validationMode !== undefined) params['validation_mode'] = validationMode;

    return this._request(
      "POST",
      `/api/v1/api/v1/risk/assess`,
      params,
      body
    );
  }

  /**
   * 风险评估可解释性分析
   */
  async assessRiskExplainApiV1RiskAssessExplainPost(
    body: Models.RiskAssessExplainRequest,
    validationMode?: string
  ): Promise<Models.RiskAssessExplainResponse> {
    const params: Record<string, any> = {};
    if (validationMode !== undefined) params['validation_mode'] = validationMode;

    return this._request(
      "POST",
      `/api/v1/api/v1/risk/assess/explain`,
      params,
      body
    );
  }

  /**
   * 更新节点级风险校准配置
   */
  async updateRiskCalibrationApiV1RiskCalibrationPost(
    body: Models.RiskCalibrationUpdateRequest
  ): Promise<Models.RiskCalibrationResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/risk/calibration`,
      params,
      body
    );
  }

  /**
   * 查询节点级风险校准配置
   */
  async getRiskCalibrationApiV1RiskCalibrationGet(
    nodeType: string,
    nodeId: string
  ): Promise<Models.RiskCalibrationResponse> {
    const params: Record<string, any> = {};
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;

    return this._request(
      "GET",
      `/api/v1/api/v1/risk/calibration`,
      params,
      undefined
    );
  }
}