package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 法兰面预测响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FlangePredictionResponse {

    @JsonProperty("flange_id")
    private String flangeId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("status_code")
    private Integer statusCode;

    @JsonProperty("confidence")
    private Double confidence;

    @JsonProperty("risk_score")
    private Double riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("bolt_count")
    private Integer boltCount;

    @JsonProperty("attention_weights")
    private Object attentionWeights;

    @JsonProperty("diagnosis")
    private String diagnosis;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    @JsonProperty("prediction_time")
    private OffsetDateTime predictionTime;

    @JsonProperty("correlation_matrix")
    private Object correlationMatrix;

    @JsonProperty("causal_graph")
    private Object causalGraph;

    @JsonProperty("leading_bolts")
    private Object leadingBolts;

    @JsonProperty("propagation_paths")
    private Object propagationPaths;

    @JsonProperty("root_cause_analysis")
    private Object rootCauseAnalysis;

    @JsonProperty("root_cause_measures")
    private Object rootCauseMeasures;

    @JsonProperty("model_version")
    private Object modelVersion;

    @JsonProperty("shadow_version")
    private Object shadowVersion;

    @JsonProperty("shadow_result")
    private Object shadowResult;

    @JsonProperty("fault_detail")
    private Object faultDetail;

    public String getFlangeId() {
        return flangeId;
    }

    public void setFlangeId(String flangeId) {
        this.flangeId = flangeId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Integer getStatusCode() {
        return statusCode;
    }

    public void setStatusCode(Integer statusCode) {
        this.statusCode = statusCode;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public Double getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Double riskScore) {
        this.riskScore = riskScore;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public void setRiskLevel(String riskLevel) {
        this.riskLevel = riskLevel;
    }

    public Integer getBoltCount() {
        return boltCount;
    }

    public void setBoltCount(Integer boltCount) {
        this.boltCount = boltCount;
    }

    public Object getAttentionWeights() {
        return attentionWeights;
    }

    public void setAttentionWeights(Object attentionWeights) {
        this.attentionWeights = attentionWeights;
    }

    public String getDiagnosis() {
        return diagnosis;
    }

    public void setDiagnosis(String diagnosis) {
        this.diagnosis = diagnosis;
    }

    public List<String> getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(List<String> recommendations) {
        this.recommendations = recommendations;
    }

    public OffsetDateTime getPredictionTime() {
        return predictionTime;
    }

    public void setPredictionTime(OffsetDateTime predictionTime) {
        this.predictionTime = predictionTime;
    }

    public Object getCorrelationMatrix() {
        return correlationMatrix;
    }

    public void setCorrelationMatrix(Object correlationMatrix) {
        this.correlationMatrix = correlationMatrix;
    }

    public Object getCausalGraph() {
        return causalGraph;
    }

    public void setCausalGraph(Object causalGraph) {
        this.causalGraph = causalGraph;
    }

    public Object getLeadingBolts() {
        return leadingBolts;
    }

    public void setLeadingBolts(Object leadingBolts) {
        this.leadingBolts = leadingBolts;
    }

    public Object getPropagationPaths() {
        return propagationPaths;
    }

    public void setPropagationPaths(Object propagationPaths) {
        this.propagationPaths = propagationPaths;
    }

    public Object getRootCauseAnalysis() {
        return rootCauseAnalysis;
    }

    public void setRootCauseAnalysis(Object rootCauseAnalysis) {
        this.rootCauseAnalysis = rootCauseAnalysis;
    }

    public Object getRootCauseMeasures() {
        return rootCauseMeasures;
    }

    public void setRootCauseMeasures(Object rootCauseMeasures) {
        this.rootCauseMeasures = rootCauseMeasures;
    }

    public Object getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(Object modelVersion) {
        this.modelVersion = modelVersion;
    }

    public Object getShadowVersion() {
        return shadowVersion;
    }

    public void setShadowVersion(Object shadowVersion) {
        this.shadowVersion = shadowVersion;
    }

    public Object getShadowResult() {
        return shadowResult;
    }

    public void setShadowResult(Object shadowResult) {
        this.shadowResult = shadowResult;
    }

    public Object getFaultDetail() {
        return faultDetail;
    }

    public void setFaultDetail(Object faultDetail) {
        this.faultDetail = faultDetail;
    }

}