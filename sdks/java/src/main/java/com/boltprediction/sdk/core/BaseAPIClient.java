package com.boltprediction.sdk.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * API 客户端基类
 */
public abstract class BaseAPIClient {
    protected final ApiClientConfig config;
    protected final AuthManager auth;
    protected final RetryManager retry;
    protected final OkHttpClient httpClient;
    protected final ObjectMapper objectMapper;

    public BaseAPIClient(ApiClientConfig config) {
        this.config = config;
        this.auth = new AuthManager(config.getApiKey(), config.getApiKeyHeader());
        this.retry = new RetryManager(
            config.getMaxRetries(),
            config.getRetryBackoffFactor(),
            config.getRetryStatusCodes()
        );
        this.objectMapper = new ObjectMapper();
        this.httpClient = new OkHttpClient.Builder()
            .connectTimeout(config.getTimeout(), TimeUnit.SECONDS)
            .readTimeout(config.getTimeout(), TimeUnit.SECONDS)
            .writeTimeout(config.getTimeout(), TimeUnit.SECONDS)
            .build();
    }

    protected <T> T _request(String method, String path, Map<String, String> params,
                             Object body, Class<T> responseType) throws IOException {
        return retry.execute(() -> {
            Request request = buildRequest(method, path, params, body);
            try (Response response = httpClient.newCall(request).execute()) {
                if (!response.isSuccessful()) {
                    throw new IOException("HTTP " + response.code() + ": " + response.message());
                }
                ResponseBody responseBody = response.body();
                if (responseBody == null) {
                    return null;
                }
                String bodyStr = responseBody.string();
                if (bodyStr.isEmpty()) {
                    return null;
                }
                return objectMapper.readValue(bodyStr, responseType);
            }
        });
    }

    protected JsonNode _requestJson(String method, String path, Map<String, String> params,
                                    Object body) throws IOException {
        return retry.execute(() -> {
            Request request = buildRequest(method, path, params, body);
            try (Response response = httpClient.newCall(request).execute()) {
                if (!response.isSuccessful()) {
                    throw new IOException("HTTP " + response.code() + ": " + response.message());
                }
                ResponseBody responseBody = response.body();
                if (responseBody == null) {
                    return null;
                }
                String bodyStr = responseBody.string();
                if (bodyStr.isEmpty()) {
                    return objectMapper.createObjectNode();
                }
                return objectMapper.readTree(bodyStr);
            }
        });
    }

    private Request buildRequest(String method, String path, Map<String, String> params,
                                 Object body) throws IOException {
        HttpUrl.Builder urlBuilder = HttpUrl.parse(config.getBaseUrl() + path).newBuilder();
        if (params != null) {
            for (Map.Entry<String, String> entry : params.entrySet()) {
                if (entry.getValue() != null) {
                    urlBuilder.addQueryParameter(entry.getKey(), entry.getValue());
                }
            }
        }
        HttpUrl url = urlBuilder.build();

        Request.Builder requestBuilder = new Request.Builder().url(url);

        Map<String, String> headers = auth.getHeaders();
        for (Map.Entry<String, String> entry : headers.entrySet()) {
            requestBuilder.header(entry.getKey(), entry.getValue());
        }
        requestBuilder.header("Content-Type", "application/json");
        requestBuilder.header("Accept", "application/json");

        RequestBody requestBody = null;
        if (body != null) {
            String bodyJson = objectMapper.writeValueAsString(body);
            requestBody = RequestBody.create(
                bodyJson,
                MediaType.parse("application/json")
            );
        }

        requestBuilder.method(method, requestBody);
        return requestBuilder.build();
    }
}
