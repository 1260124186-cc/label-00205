package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 获取全局模型响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedGlobalModelResponse {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("round_id")
    private Integer roundId;

    @JsonProperty("version")
    private Object version;

    @JsonProperty("weights")
    private Map<String, Object> weights;

    @JsonProperty("server_time")
    private OffsetDateTime serverTime;

    @JsonProperty("enable_two_level_arch")
    private Boolean enableTwoLevelArch;

    @JsonProperty("metrics")
    private Object metrics;

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

    public Integer getRoundId() {
        return roundId;
    }

    public void setRoundId(Integer roundId) {
        this.roundId = roundId;
    }

    public Object getVersion() {
        return version;
    }

    public void setVersion(Object version) {
        this.version = version;
    }

    public Map<String, Object> getWeights() {
        return weights;
    }

    public void setWeights(Map<String, Object> weights) {
        this.weights = weights;
    }

    public OffsetDateTime getServerTime() {
        return serverTime;
    }

    public void setServerTime(OffsetDateTime serverTime) {
        this.serverTime = serverTime;
    }

    public Boolean getEnableTwoLevelArch() {
        return enableTwoLevelArch;
    }

    public void setEnableTwoLevelArch(Boolean enableTwoLevelArch) {
        this.enableTwoLevelArch = enableTwoLevelArch;
    }

    public Object getMetrics() {
        return metrics;
    }

    public void setMetrics(Object metrics) {
        this.metrics = metrics;
    }

}