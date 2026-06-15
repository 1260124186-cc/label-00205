package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 审计记录响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AuditRecordResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("prediction_id")
    private String predictionId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("input_hash")
    private Object inputHash;

    @JsonProperty("model_version")
    private Object modelVersion;

    @JsonProperty("model_type")
    private Object modelType;

    @JsonProperty("feature_summary")
    private Object featureSummary;

    @JsonProperty("intermediate_results")
    private Object intermediateResults;

    @JsonProperty("final_decision")
    private Object finalDecision;

    @JsonProperty("strategy_version")
    private Object strategyVersion;

    @JsonProperty("strategy_type")
    private Object strategyType;

    @JsonProperty("explainability")
    private Object explainability;

    @JsonProperty("retention_years")
    private Integer retentionYears;

    @JsonProperty("expire_time")
    private Object expireTime;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getPredictionId() {
        return predictionId;
    }

    public void setPredictionId(String predictionId) {
        this.predictionId = predictionId;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public Object getInputHash() {
        return inputHash;
    }

    public void setInputHash(Object inputHash) {
        this.inputHash = inputHash;
    }

    public Object getModelVersion() {
        return modelVersion;
    }

    public void setModelVersion(Object modelVersion) {
        this.modelVersion = modelVersion;
    }

    public Object getModelType() {
        return modelType;
    }

    public void setModelType(Object modelType) {
        this.modelType = modelType;
    }

    public Object getFeatureSummary() {
        return featureSummary;
    }

    public void setFeatureSummary(Object featureSummary) {
        this.featureSummary = featureSummary;
    }

    public Object getIntermediateResults() {
        return intermediateResults;
    }

    public void setIntermediateResults(Object intermediateResults) {
        this.intermediateResults = intermediateResults;
    }

    public Object getFinalDecision() {
        return finalDecision;
    }

    public void setFinalDecision(Object finalDecision) {
        this.finalDecision = finalDecision;
    }

    public Object getStrategyVersion() {
        return strategyVersion;
    }

    public void setStrategyVersion(Object strategyVersion) {
        this.strategyVersion = strategyVersion;
    }

    public Object getStrategyType() {
        return strategyType;
    }

    public void setStrategyType(Object strategyType) {
        this.strategyType = strategyType;
    }

    public Object getExplainability() {
        return explainability;
    }

    public void setExplainability(Object explainability) {
        this.explainability = explainability;
    }

    public Integer getRetentionYears() {
        return retentionYears;
    }

    public void setRetentionYears(Integer retentionYears) {
        this.retentionYears = retentionYears;
    }

    public Object getExpireTime() {
        return expireTime;
    }

    public void setExpireTime(Object expireTime) {
        this.expireTime = expireTime;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

}