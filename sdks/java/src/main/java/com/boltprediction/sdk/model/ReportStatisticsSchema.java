package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 报告统计数据 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportStatisticsSchema {

    @JsonProperty("prediction_count")
    private Integer predictionCount;

    @JsonProperty("avg_risk_score")
    private Double avgRiskScore;

    @JsonProperty("min_risk_score")
    private Double minRiskScore;

    @JsonProperty("max_risk_score")
    private Double maxRiskScore;

    @JsonProperty("status_distribution")
    private Map<String, Integer> statusDistribution;

    @JsonProperty("trend")
    private String trend;

    @JsonProperty("max_status")
    private String maxStatus;

    @JsonProperty("fault_types")
    private List<String> faultTypes;

    public Integer getPredictionCount() {
        return predictionCount;
    }

    public void setPredictionCount(Integer predictionCount) {
        this.predictionCount = predictionCount;
    }

    public Double getAvgRiskScore() {
        return avgRiskScore;
    }

    public void setAvgRiskScore(Double avgRiskScore) {
        this.avgRiskScore = avgRiskScore;
    }

    public Double getMinRiskScore() {
        return minRiskScore;
    }

    public void setMinRiskScore(Double minRiskScore) {
        this.minRiskScore = minRiskScore;
    }

    public Double getMaxRiskScore() {
        return maxRiskScore;
    }

    public void setMaxRiskScore(Double maxRiskScore) {
        this.maxRiskScore = maxRiskScore;
    }

    public Map<String, Integer> getStatusDistribution() {
        return statusDistribution;
    }

    public void setStatusDistribution(Map<String, Integer> statusDistribution) {
        this.statusDistribution = statusDistribution;
    }

    public String getTrend() {
        return trend;
    }

    public void setTrend(String trend) {
        this.trend = trend;
    }

    public String getMaxStatus() {
        return maxStatus;
    }

    public void setMaxStatus(String maxStatus) {
        this.maxStatus = maxStatus;
    }

    public List<String> getFaultTypes() {
        return faultTypes;
    }

    public void setFaultTypes(List<String> faultTypes) {
        this.faultTypes = faultTypes;
    }

}