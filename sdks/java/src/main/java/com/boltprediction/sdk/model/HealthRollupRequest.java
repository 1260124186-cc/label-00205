package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 健康度汇总报表请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class HealthRollupRequest {

    @JsonProperty("line_id")
    private String lineId;

    @JsonProperty("line_name")
    private Object lineName;

    @JsonProperty("line_type")
    private String lineType;

    @JsonProperty("report_date")
    private Object reportDate;

    @JsonProperty("include_details")
    private Boolean includeDetails;

    public String getLineId() {
        return lineId;
    }

    public void setLineId(String lineId) {
        this.lineId = lineId;
    }

    public Object getLineName() {
        return lineName;
    }

    public void setLineName(Object lineName) {
        this.lineName = lineName;
    }

    public String getLineType() {
        return lineType;
    }

    public void setLineType(String lineType) {
        this.lineType = lineType;
    }

    public Object getReportDate() {
        return reportDate;
    }

    public void setReportDate(Object reportDate) {
        this.reportDate = reportDate;
    }

    public Boolean getIncludeDetails() {
        return includeDetails;
    }

    public void setIncludeDetails(Boolean includeDetails) {
        this.includeDetails = includeDetails;
    }

}