/** NotificationChannel API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class NotificationChannelClient extends BaseAPIClient {

  /**
   * 查询通知渠道列表
   */
  async listNotificationChannelsApiV1NotificationChannelsGet(
  ): Promise<Models.NotificationChannelResponse[]> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/notification/channels`,
      params,
      undefined
    );
  }

  /**
   * 创建通知渠道
   */
  async createNotificationChannelApiV1NotificationChannelsPost(
    body: Models.NotificationChannelCreate
  ): Promise<Models.NotificationChannelResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/notification/channels`,
      params,
      body
    );
  }

  /**
   * 更新通知渠道
   */
  async updateNotificationChannelApiV1NotificationChannelsChannelIdPut(
    channelId: number,
    body: Models.NotificationChannelUpdate
  ): Promise<Models.NotificationChannelResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/notification/channels/${channelId}`,
      params,
      body
    );
  }

  /**
   * 删除通知渠道
   */
  async deleteNotificationChannelApiV1NotificationChannelsChannelIdDelete(
    channelId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/notification/channels/${channelId}`,
      params,
      undefined
    );
  }

  /**
   * 查询通知发送日志
   */
  async listNotificationLogsApiV1NotificationLogsGet(
    alertId?: any,
    status?: any,
    limit?: number
  ): Promise<Models.NotificationLogResponse[]> {
    const params: Record<string, any> = {};
    if (alertId !== undefined) params['alert_id'] = alertId;
    if (status !== undefined) params['status'] = status;
    if (limit !== undefined) params['limit'] = limit;

    return this._request(
      "GET",
      `/api/v1/api/v1/notification/logs`,
      params,
      undefined
    );
  }
}