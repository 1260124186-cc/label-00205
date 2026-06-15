package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 单条策略配置响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StrategyConfigItemResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("scope")
    private String scope;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("strategy_type")
    private Integer strategyType;

    @JsonProperty("confidence_threshold")
    private Double confidenceThreshold;

    @JsonProperty("false_positive_threshold")
    private Object falsePositiveThreshold;

    @JsonProperty("false_negative_threshold")
    private Object falseNegativeThreshold;

    @JsonProperty("version")
    private Integer version;

    @JsonProperty("is_active")
    private Boolean isActive;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    @JsonProperty("create_time")
    private Object createTime;

    @JsonProperty("update_time")
    private Object updateTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

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

    public Double getConfidenceThreshold() {
        return confidenceThreshold;
    }

    public void setConfidenceThreshold(Double confidenceThreshold) {
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

    public Integer getVersion() {
        return version;
    }

    public void setVersion(Integer version) {
        this.version = version;
    }

    public Boolean getIsActive() {
        return isActive;
    }

    public void setIsActive(Boolean isActive) {
        this.isActive = isActive;
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

    public Object getCreateTime() {
        return createTime;
    }

    public void setCreateTime(Object createTime) {
        this.createTime = createTime;
    }

    public Object getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(Object updateTime) {
        this.updateTime = updateTime;
    }

}