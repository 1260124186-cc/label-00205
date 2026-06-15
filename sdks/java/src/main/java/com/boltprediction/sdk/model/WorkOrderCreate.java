package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 创建工单请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderCreate {

    @JsonProperty("title")
    private String title;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("priority")
    private String priority;

    @JsonProperty("status")
    private Object status;

    @JsonProperty("node_type")
    private Object nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("alert_level")
    private Object alertLevel;

    @JsonProperty("risk_score")
    private Object riskScore;

    @JsonProperty("assignee_id")
    private Object assigneeId;

    @JsonProperty("assignee_name")
    private Object assigneeName;

    @JsonProperty("creator_id")
    private Object creatorId;

    @JsonProperty("creator_name")
    private Object creatorName;

    @JsonProperty("due_time")
    private Object dueTime;

    @JsonProperty("recommendations")
    private Object recommendations;

    @JsonProperty("extra_info")
    private Object extraInfo;

    @JsonProperty("due_hours")
    private Object dueHours;

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
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

    public Object getAlertLevel() {
        return alertLevel;
    }

    public void setAlertLevel(Object alertLevel) {
        this.alertLevel = alertLevel;
    }

    public Object getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Object riskScore) {
        this.riskScore = riskScore;
    }

    public Object getAssigneeId() {
        return assigneeId;
    }

    public void setAssigneeId(Object assigneeId) {
        this.assigneeId = assigneeId;
    }

    public Object getAssigneeName() {
        return assigneeName;
    }

    public void setAssigneeName(Object assigneeName) {
        this.assigneeName = assigneeName;
    }

    public Object getCreatorId() {
        return creatorId;
    }

    public void setCreatorId(Object creatorId) {
        this.creatorId = creatorId;
    }

    public Object getCreatorName() {
        return creatorName;
    }

    public void setCreatorName(Object creatorName) {
        this.creatorName = creatorName;
    }

    public Object getDueTime() {
        return dueTime;
    }

    public void setDueTime(Object dueTime) {
        this.dueTime = dueTime;
    }

    public Object getRecommendations() {
        return recommendations;
    }

    public void setRecommendations(Object recommendations) {
        this.recommendations = recommendations;
    }

    public Object getExtraInfo() {
        return extraInfo;
    }

    public void setExtraInfo(Object extraInfo) {
        this.extraInfo = extraInfo;
    }

    public Object getDueHours() {
        return dueHours;
    }

    public void setDueHours(Object dueHours) {
        this.dueHours = dueHours;
    }

}