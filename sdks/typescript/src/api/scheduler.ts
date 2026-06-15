/** Scheduler API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class SchedulerClient extends BaseAPIClient {

  /**
   * 手动触发调度任务（按任务名称）
   */
  async triggerSchedulerJobByNameApiV1SchedulerTriggerJobNamePost(
    jobName: string,
    requireLeader?: boolean,
    numShards?: any
  ): Promise<Models.SchedulerTriggerResponse> {
    const params: Record<string, any> = {};
    if (requireLeader !== undefined) params['require_leader'] = requireLeader;
    if (numShards !== undefined) params['num_shards'] = numShards;

    return this._request(
      "POST",
      `/api/v1/api/v1/scheduler/trigger/${jobName}`,
      params,
      undefined
    );
  }

  /**
   * 查询任务执行日志列表
   */
  async getJobExecutionLogsApiV1SchedulerLogsGet(
    jobName?: any,
    jobType?: any,
    status?: any,
    triggerType?: any,
    startTimeFrom?: any,
    startTimeTo?: any,
    instanceId?: any,
    hasErrors?: any,
    page?: number,
    pageSize?: number
  ): Promise<Models.JobExecutionLogListResponse> {
    const params: Record<string, any> = {};
    if (jobName !== undefined) params['job_name'] = jobName;
    if (jobType !== undefined) params['job_type'] = jobType;
    if (status !== undefined) params['status'] = status;
    if (triggerType !== undefined) params['trigger_type'] = triggerType;
    if (startTimeFrom !== undefined) params['start_time_from'] = startTimeFrom;
    if (startTimeTo !== undefined) params['start_time_to'] = startTimeTo;
    if (instanceId !== undefined) params['instance_id'] = instanceId;
    if (hasErrors !== undefined) params['has_errors'] = hasErrors;
    if (page !== undefined) params['page'] = page;
    if (pageSize !== undefined) params['page_size'] = pageSize;

    return this._request(
      "GET",
      `/api/v1/api/v1/scheduler/logs`,
      params,
      undefined
    );
  }

  /**
   * 获取任务执行日志详情
   */
  async getJobExecutionLogDetailApiV1SchedulerLogsLogIdGet(
    logId: number
  ): Promise<Models.JobExecutionLogSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/scheduler/logs/${logId}`,
      params,
      undefined
    );
  }

  /**
   * 获取Leader选举状态
   */
  async getLeaderStatusApiV1SchedulerLeaderJobKeyGet(
    jobKey: string
  ): Promise<Models.LeaderStatusSchema> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/scheduler/leader/${jobKey}`,
      params,
      undefined
    );
  }
}