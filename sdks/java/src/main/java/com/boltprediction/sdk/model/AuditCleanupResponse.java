package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 清理过期审计记录响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AuditCleanupResponse {

    @JsonProperty("cleaned_count")
    private Integer cleanedCount;

    @JsonProperty("message")
    private String message;

    public Integer getCleanedCount() {
        return cleanedCount;
    }

    public void setCleanedCount(Integer cleanedCount) {
        this.cleanedCount = cleanedCount;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

}