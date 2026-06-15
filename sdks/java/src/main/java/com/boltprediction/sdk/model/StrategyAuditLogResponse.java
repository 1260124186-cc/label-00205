package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 策略审计日志响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StrategyAuditLogResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("config_id")
    private Integer configId;

    @JsonProperty("scope")
    private String scope;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("action")
    private String action;

    @JsonProperty("old_value")
    private Object oldValue;

    @JsonProperty("new_value")
    private Object newValue;

    @JsonProperty("version_before")
    private Object versionBefore;

    @JsonProperty("version_after")
    private Object versionAfter;

    @JsonProperty("change_summary")
    private Object changeSummary;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    @JsonProperty("create_time")
    private Object createTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public Integer getConfigId() {
        return configId;
    }

    public void setConfigId(Integer configId) {
        this.configId = configId;
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

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public Object getOldValue() {
        return oldValue;
    }

    public void setOldValue(Object oldValue) {
        this.oldValue = oldValue;
    }

    public Object getNewValue() {
        return newValue;
    }

    public void setNewValue(Object newValue) {
        this.newValue = newValue;
    }

    public Object getVersionBefore() {
        return versionBefore;
    }

    public void setVersionBefore(Object versionBefore) {
        this.versionBefore = versionBefore;
    }

    public Object getVersionAfter() {
        return versionAfter;
    }

    public void setVersionAfter(Object versionAfter) {
        this.versionAfter = versionAfter;
    }

    public Object getChangeSummary() {
        return changeSummary;
    }

    public void setChangeSummary(Object changeSummary) {
        this.changeSummary = changeSummary;
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

}