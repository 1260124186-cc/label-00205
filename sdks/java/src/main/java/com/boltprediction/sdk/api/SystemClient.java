package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** System API 客户端 */
public class SystemClient extends BaseAPIClient {

    public SystemClient(ApiClientConfig config) {
        super(config);
    }

    /** 健康检查（公开免鉴权） */
    public HealthResponse healthCheckHealthGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/health",
                params,
                null,
                HealthResponse.class
        );
    }

}