package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** ESG报表片段响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EsgReportFragmentResponse {

    @JsonProperty("report_period")
    private String reportPeriod;

    @JsonProperty("generated_at")
    private OffsetDateTime generatedAt;

    @JsonProperty("summary")
    private EsgReportSummarySchema summary;

    @JsonProperty("top_risk_items")
    private List<CarbonRiskItemSchema> topRiskItems;

    @JsonProperty("trend_analysis")
    private EsgTrendAnalysisSchema trendAnalysis;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    @JsonProperty("methodology_note")
    private Object methodologyNote;

    @JsonProperty("csv_content")
    private Object csvContent;

    public String getReportPeriod() {
        return reportPeriod;
    }

    public void setReportPeriod(String reportPeriod) {
        this.reportPeriod = reportPeriod;
    }

    public OffsetDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(OffsetDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

    public EsgReportSummarySchema getSummary() {
        return summary;
    }

    public void setSummary(EsgReportSummarySchema summary) {
        this.summary = summary;
    }

    public List<CarbonRiskItemSchema> getTopRiskItems() {
        return topRiskItems;
    }

    public void setTopRiskItems(List<CarbonRiskItemSchema> topRiskItems) {
        this.topRiskItems = topRiskItems;
    }

    public EsgTrendAnalysisSchema getTrendAnalysis() {
        return trendAnalysis;
    }

    public void setTrendAnalysis(EsgTrendAnalysisSchema trendAnalysis) {
        this.trendAnalysis = trendAnalysis;
    }

    public List<String> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<String> recommendations) {
        this.recommendations = recommendations;
    }

    public Object getMethodologyNote() {
        return methodologyNote;
    }

    public void setMethodologyNote(Object methodologyNote) {
        this.methodologyNote = methodologyNote;
    }

    public Object getCsvContent() {
        return csvContent;
    }

    public void setCsvContent(Object csvContent) {
        this.csvContent = csvContent;
    }

}