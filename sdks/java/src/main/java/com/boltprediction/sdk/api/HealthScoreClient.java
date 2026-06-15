package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** HealthScore API 客户端 */
public class HealthScoreClient extends BaseAPIClient {

    public HealthScoreClient(ApiClientConfig config) {
        super(config);
    }

    /** 计算螺栓健康度指数 HI */
    public HealthIndexResponse calculateHealthIndexApiV1HealthCalculatePost(
            HealthIndexCalculateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/health/calculate",
                params,
                body,
                HealthIndexResponse.class
        );
    }

    /** 批量计算螺栓健康度 */
    public HealthIndexBatchResponse calculateHealthIndexBatchApiV1HealthCalculateBatchPost(
            HealthIndexBatchCalculateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/health/calculate/batch",
                params,
                body,
                HealthIndexBatchResponse.class
        );
    }

    /** 查询健康度历史记录 */
    public HealthIndexHistoryResponse getHealthHistoryApiV1HealthHistoryGet(
            String nodeId,
            String nodeType,
            Object startTime,
            Object endTime,
            Integer limit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (startTime != null) params.put("start_time", String.valueOf(startTime));
        if (endTime != null) params.put("end_time", String.valueOf(endTime));
        if (limit != null) params.put("limit", String.valueOf(limit));

        return _request(
                "GET",
                "/api/v1/api/v1/health/history",
                params,
                null,
                HealthIndexHistoryResponse.class
        );
    }

    /** 预测剩余使用寿命 RUL */
    public RulPredictionResponse predictRulApiV1HealthRulPredictPost(
            RulPredictionRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/health/rul/predict",
                params,
                body,
                RulPredictionResponse.class
        );
    }

    /** 生成产线/装置级健康度汇总报表 */
    public HealthRollupResponse generateHealthRollupApiV1HealthRollupPost(
            HealthRollupRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/health/rollup",
                params,
                body,
                HealthRollupResponse.class
        );
    }

}