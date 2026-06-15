/** ConfigCenter API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class ConfigCenterClient extends BaseAPIClient {

  /**
   * 获取所有配置中心数据
   */
  async getConfigCenterApiV1ConfigCenterGet(
  ): Promise<Models.ConfigCenterResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/config/center`,
      params,
      undefined
    );
  }

  /**
   * 更新预警策略配置
   */
  async updateWarningStrategyApiV1ConfigWarningStrategyPut(
    body: Models.WarningStrategyConfigSchema
  ): Promise<Models.WarningStrategyConfigSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/config/warning-strategy`,
      params,
      body
    );
  }

  /**
   * 更新阈值配置
   */
  async updateThresholdsApiV1ConfigThresholdsPut(
    body: Models.ThresholdConfigSchema
  ): Promise<Models.ThresholdConfigSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/config/thresholds`,
      params,
      body
    );
  }

  /**
   * 获取调度任务列表
   */
  async listSchedulerJobsApiV1ConfigSchedulerJobsGet(
  ): Promise<Models.ScheduledJobSchema[]> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/config/scheduler/jobs`,
      params,
      undefined
    );
  }

  /**
   * 更新调度任务配置
   */
  async updateSchedulerJobApiV1ConfigSchedulerJobsJobIdPut(
    jobId: string,
    body: Models.SchedulerJobUpdateRequest
  ): Promise<Models.ScheduledJobSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/config/scheduler/jobs/${jobId}`,
      params,
      body
    );
  }

  /**
   * 手动触发调度任务
   */
  async triggerSchedulerJobApiV1ConfigSchedulerJobsJobIdTriggerPost(
    jobId: string
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/config/scheduler/jobs/${jobId}/trigger`,
      params,
      undefined
    );
  }
}