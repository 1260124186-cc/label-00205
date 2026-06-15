package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** ESG报表汇总数据 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EsgReportSummarySchema {

    @JsonProperty("reporting_period")
    private String reportingPeriod;

    @JsonProperty("total_devices_analyzed")
    private Integer totalDevicesAnalyzed;

    @JsonProperty("estimated_monthly_carbon_increment_kg")
    private Double estimatedMonthlyCarbonIncrementKg;

    @JsonProperty("estimated_monthly_carbon_increment_tons")
    private Double estimatedMonthlyCarbonIncrementTons;

    @JsonProperty("estimated_monthly_leakage_m3")
    private Double estimatedMonthlyLeakageM3;

    @JsonProperty("average_carbon_per_device_kg")
    private Double averageCarbonPerDeviceKg;

    @JsonProperty("carbon_risk_severity")
    private String carbonRiskSeverity;

    @JsonProperty("top5_contribution_ratio")
    private Double top5ContributionRatio;

    @JsonProperty("risk_distribution")
    private Map<String, Integer> riskDistribution;

    public String getReportingPeriod() {
        return reportingPeriod;
    }

    public void setReportingPeriod(String reportingPeriod) {
        this.reportingPeriod = reportingPeriod;
    }

    public Integer getTotalDevicesAnalyzed() {
        return totalDevicesAnalyzed;
    }

    public void setTotalDevicesAnalyzed(Integer totalDevicesAnalyzed) {
        this.totalDevicesAnalyzed = totalDevicesAnalyzed;
    }

    public Double getEstimatedMonthlyCarbonIncrementKg() {
        return estimatedMonthlyCarbonIncrementKg;
    }

    public void setEstimatedMonthlyCarbonIncrementKg(Double estimatedMonthlyCarbonIncrementKg) {
        this.estimatedMonthlyCarbonIncrementKg = estimatedMonthlyCarbonIncrementKg;
    }

    public Double getEstimatedMonthlyCarbonIncrementTons() {
        return estimatedMonthlyCarbonIncrementTons;
    }

    public void setEstimatedMonthlyCarbonIncrementTons(Double estimatedMonthlyCarbonIncrementTons) {
        this.estimatedMonthlyCarbonIncrementTons = estimatedMonthlyCarbonIncrementTons;
    }

    public Double getEstimatedMonthlyLeakageM3() {
        return estimatedMonthlyLeakageM3;
    }

    public void setEstimatedMonthlyLeakageM3(Double estimatedMonthlyLeakageM3) {
        this.estimatedMonthlyLeakageM3 = estimatedMonthlyLeakageM3;
    }

    public Double getAverageCarbonPerDeviceKg() {
        return averageCarbonPerDeviceKg;
    }

    public void setAverageCarbonPerDeviceKg(Double averageCarbonPerDeviceKg) {
        this.averageCarbonPerDeviceKg = averageCarbonPerDeviceKg;
    }

    public String getCarbonRiskSeverity() {
        return carbonRiskSeverity;
    }

    public void setCarbonRiskSeverity(String carbonRiskSeverity) {
        this.carbonRiskSeverity = carbonRiskSeverity;
    }

    public Double getTop5ContributionRatio() {
        return top5ContributionRatio;
    }

    public void setTop5ContributionRatio(Double top5ContributionRatio) {
        this.top5ContributionRatio = top5ContributionRatio;
    }

    public Map<String, Integer> getRiskDistribution() {
        return riskDistribution;
    }

    public void setRiskDistribution(Map<String, Integer> riskDistribution) {
        this.riskDistribution = riskDistribution;
    }

}