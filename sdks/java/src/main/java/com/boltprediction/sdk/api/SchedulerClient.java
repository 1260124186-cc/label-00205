package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** Scheduler API 客户端 */
public class SchedulerClient extends BaseAPIClient {

    public SchedulerClient(ApiClientConfig config) {
        super(config);
    }

    /** 手动触发调度任务（按任务名称） */
    public SchedulerTriggerResponse triggerSchedulerJobByNameApiV1SchedulerTriggerJobNamePost(
            String jobName,
            Boolean requireLeader,
            Object numShards
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (requireLeader != null) params.put("require_leader", String.valueOf(requireLeader));
        if (numShards != null) params.put("num_shards", String.valueOf(numShards));

        return _request(
                "POST",
                "/api/v1/api/v1/scheduler/trigger/" + jobName + "",
                params,
                null,
                SchedulerTriggerResponse.class
        );
    }

    /** 查询任务执行日志列表 */
    public JobExecutionLogListResponse getJobExecutionLogsApiV1SchedulerLogsGet(
            Object jobName,
            Object jobType,
            Object status,
            Object triggerType,
            Object startTimeFrom,
            Object startTimeTo,
            Object instanceId,
            Object hasErrors,
            Integer page,
            Integer pageSize
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (jobName != null) params.put("job_name", String.valueOf(jobName));
        if (jobType != null) params.put("job_type", String.valueOf(jobType));
        if (status != null) params.put("status", String.valueOf(status));
        if (triggerType != null) params.put("trigger_type", String.valueOf(triggerType));
        if (startTimeFrom != null) params.put("start_time_from", String.valueOf(startTimeFrom));
        if (startTimeTo != null) params.put("start_time_to", String.valueOf(startTimeTo));
        if (instanceId != null) params.put("instance_id", String.valueOf(instanceId));
        if (hasErrors != null) params.put("has_errors", String.valueOf(hasErrors));
        if (page != null) params.put("page", String.valueOf(page));
        if (pageSize != null) params.put("page_size", String.valueOf(pageSize));

        return _request(
                "GET",
                "/api/v1/api/v1/scheduler/logs",
                params,
                null,
                JobExecutionLogListResponse.class
        );
    }

    /** 获取任务执行日志详情 */
    public JobExecutionLogSchema getJobExecutionLogDetailApiV1SchedulerLogsLogIdGet(
            Integer logId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/scheduler/logs/" + logId + "",
                params,
                null,
                JobExecutionLogSchema.class
        );
    }

    /** 获取Leader选举状态 */
    public LeaderStatusSchema getLeaderStatusApiV1SchedulerLeaderJobKeyGet(
            String jobKey
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/scheduler/leader/" + jobKey + "",
                params,
                null,
                LeaderStatusSchema.class
        );
    }

}