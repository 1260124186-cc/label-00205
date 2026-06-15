package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 告警事件响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertEventResponse {

    @JsonProperty("id")
    private Integer id;

    @JsonProperty("alert_no")
    private String alertNo;

    @JsonProperty("rule_id")
    private Object ruleId;

    @JsonProperty("alert_level")
    private Integer alertLevel;

    @JsonProperty("original_level")
    private Object originalLevel;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("title")
    private Object title;

    @JsonProperty("content")
    private Object content;

    @JsonProperty("confidence")
    private Object confidence;

    @JsonProperty("risk_score")
    private Object riskScore;

    @JsonProperty("recommendations")
    private Object recommendations;

    @JsonProperty("status")
    private String status;

    @JsonProperty("handler_id")
    private Object handlerId;

    @JsonProperty("handler_name")
    private Object handlerName;

    @JsonProperty("handle_time")
    private Object handleTime;

    @JsonProperty("handle_note")
    private Object handleNote;

    @JsonProperty("is_upgraded")
    private Boolean isUpgraded;

    @JsonProperty("upgrade_count")
    private Integer upgradeCount;

    @JsonProperty("last_upgrade_time")
    private Object lastUpgradeTime;

    @JsonProperty("work_order_id")
    private Object workOrderId;

    @JsonProperty("source_prediction_id")
    private Object sourcePredictionId;

    @JsonProperty("silence_until")
    private Object silenceUntil;

    @JsonProperty("create_time")
    private OffsetDateTime createTime;

    @JsonProperty("update_time")
    private OffsetDateTime updateTime;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getAlertNo() {
        return alertNo;
    }

    public void setAlertNo(String alertNo) {
        this.alertNo = alertNo;
    }

    public Object getRuleId() {
        return ruleId;
    }

    public void setRuleId(Object ruleId) {
        this.ruleId = ruleId;
    }

    public Integer getAlertLevel() {
        return alertLevel;
    }

    public void setAlertLevel(Integer alertLevel) {
        this.alertLevel = alertLevel;
    }

    public Object getOriginalLevel() {
        return originalLevel;
    }

    public void setOriginalLevel(Object originalLevel) {
        this.originalLevel = originalLevel;
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

    public Object getTitle() {
        return title;
    }

    public void setTitle(Object title) {
        this.title = title;
    }

    public Object getContent() {
        return content;
    }

    public void setContent(Object content) {
        this.content = content;
    }

    public Object getConfidence() {
        return confidence;
    }

    public void setConfidence(Object confidence) {
        this.confidence = confidence;
    }

    public Object getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Object riskScore) {
        this.riskScore = riskScore;
    }

    public Object getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(Object recommendations) {
        this.recommendations = recommendations;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Object getHandlerId() {
        return handlerId;
    }

    public void setHandlerId(Object handlerId) {
        this.handlerId = handlerId;
    }

    public Object getHandlerName() {
        return handlerName;
    }

    public void setHandlerName(Object handlerName) {
        this.handlerName = handlerName;
    }

    public Object getHandleTime() {
        return handleTime;
    }

    public void setHandleTime(Object handleTime) {
        this.handleTime = handleTime;
    }

    public Object getHandleNote() {
        return handleNote;
    }

    public void setHandleNote(Object handleNote) {
        this.handleNote = handleNote;
    }

    public Boolean getIsUpgraded() {
        return isUpgraded;
    }

    public void setIsUpgraded(Boolean isUpgraded) {
        this.isUpgraded = isUpgraded;
    }

    public Integer getUpgradeCount() {
        return upgradeCount;
    }

    public void setUpgradeCount(Integer upgradeCount) {
        this.upgradeCount = upgradeCount;
    }

    public Object getLastUpgradeTime() {
        return lastUpgradeTime;
    }

    public void setLastUpgradeTime(Object lastUpgradeTime) {
        this.lastUpgradeTime = lastUpgradeTime;
    }

    public Object getWorkOrderId() {
        return workOrderId;
    }

    public void setWorkOrderId(Object workOrderId) {
        this.workOrderId = workOrderId;
    }

    public Object getSourcePredictionId() {
        return sourcePredictionId;
    }

    public void setSourcePredictionId(Object sourcePredictionId) {
        this.sourcePredictionId = sourcePredictionId;
    }

    public Object getSilenceUntil() {
        return silenceUntil;
    }

    public void setSilenceUntil(Object silenceUntil) {
        this.silenceUntil = silenceUntil;
    }

    public OffsetDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(OffsetDateTime createTime) {
        this.createTime = createTime;
    }

    public OffsetDateTime getUpdateTime() {
        return updateTime;
    }

    public void setUpdateTime(OffsetDateTime updateTime) {
        this.updateTime = updateTime;
    }

}