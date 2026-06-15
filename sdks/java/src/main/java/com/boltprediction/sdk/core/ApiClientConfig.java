package com.boltprediction.sdk.core;

/**
 * API 客户端配置
 */
public class ApiClientConfig {
    private String baseUrl = "https://api.example.com";
    private String apiKey;
    private String apiVersion = "v1";
    private int timeout = 30;

    private int maxRetries = 3;
    private double retryBackoffFactor = 0.5;
    private int[] retryStatusCodes = {429, 500, 502, 503, 504};

    private String apiKeyHeader = "X-API-Key";

    private String paginationCursorParam = "cursor";
    private String paginationLimitParam = "limit";
    private int paginationDefaultLimit = 20;
    private int paginationMaxLimit = 100;

    public String getBaseUrl() { return baseUrl; }
    public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }

    public String getApiKey() { return apiKey; }
    public void setApiKey(String apiKey) { this.apiKey = apiKey; }

    public String getApiVersion() { return apiVersion; }
    public void setApiVersion(String apiVersion) { this.apiVersion = apiVersion; }

    public int getTimeout() { return timeout; }
    public void setTimeout(int timeout) { this.timeout = timeout; }

    public int getMaxRetries() { return maxRetries; }
    public void setMaxRetries(int maxRetries) { this.maxRetries = maxRetries; }

    public double getRetryBackoffFactor() { return retryBackoffFactor; }
    public void setRetryBackoffFactor(double retryBackoffFactor) { this.retryBackoffFactor = retryBackoffFactor; }

    public int[] getRetryStatusCodes() { return retryStatusCodes; }
    public void setRetryStatusCodes(int[] retryStatusCodes) { this.retryStatusCodes = retryStatusCodes; }

    public String getApiKeyHeader() { return apiKeyHeader; }
    public void setApiKeyHeader(String apiKeyHeader) { this.apiKeyHeader = apiKeyHeader; }

    public String getPaginationCursorParam() { return paginationCursorParam; }
    public void setPaginationCursorParam(String paginationCursorParam) { this.paginationCursorParam = paginationCursorParam; }

    public String getPaginationLimitParam() { return paginationLimitParam; }
    public void setPaginationLimitParam(String paginationLimitParam) { this.paginationLimitParam = paginationLimitParam; }

    public int getPaginationDefaultLimit() { return paginationDefaultLimit; }
    public void setPaginationDefaultLimit(int paginationDefaultLimit) { this.paginationDefaultLimit = paginationDefaultLimit; }

    public int getPaginationMaxLimit() { return paginationMaxLimit; }
    public void setPaginationMaxLimit(int paginationMaxLimit) { this.paginationMaxLimit = paginationMaxLimit; }
}
