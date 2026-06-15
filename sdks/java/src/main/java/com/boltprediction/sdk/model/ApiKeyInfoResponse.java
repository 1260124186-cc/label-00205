package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** APIKeyInfoResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiKeyInfoResponse {

    @JsonProperty("key_id")
    private String keyId;

    @JsonProperty("key_preview")
    private String keyPreview;

    @JsonProperty("name")
    private String name;

    @JsonProperty("permissions")
    private List<String> permissions;

    @JsonProperty("rate_limit")
    private Integer rateLimit;

    @JsonProperty("is_expired")
    private Boolean isExpired;

    @JsonProperty("expires_at")
    private Object expiresAt;

    @JsonProperty("created_at")
    private Object createdAt;

    public String getKeyId() {
        return keyId;
    }

    public void setKeyId(String keyId) {
        this.keyId = keyId;
    }

    public String getKeyPreview() {
        return keyPreview;
    }

    public void setKeyPreview(String keyPreview) {
        this.keyPreview = keyPreview;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public List<String> getPermissions() {
        return permissions;
    }

    public void setPermissions(List<String> permissions) {
        this.permissions = permissions;
    }

    public Integer getRateLimit() {
        return rateLimit;
    }

    public void setRateLimit(Integer rateLimit) {
        this.rateLimit = rateLimit;
    }

    public Boolean getIsExpired() {
        return isExpired;
    }

    public void setIsExpired(Boolean isExpired) {
        this.isExpired = isExpired;
    }

    public Object getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Object expiresAt) {
        this.expiresAt = expiresAt;
    }

    public Object getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Object createdAt) {
        this.createdAt = createdAt;
    }

}