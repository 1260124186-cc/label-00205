package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 置信度调整响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ConfidenceAdjustmentResponse {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("original_confidence")
    private Double originalConfidence;

    @JsonProperty("adjusted_confidence")
    private Double adjustedConfidence;

    @JsonProperty("quality_score")
    private Double qualityScore;

    @JsonProperty("quality_level")
    private String qualityLevel;

    @JsonProperty("adjustment_factor")
    private Double adjustmentFactor;

    @JsonProperty("reasons")
    private List<String> reasons;

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

    public Double getAdjustedConfidence() {
        return adjustedConfidence;
    }

    public void setAdjustedConfidence(Double adjustedConfidence) {
        this.adjustedConfidence = adjustedConfidence;
    }

    public Double getQualityScore() {
        return qualityScore;
    }

    public void setQualityScore(Double qualityScore) {
        this.qualityScore = qualityScore;
    }

    public String getQualityLevel() {
        return qualityLevel;
    }

    public void setQualityLevel(String qualityLevel) {
        this.qualityLevel = qualityLevel;
    }

    public Double getAdjustmentFactor() {
        return adjustmentFactor;
    }

    public void setAdjustmentFactor(Double adjustmentFactor) {
        this.adjustmentFactor = adjustmentFactor;
    }

    public List<String> getReasons() {
        return reasons;
    }

    public void setReasons(List<String> reasons) {
        this.reasons = reasons;
    }

}