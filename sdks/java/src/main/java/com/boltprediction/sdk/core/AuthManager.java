package com.boltprediction.sdk.core;

import java.util.HashMap;
import java.util.Map;

/**
 * 认证管理器
 */
public class AuthManager {
    private String apiKey;
    private String headerName;

    public AuthManager(String apiKey) {
        this(apiKey, "X-API-Key");
    }

    public AuthManager(String apiKey, String headerName) {
        this.apiKey = apiKey;
        this.headerName = headerName;
    }

    public Map<String, String> getHeaders() {
        Map<String, String> headers = new HashMap<>();
        if (apiKey != null && !apiKey.isEmpty()) {
            headers.put(headerName, apiKey);
        }
        return headers;
    }

    public void setApiKey(String apiKey) {
        this.apiKey = apiKey;
    }
}
