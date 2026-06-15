package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** APIKeyCreateRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiKeyCreateRequest {

    @JsonProperty("name")
    private String name;

    @JsonProperty("permissions")
    private List<String> permissions;

    @JsonProperty("rate_limit")
    private Integer rateLimit;

    @JsonProperty("expires_hours")
    private Object expiresHours;

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

    public Object getExpiresHours() {
        return expiresHours;
    }

    public void setExpiresHours(Object expiresHours) {
        this.expiresHours = expiresHours;
    }

}