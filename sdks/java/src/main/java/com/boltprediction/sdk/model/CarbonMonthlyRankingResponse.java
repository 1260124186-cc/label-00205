package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 装置级月度碳排风险排行响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CarbonMonthlyRankingResponse {

    @JsonProperty("report_month")
    private String reportMonth;

    @JsonProperty("total_nodes")
    private Integer totalNodes;

    @JsonProperty("total_monthly_carbon_increment_kg")
    private Double totalMonthlyCarbonIncrementKg;

    @JsonProperty("total_monthly_leakage_volume_m3")
    private Double totalMonthlyLeakageVolumeM3;

    @JsonProperty("risk_distribution")
    private Map<String, Integer> riskDistribution;

    @JsonProperty("ranked_items")
    private List<CarbonRiskItemSchema> rankedItems;

    @JsonProperty("generated_at")
    private OffsetDateTime generatedAt;

    public String getReportMonth() {
        return reportMonth;
    }

    public void setReportMonth(String reportMonth) {
        this.reportMonth = reportMonth;
    }

    public Integer getTotalNodes() {
        return totalNodes;
    }

    public void setTotalNodes(Integer totalNodes) {
        this.totalNodes = totalNodes;
    }

    public Double getTotalMonthlyCarbonIncrementKg() {
        return totalMonthlyCarbonIncrementKg;
    }

    public void setTotalMonthlyCarbonIncrementKg(Double totalMonthlyCarbonIncrementKg) {
        this.totalMonthlyCarbonIncrementKg = totalMonthlyCarbonIncrementKg;
    }

    public Double getTotalMonthlyLeakageVolumeM3() {
        return totalMonthlyLeakageVolumeM3;
    }

    public void setTotalMonthlyLeakageVolumeM3(Double totalMonthlyLeakageVolumeM3) {
        this.totalMonthlyLeakageVolumeM3 = totalMonthlyLeakageVolumeM3;
    }

    public Map<String, Integer> getRiskDistribution() {
        return riskDistribution;
    }

    public void setRiskDistribution(Map<String, Integer> riskDistribution) {
        this.riskDistribution = riskDistribution;
    }

    public List<CarbonRiskItemSchema> getRankedItems() {
        return rankedItems;
    }

    public void setRankedItems(List<CarbonRiskItemSchema> rankedItems) {
        this.rankedItems = rankedItems;
    }

    public OffsetDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(OffsetDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

}