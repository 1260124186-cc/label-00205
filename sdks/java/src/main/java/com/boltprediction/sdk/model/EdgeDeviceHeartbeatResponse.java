package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgeDeviceHeartbeatResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgeDeviceHeartbeatResponse {

    @JsonProperty("device_id")
    private String deviceId;

    @JsonProperty("latest_model_version")
    private Object latestModelVersion;

    @JsonProperty("force_sync")
    private Boolean forceSync;

    @JsonProperty("server_time")
    private String serverTime;

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public Object getLatestModelVersion() {
        return latestModelVersion;
    }

    public void setLatestModelVersion(Object latestModelVersion) {
        this.latestModelVersion = latestModelVersion;
    }

    public Boolean getForceSync() {
        return forceSync;
    }

    public void setForceSync(Boolean forceSync) {
        this.forceSync = forceSync;
    }

    public String getServerTime() {
        return serverTime;
    }

    public void setServerTime(String serverTime) {
        this.serverTime = serverTime;
    }

}