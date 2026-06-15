package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 周期报告响应（周报/月报） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PeriodicReportResponse {

    @JsonProperty("report_type")
    private String reportType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("period_start")
    private OffsetDateTime periodStart;

    @JsonProperty("period_end")
    private OffsetDateTime periodEnd;

    @JsonProperty("diagnosis_summary")
    private String diagnosisSummary;

    @JsonProperty("recommended_actions")
    private List<String> recommendedActions;

    @JsonProperty("urgency_level")
    private String urgencyLevel;

    @JsonProperty("statistics")
    private ReportStatisticsSchema statistics;

    @JsonProperty("generated_at")
    private OffsetDateTime generatedAt;

    @JsonProperty("model")
    private String model;

    @JsonProperty("is_fallback")
    private Boolean isFallback;

    public String getReportType() {
        return reportType;
    }

    public void setReportType(String reportType) {
        this.reportType = reportType;
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

    public OffsetDateTime getPeriodStart() {
        return periodStart;
    }

    public void setPeriodStart(OffsetDateTime periodStart) {
        this.periodStart = periodStart;
    }

    public OffsetDateTime getPeriodEnd() {
        return periodEnd;
    }

    public void setPeriodEnd(OffsetDateTime periodEnd) {
        this.periodEnd = periodEnd;
    }

    public String getDiagnosisSummary() {
        return diagnosisSummary;
    }

    public void setDiagnosisSummary(String diagnosisSummary) {
        this.diagnosisSummary = diagnosisSummary;
    }

    public List<String> getRecommendedActions() {
        return recommendedActions;
    }

    public void setRecommendedActions(List<String> recommendedActions) {
        this.recommendedActions = recommendedActions;
    }

    public String getUrgencyLevel() {
        return urgencyLevel;
    }

    public void setUrgencyLevel(String urgencyLevel) {
        this.urgencyLevel = urgencyLevel;
    }

    public ReportStatisticsSchema getStatistics() {
        return statistics;
    }

    public void setStatistics(ReportStatisticsSchema statistics) {
        this.statistics = statistics;
    }

    public OffsetDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(OffsetDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public Boolean getIsFallback() {
        return isFallback;
    }

    public void setIsFallback(Boolean isFallback) {
        this.isFallback = isFallback;
    }

}