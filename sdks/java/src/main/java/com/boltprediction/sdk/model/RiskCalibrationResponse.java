package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RiskCalibrationResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RiskCalibrationResponse {

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("prior_weights")
    private Map<String, Double> priorWeights;

    @JsonProperty("risk_thresholds")
    private Map<String, Object> riskThresholds;

    @JsonProperty("version")
    private Integer version;

    @JsonProperty("is_active")
    private Boolean isActive;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("create_time")
    private Object createTime;

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public Map<String, Double> getPriorWeights() {
        return priorWeights;
    }

    public void setPriorWeights(Map<String, Double> priorWeights) {
        this.priorWeights = priorWeights;
    }

    public Map<String, Object> getRiskThresholds() {
        return riskThresholds;
    }

    public void setRiskThresholds(Map<String, Object> riskThresholds) {
        this.riskThresholds = riskThresholds;
    }

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }

    public Boolean getIsActive() {
        return isActive;
    }

    public void setIsActive(Boolean isActive) {
        this.isActive = isActive;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

    public Object getCreateTime() {
        return createTime;
    }

    public void setCreateTime(Object createTime) {
        this.createTime = createTime;
    }

}