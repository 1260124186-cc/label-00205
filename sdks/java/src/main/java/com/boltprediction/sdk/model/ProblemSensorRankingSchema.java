package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 问题传感器排行 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ProblemSensorRankingSchema {

    @JsonProperty("rank")
    private Integer rank;

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("quality_score")
    private Double qualityScore;

    @JsonProperty("quality_level")
    private String qualityLevel;

    @JsonProperty("problem_types")
    private List<String> problemTypes;

    @JsonProperty("violation_count")
    private Integer violationCount;

    @JsonProperty("anomaly_count")
    private Integer anomalyCount;

    @JsonProperty("collection_anomaly_ratio")
    private Double collectionAnomalyRatio;

    @JsonProperty("trend")
    private String trend;

    public Integer getRank() {
        return rank;
    }

    public void setRank(Integer rank) {
        this.rank = rank;
    }

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
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

    public List<String> getProblemTypes() {
        return problemTypes;
    }

    public void setProblemTypes(List<String> problemTypes) {
        this.problemTypes = problemTypes;
    }

    public Integer getViolationCount() {
        return violationCount;
    }

    public void setViolationCount(Integer violationCount) {
        this.violationCount = violationCount;
    }

    public Integer getAnomalyCount() {
        return anomalyCount;
    }

    public void setAnomalyCount(Integer anomalyCount) {
        this.anomalyCount = anomalyCount;
    }

    public Double getCollectionAnomalyRatio() {
        return collectionAnomalyRatio;
    }

    public void setCollectionAnomalyRatio(Double collectionAnomalyRatio) {
        this.collectionAnomalyRatio = collectionAnomalyRatio;
    }

    public String getTrend() {
        return trend;
    }

    public void setTrend(String trend) {
        this.trend = trend;
    }

}