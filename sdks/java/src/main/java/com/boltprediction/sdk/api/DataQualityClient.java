package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** DataQuality API 客户端 */
public class DataQualityClient extends BaseAPIClient {

    public DataQualityClient(ApiClientConfig config) {
        super(config);
    }

    /** 评估传感器数据质量 */
    public QualityEvaluationResponse checkDataQualityApiV1DataQualityCheckPost(
            DataQualityCheckRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/data-quality/check",
                params,
                body,
                QualityEvaluationResponse.class
        );
    }

    /** 批量评估传感器数据质量 */
    public Map<String, Object> batchCheckDataQualityApiV1DataQualityBatchCheckPost(
            DataQualityCheckBatchRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/data-quality/batch-check",
                params,
                body,
                Map.class
        );
    }

    /** 获取传感器质量评分 */
    public SensorQualityScoreSchema getSensorQualityScoreApiV1DataQualityScoreSensorIdGet(
            String sensorId,
            Integer recentDataLimit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (recentDataLimit != null) params.put("recent_data_limit", String.valueOf(recentDataLimit));

        return _request(
                "GET",
                "/api/v1/api/v1/data-quality/score/" + sensorId + "",
                params,
                null,
                SensorQualityScoreSchema.class
        );
    }

    /** 调整预测置信度 */
    public ConfidenceAdjustmentResponse adjustPredictionConfidenceApiV1DataQualityAdjustConfidencePost(
            ConfidenceAdjustmentRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/data-quality/adjust-confidence",
                params,
                body,
                ConfidenceAdjustmentResponse.class
        );
    }

    /** 生成每日质量报告 */
    public DailyQualityReportSchema generateQualityReportApiV1DataQualityReportGeneratePost(
            QualityReportRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/data-quality/report/generate",
                params,
                body,
                DailyQualityReportSchema.class
        );
    }

    /** 获取最新质量报告 */
    public DailyQualityReportSchema getLatestQualityReportApiV1DataQualityReportLatestGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/data-quality/report/latest",
                params,
                null,
                DailyQualityReportSchema.class
        );
    }

    /** 获取传感器质量历史记录 */
    public Map<String, Object> getSensorQualityHistoryApiV1DataQualityHistorySensorIdGet(
            DataQualityHistoryRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/data-quality/history/{sensor_id}",
                params,
                body,
                Map.class
        );
    }

    /** 获取问题传感器列表 */
    public Map<String, Object> getProblemSensorsApiV1DataQualityProblemSensorsGet(
            Double minScore,
            Integer limit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (minScore != null) params.put("min_score", String.valueOf(minScore));
        if (limit != null) params.put("limit", String.valueOf(limit));

        return _request(
                "GET",
                "/api/v1/api/v1/data-quality/problem-sensors",
                params,
                null,
                Map.class
        );
    }

    /** 分类传感器异常 */
    public Map<String, Object> classifySensorAnomaliesApiV1DataQualityAnomaliesSensorIdClassifyGet(
            String sensorId,
            Object startTime,
            Object endTime,
            Integer recentDataLimit
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (startTime != null) params.put("start_time", String.valueOf(startTime));
        if (endTime != null) params.put("end_time", String.valueOf(endTime));
        if (recentDataLimit != null) params.put("recent_data_limit", String.valueOf(recentDataLimit));

        return _request(
                "GET",
                "/api/v1/api/v1/data-quality/anomalies/" + sensorId + "/classify",
                params,
                null,
                Map.class
        );
    }

    /** 获取数据质量总览 */
    public Map<String, Object> getDataQualitySummaryApiV1DataQualitySummaryGet(
            Integer days
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (days != null) params.put("days", String.valueOf(days));

        return _request(
                "GET",
                "/api/v1/api/v1/data-quality/summary",
                params,
                null,
                Map.class
        );
    }

}