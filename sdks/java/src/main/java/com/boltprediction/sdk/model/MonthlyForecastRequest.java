package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 月度预测请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MonthlyForecastRequest {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("forecast_days")
    private Integer forecastDays;

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

}