package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康度计算响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthIndexResponse {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("health_data")
    private HealthIndexDetailSchema healthData;

    @JsonProperty("saved")
    private Boolean saved;

    @JsonProperty("calculate_time")
    private OffsetDateTime calculateTime;

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public HealthIndexDetailSchema getHealthData() {
        return healthData;
    }

    public void setHealthData(HealthIndexDetailSchema healthData) {
        this.healthData = healthData;
    }

    public Boolean getSaved() {
        return saved;
    }

    public void setSaved(Boolean saved) {
        this.saved = saved;
    }

    public OffsetDateTime getCalculateTime() {
        return calculateTime;
    }

    public void setCalculateTime(OffsetDateTime calculateTime) {
        this.calculateTime = calculateTime;
    }

}