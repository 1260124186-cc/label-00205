package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 单次诊断报告生成请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DiagnosisReportRequest {

    @JsonProperty("status")
    private String status;

    @JsonProperty("risk_score")
    private Double riskScore;

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_id")
    private Object nodeId;

    @JsonProperty("fault_type")
    private Object faultType;

    @JsonProperty("trend")
    private Object trend;

    @JsonProperty("recent_values")
    private Object recentValues;

    @JsonProperty("historical_incidents")
    private Object historicalIncidents;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Double getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Double riskScore) {
        this.riskScore = riskScore;
    }

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public Object getNodeId() {
        return nodeId;
    }

    public void setNodeId(Object nodeId) {
        this.nodeId = nodeId;
    }

    public Object getFaultType() {
        return faultType;
    }

    public void setFaultType(Object faultType) {
        this.faultType = faultType;
    }

    public Object getTrend() {
        return trend;
    }

    public void setTrend(Object trend) {
        this.trend = trend;
    }

    public Object getRecentValues() {
        return recentValues;
    }

    public void setRecentValues(Object recentValues) {
        this.recentValues = recentValues;
    }

    public Object getHistoricalIncidents() {
        return historicalIncidents;
    }

    public void setHistoricalIncidents(Object historicalIncidents) {
        this.historicalIncidents = historicalIncidents;
    }

}