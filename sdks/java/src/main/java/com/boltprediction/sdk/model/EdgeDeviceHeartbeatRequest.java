package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgeDeviceHeartbeatRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgeDeviceHeartbeatRequest {

    @JsonProperty("device_id")
    private String deviceId;

    @JsonProperty("model_version")
    private Object modelVersion;

    @JsonProperty("cache_size")
    private Integer cacheSize;

    @JsonProperty("unsynced_count")
    private Integer unsyncedCount;

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public Object getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(Object modelVersion) {
        this.modelVersion = modelVersion;
    }

    public Integer getCacheSize() {
        return cacheSize;
    }

    public void setCacheSize(Integer cacheSize) {
        this.cacheSize = cacheSize;
    }

    public Integer getUnsyncedCount() {
        return unsyncedCount;
    }

    public void setUnsyncedCount(Integer unsyncedCount) {
        this.unsyncedCount = unsyncedCount;
    }

}