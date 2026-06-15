package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** TenantApiKey API 客户端 */
public class TenantApiKeyClient extends BaseAPIClient {

    public TenantApiKeyClient(ApiClientConfig config) {
        super(config);
    }

    /** 创建租户API Key */
    public TenantApiKeyCreateResponse createTenantApiKeyApiV1TenantsTenantIdApiKeysPost(
            Integer tenantId,
            TenantApiKeyCreateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/tenants/" + tenantId + "/api-keys",
                params,
                body,
                TenantApiKeyCreateResponse.class
        );
    }

    /** 查询租户API Key列表 */
    public Map<String, Object> listTenantApiKeysApiV1TenantsTenantIdApiKeysGet(
            Integer tenantId,
            Object status
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (status != null) params.put("status", String.valueOf(status));

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/api-keys",
                params,
                null,
                Map.class
        );
    }

    /** 获取API Key详情 */
    public TenantApiKeyResponse getTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdGet(
            Integer tenantId,
            Integer keyId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/api-keys/" + keyId + "",
                params,
                null,
                TenantApiKeyResponse.class
        );
    }

    /** 更新API Key */
    public TenantApiKeyResponse updateTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdPut(
            Integer tenantId,
            Integer keyId,
            TenantApiKeyUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/tenants/" + tenantId + "/api-keys/" + keyId + "",
                params,
                body,
                TenantApiKeyResponse.class
        );
    }

    /** 吊销API Key */
    public Map<String, Object> revokeTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdDelete(
            Integer tenantId,
            Integer keyId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/tenants/" + tenantId + "/api-keys/" + keyId + "",
                params,
                null,
                Map.class
        );
    }

}