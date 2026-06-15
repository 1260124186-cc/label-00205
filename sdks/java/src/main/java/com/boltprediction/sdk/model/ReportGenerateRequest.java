package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 周期报告生成请求（周报/月报） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportGenerateRequest {

    @JsonProperty("node_type")
    private String nodeType;

    @JsonProperty("node_id")
    private String nodeId;

    @JsonProperty("report_type")
    private String reportType;

    @JsonProperty("use_llm")
    private Object useLlm;

    public String getNodeType() {
        return nodeType;
    }

    public void setNodeType(String nodeType) {
        this.nodeType = nodeType;
    }

    public String getNodeId() {
        return nodeId;
    }

    public void setNodeId(String nodeId) {
        this.nodeId = nodeId;
    }

    public String getReportType() {
        return reportType;
    }

    public void setReportType(String reportType) {
        this.reportType = reportType;
    }

    public Object getUseLlm() {
        return useLlm;
    }

    public void setUseLlm(Object useLlm) {
        this.useLlm = useLlm;
    }

}