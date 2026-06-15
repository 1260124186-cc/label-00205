package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 修复建议 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RepairRecommendationSchema {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("problem_type")
    private String problemType;

    @JsonProperty("description")
    private String description;

    @JsonProperty("recommendation")
    private String recommendation;

    @JsonProperty("priority")
    private String priority;

    @JsonProperty("estimated_effort")
    private Double estimatedEffort;

    @JsonProperty("affected_metrics")
    private List<String> affectedMetrics;

    @JsonProperty("evidence")
    private Map<String, Object> evidence;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public String getProblemType() {
        return problemType;
    }

    public void setProblemType(String problemType) {
        this.problemType = problemType;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getRecommendation() {
        return recommendation;
    }

    public void setRecommendation(String recommendation) {
        this.recommendation = recommendation;
    }

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public Double getEstimatedEffort() {
        return estimatedEffort;
    }

    public void setEstimatedEffort(Double estimatedEffort) {
        this.estimatedEffort = estimatedEffort;
    }

    public List<String> getAffectedMetrics() {
        return affectedMetrics;
    }

    public void setAffectedMetrics(List<String> affectedMetrics) {
        this.affectedMetrics = affectedMetrics;
    }

    public Map<String, Object> getEvidence() {
        return evidence;
    }

    public void setEvidence(Map<String, Object> evidence) {
        this.evidence = evidence;
    }

}