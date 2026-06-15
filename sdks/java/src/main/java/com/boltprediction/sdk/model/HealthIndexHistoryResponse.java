package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康度历史查询响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthIndexHistoryResponse {

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("history")
    private List<Map<String, Object>> history;

    @JsonProperty("trend_analysis")
    private Object trendAnalysis;

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

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<Map<String, Object>> getHistory() {
        return history;
    }

    public void setHistory(List<Map<String, Object>> history) {
        this.history = history;
    }

    public Object getTrendAnalysis() {
        return trendAnalysis;
    }

    public void setTrendAnalysis(Object trendAnalysis) {
        this.trendAnalysis = trendAnalysis;
    }

}