package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** ESG报表片段导出请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EsgReportExportRequest {

    @JsonProperty("nodes")
    private List<Map<String, Object>> nodes;

    @JsonProperty("format")
    private String format;

    @JsonProperty("include_methodology")
    private Boolean includeMethodology;

    @JsonProperty("top_n")
    private Object topN;

    public List<Map<String, Object>> getNodes() {
        return nodes;
    }

    public void setNodes(List<Map<String, Object>> nodes) {
        this.nodes = nodes;
    }

    public String getFormat() {
        return format;
    }

    public void setFormat(String format) {
        this.format = format;
    }

    public Boolean getIncludeMethodology() {
        return includeMethodology;
    }

    public void setIncludeMethodology(Boolean includeMethodology) {
        this.includeMethodology = includeMethodology;
    }

    public Object getTopN() {
        return topN;
    }

    public void setTopN(Object topN) {
        this.topN = topN;
    }

}