package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 故障类型细分详情 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FaultDetailSchema {

    @JsonProperty("fault_type")
    private String faultType;

    @JsonProperty("fault_confidence")
    private Double faultConfidence;

    @JsonProperty("fault_name")
    private String faultName;

    @JsonProperty("severity")
    private Integer severity;

    @JsonProperty("evidence")
    private List<String> evidence;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    @JsonProperty("pattern")
    private Object pattern;

    public String getFaultType() {
        return faultType;
    }

    public void setFaultType(String faultType) {
        this.faultType = faultType;
    }

    public Double getFaultConfidence() {
        return faultConfidence;
    }

    public void setFaultConfidence(Double faultConfidence) {
        this.faultConfidence = faultConfidence;
    }

    public String getFaultName() {
        return faultName;
    }

    public void setFaultName(String faultName) {
        this.faultName = faultName;
    }

    public Integer getSeverity() {
        return severity;
    }

    public void setSeverity(Integer severity) {
        this.severity = severity;
    }

    public List<String> getEvidence() {
        return evidence;
    }

    public void setEvidence(List<String> evidence) {
        this.evidence = evidence;
    }

    public List<String> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<String> recommendations) {
        this.recommendations = recommendations;
    }

    public Object getPattern() {
        return pattern;
    }

    public void setPattern(Object pattern) {
        this.pattern = pattern;
    }

}