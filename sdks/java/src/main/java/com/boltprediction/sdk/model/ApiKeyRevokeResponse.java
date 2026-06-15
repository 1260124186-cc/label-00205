package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** APIKeyRevokeResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiKeyRevokeResponse {

    @JsonProperty("key_id")
    private String keyId;

    @JsonProperty("revoked")
    private Boolean revoked;

    public String getKeyId() {
        return keyId;
    }

    public void setKeyId(String keyId) {
        this.keyId = keyId;
    }

    public Boolean getRevoked() {
        return revoked;
    }

    public void setRevoked(Boolean revoked) {
        this.revoked = revoked;
    }

}