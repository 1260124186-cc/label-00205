package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 可解释性报告响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ExplainabilityReportResponse {

    @JsonProperty("prediction_id")
    private String predictionId;

    @JsonProperty("attention_weights")
    private Object attentionWeights;

    @JsonProperty("key_timesteps")
    private Object keyTimesteps;

    @JsonProperty("risk_factor_decomposition")
    private Object riskFactorDecomposition;

    @JsonProperty("rule_hits")
    private Object ruleHits;

    @JsonProperty("strategy_adjustment")
    private Object strategyAdjustment;

    public String getPredictionId() {
        return predictionId;
    }

    public void setPredictionId(String predictionId) {
        this.predictionId = predictionId;
    }

    public Object getAttentionWeights() {
        return attentionWeights;
    }

    public void setAttentionWeights(Object attentionWeights) {
        this.attentionWeights = attentionWeights;
    }

    public Object getKeyTimesteps() {
        return keyTimesteps;
    }

    public void setKeyTimesteps(Object keyTimesteps) {
        this.keyTimesteps = keyTimesteps;
    }

    public Object getRiskFactorDecomposition() {
        return riskFactorDecomposition;
    }

    public void setRiskFactorDecomposition(Object riskFactorDecomposition) {
        this.riskFactorDecomposition = riskFactorDecomposition;
    }

    public Object getRuleHits() {
        return ruleHits;
    }

    public void setRuleHits(Object ruleHits) {
        this.ruleHits = ruleHits;
    }

    public Object getStrategyAdjustment() {
        return strategyAdjustment;
    }

    public void setStrategyAdjustment(Object strategyAdjustment) {
        this.strategyAdjustment = strategyAdjustment;
    }

}