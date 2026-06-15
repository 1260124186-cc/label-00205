package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RiskAssessExplainResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RiskAssessExplainResponse {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("risk_score")
    private Double riskScore;

    @JsonProperty("risk_level")
    private String riskLevel;

    @JsonProperty("probability_distribution")
    private RiskProbabilityDistributionSchema probabilityDistribution;

    @JsonProperty("factor_contributions")
    private List<FactorContributionSchema> factorContributions;

    @JsonProperty("base_value")
    private Double baseValue;

    @JsonProperty("total_contribution")
    private Double totalContribution;

    @JsonProperty("summary")
    private String summary;

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

    public RiskProbabilityDistributionSchema getProbabilityDistribution() {
        return probabilityDistribution;
    }

    public void setProbabilityDistribution(RiskProbabilityDistributionSchema probabilityDistribution) {
        this.probabilityDistribution = probabilityDistribution;
    }

    public List<FactorContributionSchema> getFactorContributions() {
        return factorContributions;
    }

    public void setFactorContributions(List<FactorContributionSchema> factorContributions) {
        this.factorContributions = factorContributions;
    }

    public Double getBaseValue() {
        return baseValue;
    }

    public void setBaseValue(Double baseValue) {
        this.baseValue = baseValue;
    }

    public Double getTotalContribution() {
        return totalContribution;
    }

    public void setTotalContribution(Double totalContribution) {
        this.totalContribution = totalContribution;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

}