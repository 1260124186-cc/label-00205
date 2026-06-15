package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** ApiAuditLog API 客户端 */
public class ApiAuditLogClient extends BaseAPIClient {

    public ApiAuditLogClient(ApiClientConfig config) {
        super(config);
    }

    /** 查询API审计日志 */
    public ApiAuditLogListResponse queryAuditLogsApiV1AuthAuditLogsGet(
            Object keyId,
            Object path,
            Object method,
            Object startTime,
            Object endTime,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (keyId != null) params.put("key_id", String.valueOf(keyId));
        if (path != null) params.put("path", String.valueOf(path));
        if (method != null) params.put("method", String.valueOf(method));
        if (startTime != null) params.put("start_time", String.valueOf(startTime));
        if (endTime != null) params.put("end_time", String.valueOf(endTime));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/auth/audit-logs",
                params,
                null,
                ApiAuditLogListResponse.class
        );
    }

}