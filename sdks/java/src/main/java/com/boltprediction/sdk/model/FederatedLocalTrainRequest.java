package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 本地训练请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedLocalTrainRequest {

    @JsonProperty("client_id")
    private String clientId;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("local_epochs")
    private Object localEpochs;

    @JsonProperty("fine_tune")
    private Boolean fineTune;

    @JsonProperty("train_data")
    private Object trainData;

    @JsonProperty("train_labels")
    private Object trainLabels;

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

    public Object getLocalEpochs() {
        return localEpochs;
    }

    public void setLocalEpochs(Object localEpochs) {
        this.localEpochs = localEpochs;
    }

    public Boolean getFineTune() {
        return fineTune;
    }

    public void setFineTune(Boolean fineTune) {
        this.fineTune = fineTune;
    }

    public Object getTrainData() {
        return trainData;
    }

    public void setTrainData(Object trainData) {
        this.trainData = trainData;
    }

    public Object getTrainLabels() {
        return trainLabels;
    }

    public void setTrainLabels(Object trainLabels) {
        this.trainLabels = trainLabels;
    }

}