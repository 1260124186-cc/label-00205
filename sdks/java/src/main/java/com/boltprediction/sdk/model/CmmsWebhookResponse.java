package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CMMS Webhook响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsWebhookResponse {

    @JsonProperty("success")
    private Boolean success;

    @JsonProperty("message")
    private String message;

    @JsonProperty("processed_count")
    private Object processedCount;

    public Boolean getSuccess() {
        return success;
    }

    public void setSuccess(Boolean success) {
        this.success = success;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Object getProcessedCount() {
        return processedCount;
    }

    public void setProcessedCount(Object processedCount) {
        this.processedCount = processedCount;
    }

}