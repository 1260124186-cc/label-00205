/** AlertManagement API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class AlertManagementClient extends BaseAPIClient {

  /**
   * 查询告警规则列表
   */
  async listAlertRulesApiV1AlertRulesGet(
    enabled?: any,
    alertLevel?: any
  ): Promise<Models.AlertRuleResponse[]> {
    const params: Record<string, any> = {};
    if (enabled !== undefined) params['enabled'] = enabled;
    if (alertLevel !== undefined) params['alert_level'] = alertLevel;

    return this._request(
      "GET",
      `/api/v1/api/v1/alert/rules`,
      params,
      undefined
    );
  }

  /**
   * 创建告警规则
   */
  async createAlertRuleApiV1AlertRulesPost(
    body: Models.AlertRuleCreate
  ): Promise<Models.AlertRuleResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/alert/rules`,
      params,
      body
    );
  }

  /**
   * 更新告警规则
   */
  async updateAlertRuleApiV1AlertRulesRuleIdPut(
    ruleId: number,
    body: Models.AlertRuleUpdate
  ): Promise<Models.AlertRuleResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/alert/rules/${ruleId}`,
      params,
      body
    );
  }

  /**
   * 删除告警规则
   */
  async deleteAlertRuleApiV1AlertRulesRuleIdDelete(
    ruleId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/alert/rules/${ruleId}`,
      params,
      undefined
    );
  }

  /**
   * 查询告警事件列表
   */
  async listAlertEventsApiV1AlertEventsGet(
    status?: any,
    alertLevel?: any,
    nodeType?: any,
    nodeId?: any,
    limit?: number,
    offset?: number
  ): Promise<Models.AlertListResponse> {
    const params: Record<string, any> = {};
    if (status !== undefined) params['status'] = status;
    if (alertLevel !== undefined) params['alert_level'] = alertLevel;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (nodeId !== undefined) params['node_id'] = nodeId;
    if (limit !== undefined) params['limit'] = limit;
    if (offset !== undefined) params['offset'] = offset;

    return this._request(
      "GET",
      `/api/v1/api/v1/alert/events`,
      params,
      undefined
    );
  }

  /**
   * 获取告警详情
   */
  async getAlertEventApiV1AlertEventsAlertIdGet(
    alertId: number
  ): Promise<Models.AlertEventResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/alert/events/${alertId}`,
      params,
      undefined
    );
  }

  /**
   * 处理告警
   */
  async handleAlertEventApiV1AlertEventsAlertIdHandlePost(
    alertId: number,
    body: Models.AlertHandleRequest
  ): Promise<Models.AlertEventResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/alert/events/${alertId}/handle`,
      params,
      body
    );
  }

  /**
   * 手动触发告警升级检查
   */
  async triggerAlertUpgradeApiV1AlertUpgradeTriggerPost(
  ): Promise<Models.AlertUpgradeTriggerResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/alert/upgrade/trigger`,
      params,
      undefined
    );
  }
}