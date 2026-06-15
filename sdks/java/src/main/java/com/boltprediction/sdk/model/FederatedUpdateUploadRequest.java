package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 上传模型更新请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedUpdateUploadRequest {

    @JsonProperty("client_id")
    private String clientId;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("round_id")
    private Integer roundId;

    @JsonProperty("weights")
    private Map<String, Object> weights;

    @JsonProperty("num_samples")
    private Integer numSamples;

    @JsonProperty("metrics")
    private Object metrics;

    @JsonProperty("encrypted")
    private Boolean encrypted;

    @JsonProperty("encrypted_update")
    private Object encryptedUpdate;

    @JsonProperty("update_type")
    private String updateType;

    public String getClientId() {
        return clientId;
    }

    public void setClientId(String clientId) {
        this.clientId = clientId;
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

    public Integer getRoundId() {
        return roundId;
    }

    public void setRoundId(Integer roundId) {
        this.roundId = roundId;
    }

    public Map<String, Object> getWeights() {
        return weights;
    }

    public void setWeights(Map<String, Object> weights) {
        this.weights = weights;
    }

    public Integer getNumSamples() {
        return numSamples;
    }

    public void setNumSamples(Integer numSamples) {
        this.numSamples = numSamples;
    }

    public Object getMetrics() {
        return metrics;
    }

    public void setMetrics(Object metrics) {
        this.metrics = metrics;
    }

    public Boolean getEncrypted() {
        return encrypted;
    }

    public void setEncrypted(Boolean encrypted) {
        this.encrypted = encrypted;
    }

    public Object getEncryptedUpdate() {
        return encryptedUpdate;
    }

    public void setEncryptedUpdate(Object encryptedUpdate) {
        this.encryptedUpdate = encryptedUpdate;
    }

    public String getUpdateType() {
        return updateType;
    }

    public void setUpdateType(String updateType) {
        this.updateType = updateType;
    }

}