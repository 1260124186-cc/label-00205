package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 更新工单状态请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderStatusUpdateRequest {

    @JsonProperty("status")
    private String status;

    @JsonProperty("operator_id")
    private Object operatorId;

    @JsonProperty("operator_name")
    private Object operatorName;

    @JsonProperty("note")
    private Object note;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
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

    public Object getNote() {
        return note;
    }

    public void setNote(Object note) {
        this.note = note;
    }

}