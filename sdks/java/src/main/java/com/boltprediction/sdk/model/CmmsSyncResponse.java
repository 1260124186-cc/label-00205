package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CMMS同步响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsSyncResponse {

    @JsonProperty("success")
    private Boolean success;

    @JsonProperty("sync_log_id")
    private Object syncLogId;

    @JsonProperty("external_id")
    private Object externalId;

    @JsonProperty("message")
    private Object message;

    public Boolean getSuccess() {
        return success;
    }

    public void setSuccess(Boolean success) {
        this.success = success;
    }

    public Object getSyncLogId() {
        return syncLogId;
    }

    public void setSyncLogId(Object syncLogId) {
        this.syncLogId = syncLogId;
    }

    public Object getExternalId() {
        return externalId;
    }

    public void setExternalId(Object externalId) {
        this.externalId = externalId;
    }

    public Object getMessage() {
        return message;
    }

    public void setMessage(Object message) {
        this.message = message;
    }

}