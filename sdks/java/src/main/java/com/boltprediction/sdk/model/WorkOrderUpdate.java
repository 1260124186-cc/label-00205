package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新工单请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderUpdate {

    @JsonProperty("title")
    private Object title;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("priority")
    private Object priority;

    @JsonProperty("status")
    private Object status;

    @JsonProperty("assignee_id")
    private Object assigneeId;

    @JsonProperty("assignee_name")
    private Object assigneeName;

    @JsonProperty("due_time")
    private Object dueTime;

    @JsonProperty("recommendations")
    private Object recommendations;

    @JsonProperty("extra_info")
    private Object extraInfo;

    public Object getTitle() {
        return title;
    }

    public void setTitle(Object title) {
        this.title = title;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

    public Object getPriority() {
        return priority;
    }

    public void setPriority(Object priority) {
        this.priority = priority;
    }

    public Object getStatus() {
        return status;
    }

    public void setStatus(Object status) {
        this.status = status;
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

}