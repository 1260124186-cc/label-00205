package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 碳排风险排行单项 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CarbonRiskItemSchema {

    @JsonProperty("rank")
    private Object rank;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_name")
    private String nodeName;

    @JsonProperty("hi_score")
    private Double hiScore;

    @JsonProperty("hi_level")
    private String hiLevel;

    @JsonProperty("carbon_risk_score")
    private Double carbonRiskScore;

    @JsonProperty("carbon_risk_level")
    private String carbonRiskLevel;

    @JsonProperty("monthly_leakage_volume_m3")
    private Double monthlyLeakageVolumeM3;

    @JsonProperty("monthly_carbon_increment_kg")
    private Double monthlyCarbonIncrementKg;

    @JsonProperty("priority_score")
    private Double priorityScore;

    @JsonProperty("trend")
    private String trend;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    public Object getRank() {
        return rank;
    }

    public void setRank(Object rank) {
        this.rank = rank;
    }

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

    public String getNodeName() {
        return nodeName;
    }

    public void setNodeName(String nodeName) {
        this.nodeName = nodeName;
    }

    public Double getHiScore() {
        return hiScore;
    }

    public void setHiScore(Double hiScore) {
        this.hiScore = hiScore;
    }

    public String getHiLevel() {
        return hiLevel;
    }

    public void setHiLevel(String hiLevel) {
        this.hiLevel = hiLevel;
    }

    public Double getCarbonRiskScore() {
        return carbonRiskScore;
    }

    public void setCarbonRiskScore(Double carbonRiskScore) {
        this.carbonRiskScore = carbonRiskScore;
    }

    public String getCarbonRiskLevel() {
        return carbonRiskLevel;
    }

    public void setCarbonRiskLevel(String carbonRiskLevel) {
        this.carbonRiskLevel = carbonRiskLevel;
    }

    public Double getMonthlyLeakageVolumeM3() {
        return monthlyLeakageVolumeM3;
    }

    public void setMonthlyLeakageVolumeM3(Double monthlyLeakageVolumeM3) {
        this.monthlyLeakageVolumeM3 = monthlyLeakageVolumeM3;
    }

    public Double getMonthlyCarbonIncrementKg() {
        return monthlyCarbonIncrementKg;
    }

    public void setMonthlyCarbonIncrementKg(Double monthlyCarbonIncrementKg) {
        this.monthlyCarbonIncrementKg = monthlyCarbonIncrementKg;
    }

    public Double getPriorityScore() {
        return priorityScore;
    }

    public void setPriorityScore(Double priorityScore) {
        this.priorityScore = priorityScore;
    }

    public String getTrend() {
        return trend;
    }

    public void setTrend(String trend) {
        this.trend = trend;
    }

    public List<String> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<String> recommendations) {
        this.recommendations = recommendations;
    }

}