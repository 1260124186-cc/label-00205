package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 开始联邦学习轮次响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedRoundStartResponse {

    @JsonProperty("round_id")
    private Integer roundId;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("expected_clients")
    private List<String> expectedClients;

    @JsonProperty("started_at")
    private OffsetDateTime startedAt;

    public Integer getRoundId() {
        return roundId;
    }

    public void setRoundId(Integer roundId) {
        this.roundId = roundId;
    }

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public List<String> getExpectedClients() {
        return expectedClients;
    }

    public void setExpectedClients(List<String> expectedClients) {
        this.expectedClients = expectedClients;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime startedAt) {
        this.startedAt = startedAt;
    }

}