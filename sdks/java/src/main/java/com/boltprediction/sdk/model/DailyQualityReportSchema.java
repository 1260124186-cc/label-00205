package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 每日质量报告 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DailyQualityReportSchema {

    @JsonProperty("report_date")
    private OffsetDateTime reportDate;

    @JsonProperty("total_sensors")
    private Integer totalSensors;

    @JsonProperty("average_quality_score")
    private Double averageQualityScore;

    @JsonProperty("quality_distribution")
    private Map<String, Integer> qualityDistribution;

    @JsonProperty("problem_sensors")
    private List<ProblemSensorRankingSchema> problemSensors;

    @JsonProperty("recommendations")
    private List<RepairRecommendationSchema> recommendations;

    @JsonProperty("anomaly_statistics")
    private Map<String, Object> anomalyStatistics;

    @JsonProperty("quality_trend")
    private List<Map<String, Object>> qualityTrend;

    @JsonProperty("summary")
    private String summary;

    @JsonProperty("generated_at")
    private OffsetDateTime generatedAt;

    public OffsetDateTime getReportDate() {
        return reportDate;
    }

    public void setReportDate(OffsetDateTime reportDate) {
        this.reportDate = reportDate;
    }

    public Integer getTotalSensors() {
        return totalSensors;
    }

    public void setTotalSensors(Integer totalSensors) {
        this.totalSensors = totalSensors;
    }

    public Double getAverageQualityScore() {
        return averageQualityScore;
    }

    public void setAverageQualityScore(Double averageQualityScore) {
        this.averageQualityScore = averageQualityScore;
    }

    public Map<String, Integer> getQualityDistribution() {
        return qualityDistribution;
    }

    public void setQualityDistribution(Map<String, Integer> qualityDistribution) {
        this.qualityDistribution = qualityDistribution;
    }

    public List<ProblemSensorRankingSchema> getProblemSensors() {
        return problemSensors;
    }

    public void setProblemSensors(List<ProblemSensorRankingSchema> problemSensors) {
        this.problemSensors = problemSensors;
    }

    public List<RepairRecommendationSchema> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<RepairRecommendationSchema> recommendations) {
        this.recommendations = recommendations;
    }

    public Map<String, Object> getAnomalyStatistics() {
        return anomalyStatistics;
    }

    public void setAnomalyStatistics(Map<String, Object> anomalyStatistics) {
        this.anomalyStatistics = anomalyStatistics;
    }

    public List<Map<String, Object>> getQualityTrend() {
        return qualityTrend;
    }

    public void setQualityTrend(List<Map<String, Object>> qualityTrend) {
        this.qualityTrend = qualityTrend;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public OffsetDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(OffsetDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

}