package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** QuotaManagement API 客户端 */
public class QuotaManagementClient extends BaseAPIClient {

    public QuotaManagementClient(ApiClientConfig config) {
        super(config);
    }

    /** 获取租户配额 */
    public QuotaResponse getTenantQuotaApiV1TenantsTenantIdQuotaGet(
            Integer tenantId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/quota",
                params,
                null,
                QuotaResponse.class
        );
    }

    /** 更新租户配额 */
    public QuotaResponse updateTenantQuotaApiV1TenantsTenantIdQuotaPut(
            Integer tenantId,
            QuotaUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/tenants/" + tenantId + "/quota",
                params,
                body,
                QuotaResponse.class
        );
    }

}