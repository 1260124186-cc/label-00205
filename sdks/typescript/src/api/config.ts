/** Config API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class ConfigClient extends BaseAPIClient {

  /**
   * 查询当前生效策略
   */
  async getStrategyConfigApiV1StrategyConfigGet(
    nodeType?: any,
    nodeId?: any
  ): Promise<Models.EffectiveStrategyResponse> {
    const params: Record<string, any> = {};
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;

    return this._request(
      "GET",
      `/api/v1/api/v1/strategy/config`,
      params,
      undefined
    );
  }

  /**
   * 更新预警策略（立即生效）
   */
  async updateStrategyConfigApiV1StrategyConfigPost(
    body: Models.StrategyConfigUpdateRequest
  ): Promise<Models.StrategyConfigItemResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/strategy/config`,
      params,
      body
    );
  }

  /**
   * 列出策略配置（含历史版本）
   */
  async listStrategyConfigsApiV1StrategyConfigListGet(
    scope?: any,
    nodeType?: any,
    nodeId?: any,
    isActive?: any,
    limit?: number
  ): Promise<Models.StrategyConfigListResponse> {
    const params: Record<string, any> = {};
    if (scope !== undefined) params['scope'] = scope;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (isActive !== undefined) params['is_active'] = isActive;
    if (limit !== undefined) params['limit'] = limit;

    return this._request(
      "GET",
      `/api/v1/api/v1/strategy/config/list`,
      params,
      undefined
    );
  }

  /**
   * 回滚策略到历史版本
   */
  async rollbackStrategyConfigApiV1StrategyConfigRollbackPost(
    body: Models.StrategyRollbackRequest
  ): Promise<Models.StrategyConfigItemResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/strategy/config/rollback`,
      params,
      body
    );
  }

  /**
   * 查询策略变更审计日志
   */
  async getStrategyAuditLogsApiV1StrategyConfigAuditGet(
    scope?: any,
    nodeType?: any,
    nodeId?: any,
    action?: any,
    operatorId?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.StrategyAuditLogListResponse> {
    const params: Record<string, any> = {};
    if (scope !== undefined) params['scope'] = scope;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (action !== undefined) params['action'] = action;
    if (operatorId !== undefined) params['operator_id'] = operatorId;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/strategy/config/audit`,
      params,
      undefined
    );
  }

  /**
   * 删除节点级策略覆盖
   */
  async deleteStrategyOverrideApiV1StrategyConfigOverrideDelete(
    body: Models.StrategyNodeOverrideDeleteRequest
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/strategy/config/override`,
      params,
      body
    );
  }
}