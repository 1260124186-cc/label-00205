package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RUL预测响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RulPredictionResponse {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("rul_data")
    private RulPredictionSchema rulData;

    @JsonProperty("calculate_time")
    private OffsetDateTime calculateTime;

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

    public RulPredictionSchema getRulData() {
        return rulData;
    }

    public void setRulData(RulPredictionSchema rulData) {
        this.rulData = rulData;
    }

    public OffsetDateTime getCalculateTime() {
        return calculateTime;
    }

    public void setCalculateTime(OffsetDateTime calculateTime) {
        this.calculateTime = calculateTime;
    }

}