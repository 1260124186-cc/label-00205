package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 指派工单请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderAssignRequest {

    @JsonProperty("assignee_id")
    private String assigneeId;

    @JsonProperty("assignee_name")
    private String assigneeName;

    @JsonProperty("assigner_id")
    private Object assignerId;

    @JsonProperty("assigner_name")
    private Object assignerName;

    public String getAssigneeId() {
        return assigneeId;
    }

    public void setAssigneeId(String assigneeId) {
        this.assigneeId = assigneeId;
    }

    public String getAssigneeName() {
        return assigneeName;
    }

    public void setAssigneeName(String assigneeName) {
        this.assigneeName = assigneeName;
    }

    public Object getAssignerId() {
        return assignerId;
    }

    public void setAssignerId(Object assignerId) {
        this.assignerId = assignerId;
    }

    public Object getAssignerName() {
        return assignerName;
    }

    public void setAssignerName(Object assignerName) {
        this.assignerName = assignerName;
    }

}