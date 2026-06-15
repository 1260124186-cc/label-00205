package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 批量健康度计算请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthIndexBatchCalculateRequest {

    @JsonProperty("nodes")
    private List<Map<String, Object>> nodes;

    @JsonProperty("working_condition")
    private Object workingCondition;

    @JsonProperty("save_to_db")
    private Boolean saveToDb;

    public List<Map<String, Object>> getNodes() {
        return nodes;
    }

    public void setNodes(List<Map<String, Object>> nodes) {
        this.nodes = nodes;
    }

    public Object getWorkingCondition() {
        return workingCondition;
    }

    public void setWorkingCondition(Object workingCondition) {
        this.workingCondition = workingCondition;
    }

    public Boolean getSaveToDb() {
        return saveToDb;
    }

    public void setSaveToDb(Boolean saveToDb) {
        this.saveToDb = saveToDb;
    }

}