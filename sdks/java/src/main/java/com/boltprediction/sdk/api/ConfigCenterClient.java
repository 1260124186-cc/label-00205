package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** ConfigCenter API 客户端 */
public class ConfigCenterClient extends BaseAPIClient {

    public ConfigCenterClient(ApiClientConfig config) {
        super(config);
    }

    /** 获取所有配置中心数据 */
    public ConfigCenterResponse getConfigCenterApiV1ConfigCenterGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/config/center",
                params,
                null,
                ConfigCenterResponse.class
        );
    }

    /** 更新预警策略配置 */
    public WarningStrategyConfigSchema updateWarningStrategyApiV1ConfigWarningStrategyPut(
            WarningStrategyConfigSchema body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/config/warning-strategy",
                params,
                body,
                WarningStrategyConfigSchema.class
        );
    }

    /** 更新阈值配置 */
    public ThresholdConfigSchema updateThresholdsApiV1ConfigThresholdsPut(
            ThresholdConfigSchema body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/config/thresholds",
                params,
                body,
                ThresholdConfigSchema.class
        );
    }

    /** 获取调度任务列表 */
    public List<ScheduledJobSchema> listSchedulerJobsApiV1ConfigSchedulerJobsGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/config/scheduler/jobs",
                params,
                null,
                List.class
        );
    }

    /** 更新调度任务配置 */
    public ScheduledJobSchema updateSchedulerJobApiV1ConfigSchedulerJobsJobIdPut(
            String jobId,
            SchedulerJobUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/config/scheduler/jobs/" + jobId + "",
                params,
                body,
                ScheduledJobSchema.class
        );
    }

    /** 手动触发调度任务 */
    public Map<String, Object> triggerSchedulerJobApiV1ConfigSchedulerJobsJobIdTriggerPost(
            String jobId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/config/scheduler/jobs/" + jobId + "/trigger",
                params,
                null,
                Map.class
        );
    }

}