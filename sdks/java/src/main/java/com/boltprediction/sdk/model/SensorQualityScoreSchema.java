package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 传感器质量评分 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class SensorQualityScoreSchema {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("overall_score")
    private Double overallScore;

    @JsonProperty("overall_level")
    private String overallLevel;

    @JsonProperty("dimensions")
    private Map<String, QualityDimensionScoreSchema> dimensions;

    @JsonProperty("valid_for_training")
    private Boolean validForTraining;

    @JsonProperty("confidence_adjustment")
    private Double confidenceAdjustment;

    @JsonProperty("rule_violations_count")
    private Map<String, Integer> ruleViolationsCount;

    @JsonProperty("calculate_time")
    private OffsetDateTime calculateTime;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Double getOverallScore() {
        return overallScore;
    }

    public void setOverallScore(Double overallScore) {
        this.overallScore = overallScore;
    }

    public String getOverallLevel() {
        return overallLevel;
    }

    public void setOverallLevel(String overallLevel) {
        this.overallLevel = overallLevel;
    }

    public Map<String, QualityDimensionScoreSchema> getDimensions() {
        return dimensions;
    }

    public void setDimensions(Map<String, QualityDimensionScoreSchema> dimensions) {
        this.dimensions = dimensions;
    }

    public Boolean getValidForTraining() {
        return validForTraining;
    }

    public void setValidForTraining(Boolean validForTraining) {
        this.validForTraining = validForTraining;
    }

    public Double getConfidenceAdjustment() {
        return confidenceAdjustment;
    }

    public void setConfidenceAdjustment(Double confidenceAdjustment) {
        this.confidenceAdjustment = confidenceAdjustment;
    }

    public Map<String, Integer> getRuleViolationsCount() {
        return ruleViolationsCount;
    }

    public void setRuleViolationsCount(Map<String, Integer> ruleViolationsCount) {
        this.ruleViolationsCount = ruleViolationsCount;
    }

    public OffsetDateTime getCalculateTime() {
        return calculateTime;
    }

    public void setCalculateTime(OffsetDateTime calculateTime) {
        this.calculateTime = calculateTime;
    }

}