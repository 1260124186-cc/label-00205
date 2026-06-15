package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** HI与碳排并列展示单项 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HiCarbonDualItemSchema {

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

    @JsonProperty("hi_trend")
    private String hiTrend;

    @JsonProperty("degradation_rate_per_month")
    private Double degradationRatePerMonth;

    @JsonProperty("estimated_leakage_rate_m3_hour")
    private Double estimatedLeakageRateM3Hour;

    @JsonProperty("monthly_carbon_increment_kg")
    private Double monthlyCarbonIncrementKg;

    @JsonProperty("carbon_risk_level")
    private String carbonRiskLevel;

    @JsonProperty("carbon_trend")
    private String carbonTrend;

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

    public String getHiTrend() {
        return hiTrend;
    }

    public void setHiTrend(String hiTrend) {
        this.hiTrend = hiTrend;
    }

    public Double getDegradationRatePerMonth() {
        return degradationRatePerMonth;
    }

    public void setDegradationRatePerMonth(Double degradationRatePerMonth) {
        this.degradationRatePerMonth = degradationRatePerMonth;
    }

    public Double getEstimatedLeakageRateM3Hour() {
        return estimatedLeakageRateM3Hour;
    }

    public void setEstimatedLeakageRateM3Hour(Double estimatedLeakageRateM3Hour) {
        this.estimatedLeakageRateM3Hour = estimatedLeakageRateM3Hour;
    }

    public Double getMonthlyCarbonIncrementKg() {
        return monthlyCarbonIncrementKg;
    }

    public void setMonthlyCarbonIncrementKg(Double monthlyCarbonIncrementKg) {
        this.monthlyCarbonIncrementKg = monthlyCarbonIncrementKg;
    }

    public String getCarbonRiskLevel() {
        return carbonRiskLevel;
    }

    public void setCarbonRiskLevel(String carbonRiskLevel) {
        this.carbonRiskLevel = carbonRiskLevel;
    }

    public String getCarbonTrend() {
        return carbonTrend;
    }

    public void setCarbonTrend(String carbonTrend) {
        this.carbonTrend = carbonTrend;
    }

}