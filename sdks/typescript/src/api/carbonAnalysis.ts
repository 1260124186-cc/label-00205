/** CarbonAnalysis API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class CarbonAnalysisClient extends BaseAPIClient {

  /**
   * 装置级月度碳排风险贡献排行
   */
  async getCarbonMonthlyRankingApiV1CarbonRankingMonthlyPost(
    body: Models.CarbonMonthlyRankingRequest
  ): Promise<Models.CarbonMonthlyRankingResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/carbon/ranking/monthly`,
      params,
      body
    );
  }

  /**
   * HI rollup 与碳排并列展示
   */
  async getHiCarbonDualViewApiV1CarbonHiDualViewPost(
    body: Models.HiCarbonDualViewRequest
  ): Promise<Models.HiCarbonDualViewResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/carbon/hi-dual-view`,
      params,
      body
    );
  }

  /**
   * 导出 ESG 报表片段
   */
  async exportEsgReportFragmentApiV1CarbonEsgExportPost(
    body: Models.EsgReportExportRequest
  ): Promise<Models.EsgReportFragmentResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/carbon/esg/export`,
      params,
      body
    );
  }

  /**
   * 获取碳排模型系数配置
   */
  async getCarbonModelConfigApiV1CarbonConfigGet(
  ): Promise<Models.CarbonModelConfigResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/carbon/config`,
      params,
      undefined
    );
  }

  /**
   * 更新碳排模型系数配置
   */
  async updateCarbonModelConfigApiV1CarbonConfigPost(
    body: Models.CarbonModelConfigUpdateRequest
  ): Promise<Models.CarbonModelConfigResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/carbon/config`,
      params,
      body
    );
  }
}