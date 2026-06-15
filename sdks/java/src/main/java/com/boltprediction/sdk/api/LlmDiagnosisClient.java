package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** LLMDiagnosis API 客户端 */
public class LlmDiagnosisClient extends BaseAPIClient {

    public LlmDiagnosisClient(ApiClientConfig config) {
        super(config);
    }

    /** 生成单次诊断报告 */
    public DiagnosisReportResponse generateDiagnosisReportApiV1ReportDiagnosisPost(
            DiagnosisReportRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/report/diagnosis",
                params,
                body,
                DiagnosisReportResponse.class
        );
    }

    /** 生成周期报告（周报/月报） */
    public PeriodicReportResponse generatePeriodicReportApiV1ReportGeneratePost(
            ReportGenerateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/report/generate",
                params,
                body,
                PeriodicReportResponse.class
        );
    }

    /** 批量生成周期报告 */
    public BatchReportResponse batchGeneratePeriodicReportsApiV1ReportBatchGeneratePost(
            BatchReportGenerateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/report/batch-generate",
                params,
                body,
                BatchReportResponse.class
        );
    }

    /** 获取 LLM 配置状态 */
    public Map<String, Object> getLlmConfigStatusApiV1ReportConfigGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/report/config",
                params,
                null,
                Map.class
        );
    }

}