package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** AnomalyManagement API 客户端 */
public class AnomalyManagementClient extends BaseAPIClient {

    public AnomalyManagementClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询异常数据 */
    public AnomalyListResponse queryAnomaliesApiV1AnomalyQueryPost(
            AnomalyQueryRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/anomaly/query",
                params,
                body,
                AnomalyListResponse.class
        );
    }

    /** 获取异常详情 */
    public AnomalyDataResponse getAnomalyDetailApiV1AnomalyAnomalyIdGet(
            Integer anomalyId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/anomaly/" + anomalyId + "",
                params,
                null,
                AnomalyDataResponse.class
        );
    }

    /** 确认异常（真实异常） */
    public AnomalyDataResponse confirmAnomalyApiV1AnomalyConfirmPost(
            AnomalyConfirmRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/anomaly/confirm",
                params,
                body,
                AnomalyDataResponse.class
        );
    }

    /** 标注异常为误报 */
    public AnomalyDataResponse markAnomalyFalsePositiveApiV1AnomalyFalsePositivePost(
            AnomalyFalsePositiveRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/anomaly/false-positive",
                params,
                body,
                AnomalyDataResponse.class
        );
    }

    /** 批量确认异常 */
    public AnomalyBatchResultResponse batchConfirmAnomaliesApiV1AnomalyBatchConfirmPost(
            AnomalyBatchConfirmRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/anomaly/batch-confirm",
                params,
                body,
                AnomalyBatchResultResponse.class
        );
    }

    /** 批量标注误报 */
    public AnomalyBatchResultResponse batchMarkFalsePositivesApiV1AnomalyBatchFalsePositivePost(
            AnomalyBatchFalsePositiveRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/anomaly/batch-false-positive",
                params,
                body,
                AnomalyBatchResultResponse.class
        );
    }

    /** 获取异常统计信息 */
    public AnomalyStatisticsResponse getAnomalyStatisticsApiV1AnomalyStatisticsSummaryGet(
            Object sensorId,
            Object startTime,
            Object endTime
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (sensorId != null) params.put("sensor_id", String.valueOf(sensorId));
        if (startTime != null) params.put("start_time", String.valueOf(startTime));
        if (endTime != null) params.put("end_time", String.valueOf(endTime));

        return _request(
                "GET",
                "/api/v1/api/v1/anomaly/statistics/summary",
                params,
                null,
                AnomalyStatisticsResponse.class
        );
    }

    /** 检查异常对预警等级的影响 */
    public AnomalyWarningImpactResponse checkAnomalyWarningImpactApiV1AnomalyWarningImpactSensorIdGet(
            String sensorId,
            Integer currentLevel
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (currentLevel != null) params.put("current_level", String.valueOf(currentLevel));

        return _request(
                "GET",
                "/api/v1/api/v1/anomaly/warning-impact/" + sensorId + "",
                params,
                null,
                AnomalyWarningImpactResponse.class
        );
    }

}