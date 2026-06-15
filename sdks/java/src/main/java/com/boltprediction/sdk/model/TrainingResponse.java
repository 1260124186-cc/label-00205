package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 模型训练响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TrainingResponse {

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("status")
    private String status;

    @JsonProperty("message")
    private String message;

    @JsonProperty("training_time")
    private Double trainingTime;

    @JsonProperty("metrics")
    private Object metrics;

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
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

    public Double getTrainingTime() {
        return trainingTime;
    }

    public void setTrainingTime(Double trainingTime) {
        this.trainingTime = trainingTime;
    }

    public Object getMetrics() {
        return metrics;
    }

    public void setMetrics(Object metrics) {
        this.metrics = metrics;
    }

}