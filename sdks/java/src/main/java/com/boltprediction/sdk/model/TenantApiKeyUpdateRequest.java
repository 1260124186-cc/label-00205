package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantAPIKeyUpdateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantApiKeyUpdateRequest {

    @JsonProperty("key_name")
    private Object keyName;

    @JsonProperty("permissions")
    private Object permissions;

    @JsonProperty("rate_limit")
    private Object rateLimit;

    @JsonProperty("status")
    private Object status;

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

    public Object getRateLimit() {
        return rateLimit;
    }

    public void setRateLimit(Object rateLimit) {
        this.rateLimit = rateLimit;
    }

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
    }

    public Object getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Object expiresAt) {
        this.expiresAt = expiresAt;
    }

}