package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 客户端状态响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FederatedClientStatusResponse {

    @JsonProperty("client_id")
    private String clientId;

    @JsonProperty("factory_id")
    private String factoryId;

    @JsonProperty("model_type")
    private Object modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("current_round")
    private Integer currentRound;

    @JsonProperty("has_global_model")
    private Boolean hasGlobalModel;

    @JsonProperty("has_local_model")
    private Boolean hasLocalModel;

    @JsonProperty("training_count")
    private Integer trainingCount;

    @JsonProperty("privacy_mechanism")
    private String privacyMechanism;

    @JsonProperty("update_type")
    private String updateType;

    @JsonProperty("two_level_arch_enabled")
    private Boolean twoLevelArchEnabled;

    @JsonProperty("last_update_time")
    private Object lastUpdateTime;

    public String getClientId() {
        return clientId;
    }

    public void setClientId(String clientId) {
        this.clientId = clientId;
    }

    public String getFactoryId() {
        return factoryId;
    }

    public void setFactoryId(String factoryId) {
        this.factoryId = factoryId;
    }

    public Object getModelType() {
        return modelType;
    }

    public void setModelType(Object modelType) {
        this.modelType = modelType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
    }

    public Integer getCurrentRound() {
        return currentRound;
    }

    public void setCurrentRound(Integer currentRound) {
        this.currentRound = currentRound;
    }

    public Boolean getHasGlobalModel() {
        return hasGlobalModel;
    }

    public void setHasGlobalModel(Boolean hasGlobalModel) {
        this.hasGlobalModel = hasGlobalModel;
    }

    public Boolean getHasLocalModel() {
        return hasLocalModel;
    }

    public void setHasLocalModel(Boolean hasLocalModel) {
        this.hasLocalModel = hasLocalModel;
    }

    public Integer getTrainingCount() {
        return trainingCount;
    }

    public void setTrainingCount(Integer trainingCount) {
        this.trainingCount = trainingCount;
    }

    public String getPrivacyMechanism() {
        return privacyMechanism;
    }

    public void setPrivacyMechanism(String privacyMechanism) {
        this.privacyMechanism = privacyMechanism;
    }

    public String getUpdateType() {
        return updateType;
    }

    public void setUpdateType(String updateType) {
        this.updateType = updateType;
    }

    public Boolean getTwoLevelArchEnabled() {
        return twoLevelArchEnabled;
    }

    public void setTwoLevelArchEnabled(Boolean twoLevelArchEnabled) {
        this.twoLevelArchEnabled = twoLevelArchEnabled;
    }

    public Object getLastUpdateTime() {
        return lastUpdateTime;
    }

    public void setLastUpdateTime(Object lastUpdateTime) {
        this.lastUpdateTime = lastUpdateTime;
    }

}