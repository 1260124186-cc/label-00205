/** ComplianceAudit API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class ComplianceAuditClient extends BaseAPIClient {

  /**
   * 查询审计记录列表
   */
  async listAuditRecordsApiV1AuditRecordsGet(
    nodeType?: any,
    nodeId?: any,
    modelVersion?: any,
    startTime?: any,
    endTime?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.AuditListResponse> {
    const params: Record<string, any> = {};
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (modelVersion !== undefined) params['model_version'] = modelVersion;
    if (startTime !== undefined) params['start_time'] = startTime;
    if (endTime !== undefined) params['end_time'] = endTime;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/audit/records`,
      params,
      undefined
    );
  }

  /**
   * 获取审计记录详情
   */
  async getAuditRecordApiV1AuditRecordsAuditIdGet(
    auditId: number
  ): Promise<Models.AuditRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/audit/records/${auditId}`,
      params,
      undefined
    );
  }

  /**
   * 更新审计记录保留年限
   */
  async updateAuditRetentionApiV1AuditRecordsAuditIdRetentionPut(
    auditId: number,
    body: Models.AuditRetentionUpdateRequest
  ): Promise<Models.AuditRecordResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/audit/records/${auditId}/retention`,
      params,
      body
    );
  }

  /**
   * 清理过期审计记录
   */
  async cleanupExpiredAuditsApiV1AuditCleanupPost(
  ): Promise<Models.AuditCleanupResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/audit/cleanup`,
      params,
      undefined
    );
  }

  /**
   * 导出审计包
   */
  async exportAuditPackageApiV1AuditExportPost(
    body: Models.AuditExportRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/audit/export`,
      params,
      body
    );
  }

  /**
   * 获取可解释性报告
   */
  async getExplainabilityReportApiV1AuditRecordsAuditIdExplainabilityGet(
    auditId: number
  ): Promise<Models.ExplainabilityReportResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/audit/records/${auditId}/explainability`,
      params,
      undefined
    );
  }
}