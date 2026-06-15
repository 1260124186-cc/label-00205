package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** ApiKeyManagement API 客户端 */
public class ApiKeyManagementClient extends BaseAPIClient {

    public ApiKeyManagementClient(ApiClientConfig config) {
        super(config);
    }

    /** 列出所有API密钥 */
    public ApiKeyListResponse listApiKeysApiV1AuthKeysGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/auth/keys",
                params,
                null,
                ApiKeyListResponse.class
        );
    }

    /** 创建API密钥 */
    public ApiKeyCreateResponse createApiKeyApiV1AuthKeysPost(
            ApiKeyCreateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/auth/keys",
                params,
                body,
                ApiKeyCreateResponse.class
        );
    }

    /** 轮换API密钥 */
    public ApiKeyRotateResponse rotateApiKeyApiV1AuthKeysKeyIdRotatePost(
            String keyId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/auth/keys/" + keyId + "/rotate",
                params,
                null,
                ApiKeyRotateResponse.class
        );
    }

    /** 吊销API密钥 */
    public ApiKeyRevokeResponse revokeApiKeyApiV1AuthKeysKeyIdDelete(
            String keyId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/auth/keys/" + keyId + "",
                params,
                null,
                ApiKeyRevokeResponse.class
        );
    }

    /** 查询密钥限流状态 */
    public RateLimitStatusResponse getRateLimitStatusApiV1AuthKeysKeyIdRateLimitGet(
            String keyId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/auth/keys/" + keyId + "/rate-limit",
                params,
                null,
                RateLimitStatusResponse.class
        );
    }

}