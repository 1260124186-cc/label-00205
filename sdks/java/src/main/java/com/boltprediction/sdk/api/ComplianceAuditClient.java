package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** ComplianceAudit API 客户端 */
public class ComplianceAuditClient extends BaseAPIClient {

    public ComplianceAuditClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询审计记录列表 */
    public AuditListResponse listAuditRecordsApiV1AuditRecordsGet(
            Object nodeType,
            Object nodeId,
            Object modelVersion,
            Object startTime,
            Object endTime,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (nodeId != null) params.put("node_id", String.valueOf(nodeId));
        if (modelVersion != null) params.put("model_version", String.valueOf(modelVersion));
        if (startTime != null) params.put("start_time", String.valueOf(startTime));
        if (endTime != null) params.put("end_time", String.valueOf(endTime));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/audit/records",
                params,
                null,
                AuditListResponse.class
        );
    }

    /** 获取审计记录详情 */
    public AuditRecordResponse getAuditRecordApiV1AuditRecordsAuditIdGet(
            Integer auditId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/audit/records/" + auditId + "",
                params,
                null,
                AuditRecordResponse.class
        );
    }

    /** 更新审计记录保留年限 */
    public AuditRecordResponse updateAuditRetentionApiV1AuditRecordsAuditIdRetentionPut(
            Integer auditId,
            AuditRetentionUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/audit/records/" + auditId + "/retention",
                params,
                body,
                AuditRecordResponse.class
        );
    }

    /** 清理过期审计记录 */
    public AuditCleanupResponse cleanupExpiredAuditsApiV1AuditCleanupPost(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/audit/cleanup",
                params,
                null,
                AuditCleanupResponse.class
        );
    }

    /** 导出审计包 */
    public Map<String, Object> exportAuditPackageApiV1AuditExportPost(
            AuditExportRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/audit/export",
                params,
                body,
                Map.class
        );
    }

    /** 获取可解释性报告 */
    public ExplainabilityReportResponse getExplainabilityReportApiV1AuditRecordsAuditIdExplainabilityGet(
            Integer auditId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/audit/records/" + auditId + "/explainability",
                params,
                null,
                ExplainabilityReportResponse.class
        );
    }

}