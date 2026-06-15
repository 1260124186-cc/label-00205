package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 训练会话信息 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TrainingSessionSchema {

    @JsonProperty("session_id")
    private String sessionId;

    @JsonProperty("model_id")
    private String modelId;

    @JsonProperty("model_type")
    private String modelType;

    @JsonProperty("status")
    private String status;

    @JsonProperty("start_time")
    private Object startTime;

    @JsonProperty("end_time")
    private Object endTime;

    @JsonProperty("total_epochs")
    private Integer totalEpochs;

    @JsonProperty("current_epoch")
    private Integer currentEpoch;

    @JsonProperty("best_metrics")
    private Map<String, Double> bestMetrics;

    @JsonProperty("metrics_history")
    private List<EpochMetricsSchema> metricsHistory;

    @JsonProperty("config")
    private Map<String, Object> config;

    @JsonProperty("error_message")
    private Object errorMessage;

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getModelId() {
        return modelId;
    }

    public void setModelId(String modelId) {
        this.modelId = modelId;
    }

    public String getModelType() {
        return modelType;
    }

    public void setModelType(String modelType) {
        this.modelType = modelType;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Object getStartTime() {
        return startTime;
    }

    public void setStartTime(Object startTime) {
        this.startTime = startTime;
    }

    public Object getEndTime() {
        return endTime;
    }

    public void setEndTime(Object endTime) {
        this.endTime = endTime;
    }

    public Integer getTotalEpochs() {
        return totalEpochs;
    }

    public void setTotalEpochs(Integer totalEpochs) {
        this.totalEpochs = totalEpochs;
    }

    public Integer getCurrentEpoch() {
        return currentEpoch;
    }

    public void setCurrentEpoch(Integer currentEpoch) {
        this.currentEpoch = currentEpoch;
    }

    public Map<String, Double> getBestMetrics() {
        return bestMetrics;
    }

    public void setBestMetrics(Map<String, Double> bestMetrics) {
        this.bestMetrics = bestMetrics;
    }

    public List<EpochMetricsSchema> getMetricsHistory() {
        return metricsHistory;
    }

    public void setMetricsHistory(List<EpochMetricsSchema> metricsHistory) {
        this.metricsHistory = metricsHistory;
    }

    public Map<String, Object> getConfig() {
        return config;
    }

    public void setConfig(Map<String, Object> config) {
        this.config = config;
    }

    public Object getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(Object errorMessage) {
        this.errorMessage = errorMessage;
    }

}