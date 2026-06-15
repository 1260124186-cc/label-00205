package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 流式窗口状态响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamWindowStatusResponse {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("window_size")
    private Integer windowSize;

    @JsonProperty("current_size")
    private Integer currentSize;

    @JsonProperty("is_full")
    private Boolean isFull;

    @JsonProperty("last_updated")
    private Object lastUpdated;

    @JsonProperty("last_prediction_status")
    private Object lastPredictionStatus;

    @JsonProperty("prediction_count")
    private Object predictionCount;

    @JsonProperty("first_timestamp")
    private Object firstTimestamp;

    @JsonProperty("last_timestamp")
    private Object lastTimestamp;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public Integer getWindowSize() {
        return windowSize;
    }

    public void setWindowSize(Integer windowSize) {
        this.windowSize = windowSize;
    }

    public Integer getCurrentSize() {
        return currentSize;
    }

    public void setCurrentSize(Integer currentSize) {
        this.currentSize = currentSize;
    }

    public Boolean getIsFull() {
        return isFull;
    }

    public void setIsFull(Boolean isFull) {
        this.isFull = isFull;
    }

    public Object getLastUpdated() {
        return lastUpdated;
    }

    public void setLastUpdated(Object lastUpdated) {
        this.lastUpdated = lastUpdated;
    }

    public Object getLastPredictionStatus() {
        return lastPredictionStatus;
    }

    public void setLastPredictionStatus(Object lastPredictionStatus) {
        this.lastPredictionStatus = lastPredictionStatus;
    }

    public Object getPredictionCount() {
        return predictionCount;
    }

    public void setPredictionCount(Object predictionCount) {
        this.predictionCount = predictionCount;
    }

    public Object getFirstTimestamp() {
        return firstTimestamp;
    }

    public void setFirstTimestamp(Object firstTimestamp) {
        this.firstTimestamp = firstTimestamp;
    }

    public Object getLastTimestamp() {
        return lastTimestamp;
    }

    public void setLastTimestamp(Object lastTimestamp) {
        this.lastTimestamp = lastTimestamp;
    }

}