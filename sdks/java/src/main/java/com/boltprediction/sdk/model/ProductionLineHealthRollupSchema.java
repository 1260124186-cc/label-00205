package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 产线/装置级健康度汇总报表 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ProductionLineHealthRollupSchema {

    @JsonProperty("line_id")
    private String lineId;

    @JsonProperty("line_name")
    private String lineName;

    @JsonProperty("line_type")
    private String lineType;

    @JsonProperty("overall_hi")
    private Double overallHi;

    @JsonProperty("overall_level")
    private String overallLevel;

    @JsonProperty("total_flange_count")
    private Integer totalFlangeCount;

    @JsonProperty("total_bolt_count")
    private Integer totalBoltCount;

    @JsonProperty("healthy_flange_count")
    private Integer healthyFlangeCount;

    @JsonProperty("warning_flange_count")
    private Integer warningFlangeCount;

    @JsonProperty("critical_flange_count")
    private Integer criticalFlangeCount;

    @JsonProperty("healthy_bolt_count")
    private Integer healthyBoltCount;

    @JsonProperty("warning_bolt_count")
    private Integer warningBoltCount;

    @JsonProperty("critical_bolt_count")
    private Integer criticalBoltCount;

    @JsonProperty("worst_flange_hi")
    private Double worstFlangeHi;

    @JsonProperty("worst_flange_id")
    private String worstFlangeId;

    @JsonProperty("average_degradation_rate")
    private Double averageDegradationRate;

    @JsonProperty("flanges_health")
    private List<FlangeHealthIndexSchema> flangesHealth;

    @JsonProperty("risk_summary")
    private Map<String, Object> riskSummary;

    @JsonProperty("maintenance_priorities")
    private List<Map<String, Object>> maintenancePriorities;

    @JsonProperty("report_date")
    private OffsetDateTime reportDate;

    @JsonProperty("generate_time")
    private OffsetDateTime generateTime;

    public String getLineId() {
        return lineId;
    }

    public void setLineId(String lineId) {
        this.lineId = lineId;
    }

    public String getLineName() {
        return lineName;
    }

    public void setLineName(String lineName) {
        this.lineName = lineName;
    }

    public String getLineType() {
        return lineType;
    }

    public void setLineType(String lineType) {
        this.lineType = lineType;
    }

    public Double getOverallHi() {
        return overallHi;
    }

    public void setOverallHi(Double overallHi) {
        this.overallHi = overallHi;
    }

    public String getOverallLevel() {
        return overallLevel;
    }

    public void setOverallLevel(String overallLevel) {
        this.overallLevel = overallLevel;
    }

    public Integer getTotalFlangeCount() {
        return totalFlangeCount;
    }

    public void setTotalFlangeCount(Integer totalFlangeCount) {
        this.totalFlangeCount = totalFlangeCount;
    }

    public Integer getTotalBoltCount() {
        return totalBoltCount;
    }

    public void setTotalBoltCount(Integer totalBoltCount) {
        this.totalBoltCount = totalBoltCount;
    }

    public Integer getHealthyFlangeCount() {
        return healthyFlangeCount;
    }

    public void setHealthyFlangeCount(Integer healthyFlangeCount) {
        this.healthyFlangeCount = healthyFlangeCount;
    }

    public Integer getWarningFlangeCount() {
        return warningFlangeCount;
    }

    public void setWarningFlangeCount(Integer warningFlangeCount) {
        this.warningFlangeCount = warningFlangeCount;
    }

    public Integer getCriticalFlangeCount() {
        return criticalFlangeCount;
    }

    public void setCriticalFlangeCount(Integer criticalFlangeCount) {
        this.criticalFlangeCount = criticalFlangeCount;
    }

    public Integer getHealthyBoltCount() {
        return healthyBoltCount;
    }

    public void setHealthyBoltCount(Integer healthyBoltCount) {
        this.healthyBoltCount = healthyBoltCount;
    }

    public Integer getWarningBoltCount() {
        return warningBoltCount;
    }

    public void setWarningBoltCount(Integer warningBoltCount) {
        this.warningBoltCount = warningBoltCount;
    }

    public Integer getCriticalBoltCount() {
        return criticalBoltCount;
    }

    public void setCriticalBoltCount(Integer criticalBoltCount) {
        this.criticalBoltCount = criticalBoltCount;
    }

    public Double getWorstFlangeHi() {
        return worstFlangeHi;
    }

    public void setWorstFlangeHi(Double worstFlangeHi) {
        this.worstFlangeHi = worstFlangeHi;
    }

    public String getWorstFlangeId() {
        return worstFlangeId;
    }

    public void setWorstFlangeId(String worstFlangeId) {
        this.worstFlangeId = worstFlangeId;
    }

    public Double getAverageDegradationRate() {
        return averageDegradationRate;
    }

    public void setAverageDegradationRate(Double averageDegradationRate) {
        this.averageDegradationRate = averageDegradationRate;
    }

    public List<FlangeHealthIndexSchema> getFlangesHealth() {
        return flangesHealth;
    }

    public void setFlangesHealth(List<FlangeHealthIndexSchema> flangesHealth) {
        this.flangesHealth = flangesHealth;
    }

    public Map<String, Object> getRiskSummary() {
        return riskSummary;
    }

    public void setRiskSummary(Map<String, Object> riskSummary) {
        this.riskSummary = riskSummary;
    }

    public List<Map<String, Object>> getMaintenancePriorities() {
        return maintenancePriorities;
    }

    public void setMaintenancePriorities(List<Map<String, Object>> maintenancePriorities) {
        this.maintenancePriorities = maintenancePriorities;
    }

    public OffsetDateTime getReportDate() {
        return reportDate;
    }

    public void setReportDate(OffsetDateTime reportDate) {
        this.reportDate = reportDate;
    }

    public OffsetDateTime getGenerateTime() {
        return generateTime;
    }

    public void setGenerateTime(OffsetDateTime generateTime) {
        this.generateTime = generateTime;
    }

}