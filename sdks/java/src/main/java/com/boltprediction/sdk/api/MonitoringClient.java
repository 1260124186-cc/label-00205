package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** Monitoring API 客户端 */
public class MonitoringClient extends BaseAPIClient {

    public MonitoringClient(ApiClientConfig config) {
        super(config);
    }

    /** Get Metrics */
    public Map<String, Object> getMetricsMetricsGet(
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/metrics",
                params,
                null,
                Map.class
        );
    }

}