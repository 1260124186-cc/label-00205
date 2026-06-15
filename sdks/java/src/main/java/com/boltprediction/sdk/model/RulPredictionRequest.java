package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** RUL预测请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RulPredictionRequest {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("forecast_days")
    private Integer forecastDays;

    @JsonProperty("failure_threshold")
    private Double failureThreshold;

    @JsonProperty("warning_threshold")
    private Double warningThreshold;

    @JsonProperty("model_type")
    private Object modelType;

    @JsonProperty("use_history_days")
    private Integer useHistoryDays;

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

    public Integer getForecastDays() {
        return forecastDays;
    }

    public void setForecastDays(Integer forecastDays) {
        this.forecastDays = forecastDays;
    }

    public Double getFailureThreshold() {
        return failureThreshold;
    }

    public void setFailureThreshold(Double failureThreshold) {
        this.failureThreshold = failureThreshold;
    }

    public Double getWarningThreshold() {
        return warningThreshold;
    }

    public void setWarningThreshold(Double warningThreshold) {
        this.warningThreshold = warningThreshold;
    }

    public Object getModelType() {
        return modelType;
    }

    public void setModelType(Object modelType) {
        this.modelType = modelType;
    }

    public Integer getUseHistoryDays() {
        return useHistoryDays;
    }

    public void setUseHistoryDays(Integer useHistoryDays) {
        this.useHistoryDays = useHistoryDays;
    }

}