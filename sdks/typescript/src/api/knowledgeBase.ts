/** KnowledgeBase API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class KnowledgeBaseClient extends BaseAPIClient {

  /**
   * 创建案例
   */
  async createKnowledgeCaseApiV1KnowledgeCasesPost(
    body: Models.KnowledgeCaseCreateRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/knowledge/cases`,
      params,
      body
    );
  }

  /**
   * 查询案例列表
   */
  async listKnowledgeCasesApiV1KnowledgeCasesGet(
    status?: any,
    nodeType?: any,
    faultType?: any,
    faultLevel?: any,
    tenantId?: any,
    keyword?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.KnowledgeCaseListResponse> {
    const params: Record<string, any> = {};
    if (status !== undefined) params['status'] = status;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (faultType !== undefined) params['fault_type'] = faultType;
    if (faultLevel !== undefined) params['fault_level'] = faultLevel;
    if (tenantId !== undefined) params['tenant_id'] = tenantId;
    if (keyword !== undefined) params['keyword'] = keyword;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/cases`,
      params,
      undefined
    );
  }

  /**
   * 获取案例详情
   */
  async getKnowledgeCaseApiV1KnowledgeCasesCaseIdGet(
    caseId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/cases/${caseId}`,
      params,
      undefined
    );
  }

  /**
   * 更新案例
   */
  async updateKnowledgeCaseApiV1KnowledgeCasesCaseIdPut(
    caseId: number,
    body: Models.KnowledgeCaseUpdateRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/knowledge/cases/${caseId}`,
      params,
      body
    );
  }

  /**
   * 删除案例
   */
  async deleteKnowledgeCaseApiV1KnowledgeCasesCaseIdDelete(
    caseId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/knowledge/cases/${caseId}`,
      params,
      undefined
    );
  }

  /**
   * 提交审核
   */
  async submitCaseForReviewApiV1KnowledgeCasesCaseIdSubmitReviewPost(
    caseId: number,
    operatorId?: any,
    operatorName?: any
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (operatorId !== undefined) params['operator_id'] = operatorId;
    if (operatorName !== undefined) params['operator_name'] = operatorName;

    return this._request(
      "POST",
      `/api/v1/api/v1/knowledge/cases/${caseId}/submit-review`,
      params,
      undefined
    );
  }

  /**
   * 审核案例
   */
  async reviewKnowledgeCaseApiV1KnowledgeCasesCaseIdReviewPost(
    caseId: number,
    body: Models.CaseReviewRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/knowledge/cases/${caseId}/review`,
      params,
      body
    );
  }

  /**
   * 获取审核记录
   */
  async listCaseReviewsApiV1KnowledgeCasesCaseIdReviewsGet(
    caseId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/cases/${caseId}/reviews`,
      params,
      undefined
    );
  }

  /**
   * 获取版本历史
   */
  async listCaseVersionsApiV1KnowledgeCasesCaseIdVersionsGet(
    caseId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/cases/${caseId}/versions`,
      params,
      undefined
    );
  }

  /**
   * 获取指定版本
   */
  async getCaseVersionApiV1KnowledgeCasesCaseIdVersionsVersionGet(
    caseId: number,
    version: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/cases/${caseId}/versions/${version}`,
      params,
      undefined
    );
  }

  /**
   * 对比版本差异
   */
  async compareCaseVersionsApiV1KnowledgeCasesCaseIdVersionsCompareGet(
    caseId: number,
    versionFrom: number,
    versionTo: number
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (versionFrom !== undefined) params['version_from'] = versionFrom;
    if (versionTo !== undefined) params['version_to'] = versionTo;

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/cases/${caseId}/versions/compare`,
      params,
      undefined
    );
  }

  /**
   * 回退到指定版本
   */
  async revertCaseToVersionApiV1KnowledgeCasesCaseIdVersionsVersionRevertPost(
    caseId: number,
    version: number,
    operatorId?: any,
    operatorName?: any
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (operatorId !== undefined) params['operator_id'] = operatorId;
    if (operatorName !== undefined) params['operator_name'] = operatorName;

    return this._request(
      "POST",
      `/api/v1/api/v1/knowledge/cases/${caseId}/versions/${version}/revert`,
      params,
      undefined
    );
  }

  /**
   * 检索相似案例 (Top-K)
   */
  async searchSimilarCasesApiV1KnowledgeCasesSearchSimilarPost(
    body: Models.CaseSimilaritySearchRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/knowledge/cases/search/similar`,
      params,
      body
    );
  }

  /**
   * 获取案例推荐 (推荐措施 + RAG上下文)
   */
  async getCaseRecommendationsApiV1KnowledgeCasesRecommendPost(
    body: Models.CaseSimilaritySearchRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/knowledge/cases/recommend`,
      params,
      body
    );
  }

  /**
   * 获取知识库统计
   */
  async getKnowledgeStatisticsApiV1KnowledgeStatisticsGet(
    tenantId?: any
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (tenantId !== undefined) params['tenant_id'] = tenantId;

    return this._request(
      "GET",
      `/api/v1/api/v1/knowledge/statistics`,
      params,
      undefined
    );
  }
}