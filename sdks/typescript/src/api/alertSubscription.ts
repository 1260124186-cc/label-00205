/** AlertSubscription API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class AlertSubscriptionClient extends BaseAPIClient {

  /**
   * 查询订阅列表
   */
  async listAlertSubscriptionsApiV1AlertSubscriptionsGet(
    subscriberType?: any,
    subscriberId?: any,
    enabled?: any
  ): Promise<Models.AlertSubscriptionResponse[]> {
    const params: Record<string, any> = {};
    if (subscriberType !== undefined) params['subscriber_type'] = subscriberType;
    if (subscriberId !== undefined) params['subscriber_id'] = subscriberId;
    if (enabled !== undefined) params['enabled'] = enabled;

    return this._request(
      "GET",
      `/api/v1/api/v1/alert/subscriptions`,
      params,
      undefined
    );
  }

  /**
   * 创建订阅
   */
  async createAlertSubscriptionApiV1AlertSubscriptionsPost(
    body: Models.AlertSubscriptionCreate
  ): Promise<Models.AlertSubscriptionResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/alert/subscriptions`,
      params,
      body
    );
  }

  /**
   * 获取订阅详情
   */
  async getAlertSubscriptionApiV1AlertSubscriptionsSubIdGet(
    subId: number
  ): Promise<Models.AlertSubscriptionResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/alert/subscriptions/${subId}`,
      params,
      undefined
    );
  }

  /**
   * 更新订阅
   */
  async updateAlertSubscriptionApiV1AlertSubscriptionsSubIdPut(
    subId: number,
    body: Models.AlertSubscriptionUpdate
  ): Promise<Models.AlertSubscriptionResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/alert/subscriptions/${subId}`,
      params,
      body
    );
  }

  /**
   * 删除订阅
   */
  async deleteAlertSubscriptionApiV1AlertSubscriptionsSubIdDelete(
    subId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/alert/subscriptions/${subId}`,
      params,
      undefined
    );
  }
}