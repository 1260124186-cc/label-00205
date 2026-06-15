package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常查询请求

支持按 sensor_id、时间范围、类型、确认状态等多维度查询。 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyQueryRequest {

    @JsonProperty("sensor_id")
    private Object sensorId;

    @JsonProperty("start_time")
    private Object startTime;

    @JsonProperty("end_time")
    private Object endTime;

    @JsonProperty("anomaly_type")
    private Object anomalyType;

    @JsonProperty("classification")
    private Object classification;

    @JsonProperty("is_confirmed")
    private Object isConfirmed;

    @JsonProperty("is_false_positive")
    private Object isFalsePositive;

    @JsonProperty("min_score")
    private Object minScore;

    @JsonProperty("max_score")
    private Object maxScore;

    @JsonProperty("limit")
    private Integer limit;

    @JsonProperty("offset")
    private Integer offset;

    @JsonProperty("sort_by")
    private String sortBy;

    @JsonProperty("sort_order")
    private String sortOrder;

    public Object getSensorId() {
        return sensorId;
    }

    public void setSensorId(Object sensorId) {
        this.sensorId = sensorId;
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

    public Object getAnomalyType() {
        return anomalyType;
    }

    public void setAnomalyType(Object anomalyType) {
        this.anomalyType = anomalyType;
    }

    public Object getClassification() {
        return classification;
    }

    public void setClassification(Object classification) {
        this.classification = classification;
    }

    public Object getIsConfirmed() {
        return isConfirmed;
    }

    public void setIsConfirmed(Object isConfirmed) {
        this.isConfirmed = isConfirmed;
    }

    public Object getIsFalsePositive() {
        return isFalsePositive;
    }

    public void setIsFalsePositive(Object isFalsePositive) {
        this.isFalsePositive = isFalsePositive;
    }

    public Object getMinScore() {
        return minScore;
    }

    public void setMinScore(Object minScore) {
        this.minScore = minScore;
    }

    public Object getMaxScore() {
        return maxScore;
    }

    public void setMaxScore(Object maxScore) {
        this.maxScore = maxScore;
    }

    public Integer getLimit() {
        return limit;
    }

    public void setLimit(Integer limit) {
        this.limit = limit;
    }

    public Integer getOffset() {
        return offset;
    }

    public void setOffset(Integer offset) {
        this.offset = offset;
    }

    public String getSortBy() {
        return sortBy;
    }

    public void setSortBy(String sortBy) {
        this.sortBy = sortBy;
    }

    public String getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(String sortOrder) {
        this.sortOrder = sortOrder;
    }

}