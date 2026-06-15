package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 流式预测引擎状态响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StreamEngineStatusResponse {

    @JsonProperty("is_running")
    private Boolean isRunning;

    @JsonProperty("mode")
    private String mode;

    @JsonProperty("active_streams")
    private Integer activeStreams;

    @JsonProperty("total_predictions")
    private Integer totalPredictions;

    @JsonProperty("status_changes")
    private Integer statusChanges;

    @JsonProperty("window_manager")
    private Map<String, Object> windowManager;

    @JsonProperty("backpressure")
    private Map<String, Object> backpressure;

    @JsonProperty("events")
    private Map<String, Object> events;

    @JsonProperty("adapters")
    private List<Map<String, Object>> adapters;

    public Boolean getIsRunning() {
        return isRunning;
    }

    public void setIsRunning(Boolean isRunning) {
        this.isRunning = isRunning;
    }

    public String getMode() {
        return mode;
    }

    public void setMode(String mode) {
        this.mode = mode;
    }

    public Integer getActiveStreams() {
        return activeStreams;
    }

    public void setActiveStreams(Integer activeStreams) {
        this.activeStreams = activeStreams;
    }

    public Integer getTotalPredictions() {
        return totalPredictions;
    }

    public void setTotalPredictions(Integer totalPredictions) {
        this.totalPredictions = totalPredictions;
    }

    public Integer getStatusChanges() {
        return statusChanges;
    }

    public void setStatusChanges(Integer statusChanges) {
        this.statusChanges = statusChanges;
    }

    public Map<String, Object> getWindowManager() {
        return windowManager;
    }

    public void setWindowManager(Map<String, Object> windowManager) {
        this.windowManager = windowManager;
    }

    public Map<String, Object> getBackpressure() {
        return backpressure;
    }

    public void setBackpressure(Map<String, Object> backpressure) {
        this.backpressure = backpressure;
    }

    public Map<String, Object> getEvents() {
        return events;
    }

    public void setEvents(Map<String, Object> events) {
        this.events = events;
    }

    public List<Map<String, Object>> getAdapters() {
        return adapters;
    }

    public void setAdapters(List<Map<String, Object>> adapters) {
        this.adapters = adapters;
    }

}