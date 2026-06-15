package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 月度预测响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MonthlyForecastResponse {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("pw_type")
    private String pwType;

    @JsonProperty("fault_type")
    private Object faultType;

    @JsonProperty("begin_time")
    private Object beginTime;

    @JsonProperty("end_time")
    private Object endTime;

    @JsonProperty("confidence")
    private Double confidence;

    @JsonProperty("rec_measures")
    private String recMeasures;

    @JsonProperty("forecast_dates")
    private List<OffsetDateTime> forecastDates;

    @JsonProperty("forecast_values")
    private List<Double> forecastValues;

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

    public String getPwType() {
        return pwType;
    }

    public void setPwType(String pwType) {
        this.pwType = pwType;
    }

    public Object getFaultType() {
        return faultType;
    }

    public void setFaultType(Object faultType) {
        this.faultType = faultType;
    }

    public Object getBeginTime() {
        return beginTime;
    }

    public void setBeginTime(Object beginTime) {
        this.beginTime = beginTime;
    }

    public Object getEndTime() {
        return endTime;
    }

    public void setEndTime(Object endTime) {
        this.endTime = endTime;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public String getRecMeasures() {
        return recMeasures;
    }

    public void setRecMeasures(String recMeasures) {
        this.recMeasures = recMeasures;
    }

    public List<OffsetDateTime> getForecastDates() {
        return forecastDates;
    }

    public void setForecastDates(List<OffsetDateTime> forecastDates) {
        this.forecastDates = forecastDates;
    }

    public List<Double> getForecastValues() {
        return forecastValues;
    }

    public void setForecastValues(List<Double> forecastValues) {
        this.forecastValues = forecastValues;
    }

}