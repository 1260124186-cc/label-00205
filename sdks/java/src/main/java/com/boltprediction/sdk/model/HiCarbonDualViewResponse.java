package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** HI rollup 与碳排并列展示响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HiCarbonDualViewResponse {

    @JsonProperty("report_month")
    private String reportMonth;

    @JsonProperty("total_nodes")
    private Integer totalNodes;

    @JsonProperty("items")
    private List<HiCarbonDualItemSchema> items;

    @JsonProperty("generated_at")
    private OffsetDateTime generatedAt;

    public String getReportMonth() {
        return reportMonth;
    }

    public void setReportMonth(String reportMonth) {
        this.reportMonth = reportMonth;
    }

    public Integer getTotalNodes() {
        return totalNodes;
    }

    public void setTotalNodes(Integer totalNodes) {
        this.totalNodes = totalNodes;
    }

    public List<HiCarbonDualItemSchema> getItems() {
        return items;
    }

    public void setItems(List<HiCarbonDualItemSchema> items) {
        this.items = items;
    }

    public OffsetDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(OffsetDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

}