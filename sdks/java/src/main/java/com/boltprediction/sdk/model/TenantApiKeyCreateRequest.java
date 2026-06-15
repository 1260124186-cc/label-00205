package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantAPIKeyCreateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantApiKeyCreateRequest {

    @JsonProperty("key_name")
    private Object keyName;

    @JsonProperty("permissions")
    private Object permissions;

    @JsonProperty("rate_limit")
    private Integer rateLimit;

    @JsonProperty("user_id")
    private Object userId;

    @JsonProperty("expires_at")
    private Object expiresAt;

    public Object getKeyName() {
        return keyName;
    }

    public void setKeyName(Object keyName) {
        this.keyName = keyName;
    }

    public Object getPermissions() {
        return permissions;
    }

    public void setPermissions(Object permissions) {
        this.permissions = permissions;
    }

    public Integer getRateLimit() {
        return rateLimit;
    }

    public void setRateLimit(Integer rateLimit) {
        this.rateLimit = rateLimit;
    }

    public Object getUserId() {
        return userId;
    }

    public void setUserId(Object userId) {
        this.userId = userId;
    }

    public Object getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Object expiresAt) {
        this.expiresAt = expiresAt;
    }

}