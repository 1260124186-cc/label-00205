package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 模型信息响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ModelInfoResponse {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("is_trained")
    private Boolean isTrained;

    @JsonProperty("last_training_time")
    private Object lastTrainingTime;

    @JsonProperty("training_samples")
    private Object trainingSamples;

    @JsonProperty("validation_accuracy")
    private Object validationAccuracy;

    @JsonProperty("version")
    private Object version;

    @JsonProperty("file_hash")
    private Object fileHash;

    @JsonProperty("create_time")
    private Object createTime;

    @JsonProperty("training_session_id")
    private Object trainingSessionId;

    @JsonProperty("description")
    private Object description;

    @JsonProperty("validation_samples")
    private Object validationSamples;

    @JsonProperty("is_incremental")
    private Object isIncremental;

    @JsonProperty("parent_version")
    private Object parentVersion;

    @JsonProperty("metrics")
    private Object metrics;

    @JsonProperty("version_history")
    private Object versionHistory;

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

    public Boolean getIsTrained() {
        return isTrained;
    }

    public void setIsTrained(Boolean isTrained) {
        this.isTrained = isTrained;
    }

    public Object getLastTrainingTime() {
        return lastTrainingTime;
    }

    public void setLastTrainingTime(Object lastTrainingTime) {
        this.lastTrainingTime = lastTrainingTime;
    }

    public Object getTrainingSamples() {
        return trainingSamples;
    }

    public void setTrainingSamples(Object trainingSamples) {
        this.trainingSamples = trainingSamples;
    }

    public Object getValidationAccuracy() {
        return validationAccuracy;
    }

    public void setValidationAccuracy(Object validationAccuracy) {
        this.validationAccuracy = validationAccuracy;
    }

    public Object getVersion() {
        return version;
    }

    public void setVersion(Object version) {
        this.version = version;
    }

    public Object getFileHash() {
        return fileHash;
    }

    public void setFileHash(Object fileHash) {
        this.fileHash = fileHash;
    }

    public Object getCreateTime() {
        return createTime;
    }

    public void setCreateTime(Object createTime) {
        this.createTime = createTime;
    }

    public Object getTrainingSessionId() {
        return trainingSessionId;
    }

    public void setTrainingSessionId(Object trainingSessionId) {
        this.trainingSessionId = trainingSessionId;
    }

    public Object getDescription() {
        return description;
    }

    public void setDescription(Object description) {
        this.description = description;
    }

    public Object getValidationSamples() {
        return validationSamples;
    }

    public void setValidationSamples(Object validationSamples) {
        this.validationSamples = validationSamples;
    }

    public Object getIsIncremental() {
        return isIncremental;
    }

    public void setIsIncremental(Object isIncremental) {
        this.isIncremental = isIncremental;
    }

    public Object getParentVersion() {
        return parentVersion;
    }

    public void setParentVersion(Object parentVersion) {
        this.parentVersion = parentVersion;
    }

    public Object getMetrics() {
        return metrics;
    }

    public void setMetrics(Object metrics) {
        this.metrics = metrics;
    }

    public Object getVersionHistory() {
        return versionHistory;
    }

    public void setVersionHistory(Object versionHistory) {
        this.versionHistory = versionHistory;
    }

}