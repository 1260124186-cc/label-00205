package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 质量检查结果 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class QualityCheckResultSchema {

    @JsonProperty("sensor_id")
    private String sensorId;

    @JsonProperty("total_points")
    private Integer totalPoints;

    @JsonProperty("valid_points")
    private Integer validPoints;

    @JsonProperty("overall_score")
    private Double overallScore;

    @JsonProperty("rule_scores")
    private Map<String, Double> ruleScores;

    @JsonProperty("violations")
    private List<RuleViolationSchema> violations;

    @JsonProperty("violation_count")
    private Integer violationCount;

    @JsonProperty("check_time")
    private OffsetDateTime checkTime;

    public String getSensorId() {
        return sensorId;
    }

    public void setSensorId(String sensorId) {
        this.sensorId = sensorId;
    }

    public Integer getTotalPoints() {
        return totalPoints;
    }

    public void setTotalPoints(Integer totalPoints) {
        this.totalPoints = totalPoints;
    }

    public Integer getValidPoints() {
        return validPoints;
    }

    public void setValidPoints(Integer validPoints) {
        this.validPoints = validPoints;
    }

    public Double getOverallScore() {
        return overallScore;
    }

    public void setOverallScore(Double overallScore) {
        this.overallScore = overallScore;
    }

    public Map<String, Double> getRuleScores() {
        return ruleScores;
    }

    public void setRuleScores(Map<String, Double> ruleScores) {
        this.ruleScores = ruleScores;
    }

    public List<RuleViolationSchema> getViolations() {
        return violations;
    }

    public void setViolations(List<RuleViolationSchema> violations) {
        this.violations = violations;
    }

    public Integer getViolationCount() {
        return violationCount;
    }

    public void setViolationCount(Integer violationCount) {
        this.violationCount = violationCount;
    }

    public OffsetDateTime getCheckTime() {
        return checkTime;
    }

    public void setCheckTime(OffsetDateTime checkTime) {
        this.checkTime = checkTime;
    }

}