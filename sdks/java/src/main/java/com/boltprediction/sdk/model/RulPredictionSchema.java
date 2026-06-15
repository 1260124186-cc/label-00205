package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 剩余使用寿命预测 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RulPredictionSchema {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("current_hi")
    private Double currentHi;

    @JsonProperty("rul_days")
    private Double rulDays;

    @JsonProperty("rul_lower_bound")
    private Double rulLowerBound;

    @JsonProperty("rul_upper_bound")
    private Double rulUpperBound;

    @JsonProperty("rul_confidence")
    private Double rulConfidence;

    @JsonProperty("failure_threshold")
    private Double failureThreshold;

    @JsonProperty("warning_threshold")
    private Double warningThreshold;

    @JsonProperty("days_to_warning")
    private Object daysToWarning;

    @JsonProperty("historical_hi")
    private List<Map<String, Object>> historicalHi;

    @JsonProperty("forecast_series")
    private List<RulPredictionPointSchema> forecastSeries;

    @JsonProperty("degradation_model")
    private String degradationModel;

    @JsonProperty("model_params")
    private Map<String, Object> modelParams;

    @JsonProperty("prediction_date")
    private OffsetDateTime predictionDate;

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

    public Double getCurrentHi() {
        return currentHi;
    }

    public void setCurrentHi(Double currentHi) {
        this.currentHi = currentHi;
    }

    public Double getRulDays() {
        return rulDays;
    }

    public void setRulDays(Double rulDays) {
        this.rulDays = rulDays;
    }

    public Double getRulLowerBound() {
        return rulLowerBound;
    }

    public void setRulLowerBound(Double rulLowerBound) {
        this.rulLowerBound = rulLowerBound;
    }

    public Double getRulUpperBound() {
        return rulUpperBound;
    }

    public void setRulUpperBound(Double rulUpperBound) {
        this.rulUpperBound = rulUpperBound;
    }

    public Double getRulConfidence() {
        return rulConfidence;
    }

    public void setRulConfidence(Double rulConfidence) {
        this.rulConfidence = rulConfidence;
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

    public Object getDaysToWarning() {
        return daysToWarning;
    }

    public void setDaysToWarning(Object daysToWarning) {
        this.daysToWarning = daysToWarning;
    }

    public List<Map<String, Object>> getHistoricalHi() {
        return historicalHi;
    }

    public void setHistoricalHi(List<Map<String, Object>> historicalHi) {
        this.historicalHi = historicalHi;
    }

    public List<RulPredictionPointSchema> getForecastSeries() {
        return forecastSeries;
    }

    public void setForecastSeries(List<RulPredictionPointSchema> forecastSeries) {
        this.forecastSeries = forecastSeries;
    }

    public String getDegradationModel() {
        return degradationModel;
    }

    public void setDegradationModel(String degradationModel) {
        this.degradationModel = degradationModel;
    }

    public Map<String, Object> getModelParams() {
        return modelParams;
    }

    public void setModelParams(Map<String, Object> modelParams) {
        this.modelParams = modelParams;
    }

    public OffsetDateTime getPredictionDate() {
        return predictionDate;
    }

    public void setPredictionDate(OffsetDateTime predictionDate) {
        this.predictionDate = predictionDate;
    }

}