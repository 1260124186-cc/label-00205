package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** EdgePredictionUploadRequest */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EdgePredictionUploadRequest {

    @JsonProperty("device_id")
    private String deviceId;

    @JsonProperty("predictions")
    private List<Map<String, Object>> predictions;

    public String getDeviceId() {
        return deviceId;
    }

    public void setDeviceId(String deviceId) {
        this.deviceId = deviceId;
    }

    public List<Map<String, Object>> getPredictions() {
        return predictions;
    }

    public void setPredictions(List<Map<String, Object>> predictions) {
        this.predictions = predictions;
    }

}