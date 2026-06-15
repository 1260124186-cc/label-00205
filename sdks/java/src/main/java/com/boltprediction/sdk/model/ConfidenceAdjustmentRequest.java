package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 置信度调整请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ConfidenceAdjustmentRequest {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("original_confidence")
    private Double originalConfidence;

    @JsonProperty("data")
    private List<List<Object>> data;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Double getOriginalConfidence() {
        return originalConfidence;
    }

    public void setOriginalConfidence(Double originalConfidence) {
        this.originalConfidence = originalConfidence;
    }

    public List<List<Object>> getData() {
        return data;
    }

    public void setData(List<List<Object>> data) {
        this.data = data;
    }

}