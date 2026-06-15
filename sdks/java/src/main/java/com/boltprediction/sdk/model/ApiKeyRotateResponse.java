package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** APIKeyRotateResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiKeyRotateResponse {

    @JsonProperty("old_key_id")
    private String oldKeyId;

    @JsonProperty("new_key")
    private String newKey;

    @JsonProperty("new_key_id")
    private String newKeyId;

    @JsonProperty("old_key_grace_expires")
    private OffsetDateTime oldKeyGraceExpires;

    @JsonProperty("permissions")
    private List<String> permissions;

    @JsonProperty("rate_limit")
    private Integer rateLimit;

    public String getOldKeyId() {
        return oldKeyId;
    }

    public void setOldKeyId(String oldKeyId) {
        this.oldKeyId = oldKeyId;
    }

    public String getNewKey() {
        return newKey;
    }

    public void setNewKey(String newKey) {
        this.newKey = newKey;
    }

    public String getNewKeyId() {
        return newKeyId;
    }

    public void setNewKeyId(String newKeyId) {
        this.newKeyId = newKeyId;
    }

    public OffsetDateTime getOldKeyGraceExpires() {
        return oldKeyGraceExpires;
    }

    public void setOldKeyGraceExpires(OffsetDateTime oldKeyGraceExpires) {
        this.oldKeyGraceExpires = oldKeyGraceExpires;
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

}