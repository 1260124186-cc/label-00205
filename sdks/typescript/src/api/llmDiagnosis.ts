/** LLMDiagnosis API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class LlmDiagnosisClient extends BaseAPIClient {

  /**
   * 生成单次诊断报告
   */
  async generateDiagnosisReportApiV1ReportDiagnosisPost(
    body: Models.DiagnosisReportRequest
  ): Promise<Models.DiagnosisReportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/report/diagnosis`,
      params,
      body
    );
  }

  /**
   * 生成周期报告（周报/月报）
   */
  async generatePeriodicReportApiV1ReportGeneratePost(
    body: Models.ReportGenerateRequest
  ): Promise<Models.PeriodicReportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/report/generate`,
      params,
      body
    );
  }

  /**
   * 批量生成周期报告
   */
  async batchGeneratePeriodicReportsApiV1ReportBatchGeneratePost(
    body: Models.BatchReportGenerateRequest
  ): Promise<Models.BatchReportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/report/batch-generate`,
      params,
      body
    );
  }

  /**
   * 获取 LLM 配置状态
   */
  async getLlmConfigStatusApiV1ReportConfigGet(
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/report/config`,
      params,
      undefined
    );
  }
}