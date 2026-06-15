package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantAPIKeyResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantApiKeyResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("tenant_id")
    private Integer tenantId;

    @JsonProperty("api_key")
    private String apiKey;

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

    @JsonProperty("last_used_at")
    private Object lastUsedAt;

    @JsonProperty("status")
    private String status;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public Integer getTenantId() {
        return tenantId;
    }

    public void setTenantId(Integer tenantId) {
        this.tenantId = tenantId;
    }

    public String getApiKey() {
        return apiKey;
    }

    public void setApiKey(String apiKey) {
        this.apiKey = apiKey;
    }

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

    public Object getLastUsedAt() {
        return lastUsedAt;
    }

    public void setLastUsedAt(Object lastUsedAt) {
        this.lastUsedAt = lastUsedAt;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

}