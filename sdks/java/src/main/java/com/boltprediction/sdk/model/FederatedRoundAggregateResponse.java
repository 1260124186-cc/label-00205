package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 聚合模型更新响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedRoundAggregateResponse {

    @JsonProperty("round_id")
    private Integer roundId;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("message")
    private String message;

    @JsonProperty("num_clients_aggregated")
    private Integer numClientsAggregated;

    @JsonProperty("version")
    private Object version;

    @JsonProperty("metrics")
    private Object metrics;

    @JsonProperty("aggregated_at")
    private OffsetDateTime aggregatedAt;

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

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Integer getNumClientsAggregated() {
        return numClientsAggregated;
    }

    public void setNumClientsAggregated(Integer numClientsAggregated) {
        this.numClientsAggregated = numClientsAggregated;
    }

    public Object getVersion() {
        return version;
    }

    public void setVersion(Object version) {
        this.version = version;
    }

    public Object getMetrics() {
        return metrics;
    }

    public void setMetrics(Object metrics) {
        this.metrics = metrics;
    }

    public OffsetDateTime getAggregatedAt() {
        return aggregatedAt;
    }

    public void setAggregatedAt(OffsetDateTime aggregatedAt) {
        this.aggregatedAt = aggregatedAt;
    }

}