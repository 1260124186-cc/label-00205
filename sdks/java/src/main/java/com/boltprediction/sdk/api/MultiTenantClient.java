package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** MultiTenant API 客户端 */
public class MultiTenantClient extends BaseAPIClient {

    public MultiTenantClient(ApiClientConfig config) {
        super(config);
    }

    /** 租户用户登录 */
    public TenantLoginResponse tenantLoginApiV1TenantLoginPost(
            TenantLoginRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/tenant/login",
                params,
                body,
                TenantLoginResponse.class
        );
    }

    /** 获取当前登录用户信息 */
    public Map<String, Object> getCurrentTenantUserApiV1TenantMeGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenant/me",
                params,
                null,
                Map.class
        );
    }

    /** 租户用户登出 */
    public Map<String, Object> tenantLogoutApiV1TenantLogoutPost(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/tenant/logout",
                params,
                null,
                Map.class
        );
    }

    /** 创建租户 */
    public TenantResponse createTenantApiV1TenantsPost(
            TenantCreateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/tenants",
                params,
                body,
                TenantResponse.class
        );
    }

    /** 查询租户列表 */
    public TenantListResponse listTenantsApiV1TenantsGet(
            Object status,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (status != null) params.put("status", String.valueOf(status));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/tenants",
                params,
                null,
                TenantListResponse.class
        );
    }

    /** 获取租户详情 */
    public TenantResponse getTenantApiV1TenantsTenantIdGet(
            Integer tenantId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "",
                params,
                null,
                TenantResponse.class
        );
    }

    /** 更新租户 */
    public TenantResponse updateTenantApiV1TenantsTenantIdPut(
            Integer tenantId,
            TenantUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/tenants/" + tenantId + "",
                params,
                body,
                TenantResponse.class
        );
    }

    /** 删除租户 */
    public Map<String, Object> deleteTenantApiV1TenantsTenantIdDelete(
            Integer tenantId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/tenants/" + tenantId + "",
                params,
                null,
                Map.class
        );
    }

}