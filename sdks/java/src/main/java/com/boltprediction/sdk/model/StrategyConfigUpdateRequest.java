package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 预警策略动态配置更新请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StrategyConfigUpdateRequest {

    @JsonProperty("scope")
    private String scope;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("strategy_type")
    private Integer strategyType;

    @JsonProperty("confidence_threshold")
    private Object confidenceThreshold;

    @JsonProperty("false_positive_threshold")
    private Object falsePositiveThreshold;

    @JsonProperty("false_negative_threshold")
    private Object falseNegativeThreshold;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    public String getScope() {
        return scope;
    }

    public void setScope(String scope) {
        this.scope = scope;
    }

    public Object getNodeType() {
        return nodeType;
    }

    public void setNodeType(Object nodeType) {
        this.nodeType = nodeType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
    }

    public Integer getStrategyType() {
        return strategyType;
    }

    public void setStrategyType(Integer strategyType) {
        this.strategyType = strategyType;
    }

    public Object getConfidenceThreshold() {
        return confidenceThreshold;
    }

    public void setConfidenceThreshold(Object confidenceThreshold) {
        this.confidenceThreshold = confidenceThreshold;
    }

    public Object getFalsePositiveThreshold() {
        return falsePositiveThreshold;
    }

    public void setFalsePositiveThreshold(Object falsePositiveThreshold) {
        this.falsePositiveThreshold = falsePositiveThreshold;
    }

    public Object getFalseNegativeThreshold() {
        return falseNegativeThreshold;
    }

    public void setFalseNegativeThreshold(Object falseNegativeThreshold) {
        this.falseNegativeThreshold = falseNegativeThreshold;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

    public Object getOperatorId() {
        return operatorId;
    }

    public void setOperatorId(Object operatorId) {
        this.operatorId = operatorId;
    }

    public Object getOperatorName() {
        return operatorName;
    }

    public void setOperatorName(Object operatorName) {
        this.operatorName = operatorName;
    }

}