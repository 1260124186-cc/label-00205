package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康度计算请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthIndexCalculateRequest {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("data")
    private Object data;

    @JsonProperty("working_condition")
    private Object workingCondition;

    @JsonProperty("include_history")
    private Boolean includeHistory;

    @JsonProperty("save_to_db")
    private Boolean saveToDb;

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public Object getData() {
        return data;
    }

    public void setData(Object data) {
        this.data = data;
    }

    public Object getWorkingCondition() {
        return workingCondition;
    }

    public void setWorkingCondition(Object workingCondition) {
        this.workingCondition = workingCondition;
    }

    public Boolean getIncludeHistory() {
        return includeHistory;
    }

    public void setIncludeHistory(Boolean includeHistory) {
        this.includeHistory = includeHistory;
    }

    public Boolean getSaveToDb() {
        return saveToDb;
    }

    public void setSaveToDb(Boolean saveToDb) {
        this.saveToDb = saveToDb;
    }

}