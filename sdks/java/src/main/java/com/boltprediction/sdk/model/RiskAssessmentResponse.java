package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 风险评估响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RiskAssessmentResponse {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("risk_score")
    private Double riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("factors")
    private List<String> factors;

    @JsonProperty("diagnosis")
    private String diagnosis;

    @JsonProperty("recommendations")
    private List<String> recommendations;

    @JsonProperty("confidence")
    private Double confidence;

    @JsonProperty("probability_distribution")
    private Object probabilityDistribution;

    @JsonProperty("factor_contributions")
    private Object factorContributions;

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

    public List<String> getFactors() {
        return factors;
    }

    public void setFactors(List<String> factors) {
        this.factors = factors;
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

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public Object getProbabilityDistribution() {
        return probabilityDistribution;
    }

    public void setProbabilityDistribution(Object probabilityDistribution) {
        this.probabilityDistribution = probabilityDistribution;
    }

    public Object getFactorContributions() {
        return factorContributions;
    }

    public void setFactorContributions(Object factorContributions) {
        this.factorContributions = factorContributions;
    }

}