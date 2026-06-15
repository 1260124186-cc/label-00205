package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RateLimitStatusResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RateLimitStatusResponse {

    @JsonProperty("key_id")
    private String keyId;

    @JsonProperty("limit")
    private Integer limit;

    @JsonProperty("remaining")
    private Integer remaining;

    @JsonProperty("used")
    private Integer used;

    public String getKeyId() {
        return keyId;
    }

    public void setKeyId(String keyId) {
        this.keyId = keyId;
    }

    public Integer getLimit() {
        return limit;
    }

    public void setLimit(Integer limit) {
        this.limit = limit;
    }

    public Integer getRemaining() {
        return remaining;
    }

    public void setRemaining(Integer remaining) {
        this.remaining = remaining;
    }

    public Integer getUsed() {
        return used;
    }

    public void setUsed(Integer used) {
        this.used = used;
    }

}