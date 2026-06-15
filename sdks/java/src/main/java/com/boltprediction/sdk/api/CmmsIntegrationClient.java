package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** CMMSIntegration API 客户端 */
public class CmmsIntegrationClient extends BaseAPIClient {

    public CmmsIntegrationClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询CMMS配置列表 */
    public CmmsConfigListResponse listCmmsConfigsApiV1CmmsConfigsGet(
            Object enabled,
            Object systemType,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (enabled != null) params.put("enabled", String.valueOf(enabled));
        if (systemType != null) params.put("system_type", String.valueOf(systemType));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/cmms/configs",
                params,
                null,
                CmmsConfigListResponse.class
        );
    }

    /** 创建CMMS配置 */
    public CmmsConfigResponse createCmmsConfigApiV1CmmsConfigsPost(
            CmmsConfigCreate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/cmms/configs",
                params,
                body,
                CmmsConfigResponse.class
        );
    }

    /** 获取CMMS配置详情 */
    public CmmsConfigResponse getCmmsConfigApiV1CmmsConfigsConfigIdGet(
            Integer configId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/cmms/configs/" + configId + "",
                params,
                null,
                CmmsConfigResponse.class
        );
    }

    /** 更新CMMS配置 */
    public CmmsConfigResponse updateCmmsConfigApiV1CmmsConfigsConfigIdPut(
            Integer configId,
            CmmsConfigUpdate body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/cmms/configs/" + configId + "",
                params,
                body,
                CmmsConfigResponse.class
        );
    }

    /** 删除CMMS配置 */
    public Map<String, Object> deleteCmmsConfigApiV1CmmsConfigsConfigIdDelete(
            Integer configId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/cmms/configs/" + configId + "",
                params,
                null,
                Map.class
        );
    }

    /** 同步工单到CMMS */
    public CmmsSyncResponse syncWorkOrderToCmmsApiV1CmmsSyncWorkOrderPost(
            CmmsSyncRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/cmms/sync/work-order",
                params,
                body,
                CmmsSyncResponse.class
        );
    }

    /** CMMS Webhook回调 */
    public CmmsWebhookResponse cmmsWebhookCallbackApiV1CmmsWebhookConfigIdPost(
            Integer configId,
            Map<String, Object> body,
            Object xSignature
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (xSignature != null) params.put("X-Signature", String.valueOf(xSignature));

        return _request(
                "POST",
                "/api/v1/api/v1/cmms/webhook/" + configId + "",
                params,
                body,
                CmmsWebhookResponse.class
        );
    }

    /** 查询CMMS同步日志 */
    public CmmsSyncLogListResponse listCmmsSyncLogsApiV1CmmsSyncLogsGet(
            Object configId,
            Object workOrderId,
            Object status,
            Object syncDirection,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (configId != null) params.put("config_id", String.valueOf(configId));
        if (workOrderId != null) params.put("work_order_id", String.valueOf(workOrderId));
        if (status != null) params.put("status", String.valueOf(status));
        if (syncDirection != null) params.put("sync_direction", String.valueOf(syncDirection));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/cmms/sync-logs",
                params,
                null,
                CmmsSyncLogListResponse.class
        );
    }

    /** 重试CMMS同步 */
    public CmmsSyncResponse retryCmmsSyncApiV1CmmsSyncLogsLogIdRetryPost(
            Integer logId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/cmms/sync-logs/" + logId + "/retry",
                params,
                null,
                CmmsSyncResponse.class
        );
    }

}