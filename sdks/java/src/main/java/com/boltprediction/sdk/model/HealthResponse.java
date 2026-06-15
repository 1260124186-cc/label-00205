package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康检查响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthResponse {

    @JsonProperty("status")
    private String status;

    @JsonProperty("version")
    private String version;

    @JsonProperty("timestamp")
    private OffsetDateTime timestamp;

    @JsonProperty("components")
    private Object components;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public OffsetDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(OffsetDateTime timestamp) {
        this.timestamp = timestamp;
    }

    public Object getComponents() {
        return components;
    }

    public void setComponents(Object components) {
        this.components = components;
    }

}