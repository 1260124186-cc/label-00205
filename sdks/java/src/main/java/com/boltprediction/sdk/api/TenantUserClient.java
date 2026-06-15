package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** TenantUser API 客户端 */
public class TenantUserClient extends BaseAPIClient {

    public TenantUserClient(ApiClientConfig config) {
        super(config);
    }

    /** 创建租户用户 */
    public TenantUserResponse createTenantUserApiV1TenantsTenantIdUsersPost(
            Integer tenantId,
            TenantUserCreateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/tenants/" + tenantId + "/users",
                params,
                body,
                TenantUserResponse.class
        );
    }

    /** 查询租户用户列表 */
    public TenantUserListResponse listTenantUsersApiV1TenantsTenantIdUsersGet(
            Integer tenantId,
            Object role,
            Object status,
            Integer limit,
            Integer offset
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (role != null) params.put("role", String.valueOf(role));
        if (status != null) params.put("status", String.valueOf(status));
        if (limit != null) params.put("limit", String.valueOf(limit));
        if (offset != null) params.put("offset", String.valueOf(offset));

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/users",
                params,
                null,
                TenantUserListResponse.class
        );
    }

    /** 获取租户用户详情 */
    public TenantUserResponse getTenantUserApiV1TenantsTenantIdUsersUserIdGet(
            Integer tenantId,
            Integer userId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/users/" + userId + "",
                params,
                null,
                TenantUserResponse.class
        );
    }

    /** 更新租户用户 */
    public TenantUserResponse updateTenantUserApiV1TenantsTenantIdUsersUserIdPut(
            Integer tenantId,
            Integer userId,
            TenantUserUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/tenants/" + tenantId + "/users/" + userId + "",
                params,
                body,
                TenantUserResponse.class
        );
    }

    /** 禁用租户用户 */
    public Map<String, Object> deleteTenantUserApiV1TenantsTenantIdUsersUserIdDelete(
            Integer tenantId,
            Integer userId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/tenants/" + tenantId + "/users/" + userId + "",
                params,
                null,
                Map.class
        );
    }

    /** 修改租户用户密码 */
    public Map<String, Object> changeTenantUserPasswordApiV1TenantsTenantIdUsersUserIdPasswordPut(
            Integer tenantId,
            Integer userId,
            TenantUserPasswordRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/tenants/" + tenantId + "/users/" + userId + "/password",
                params,
                body,
                Map.class
        );
    }

}