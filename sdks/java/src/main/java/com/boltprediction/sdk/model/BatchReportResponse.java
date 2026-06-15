package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 批量报告响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BatchReportResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("success")
    private Integer success;

    @JsonProperty("failed")
    private Integer failed;

    @JsonProperty("results")
    private List<PeriodicReportResponse> results;

    @JsonProperty("errors")
    private Map<String, String> errors;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public Integer getSuccess() {
        return success;
    }

    public void setSuccess(Integer success) {
        this.success = success;
    }

    public Integer getFailed() {
        return failed;
    }

    public void setFailed(Integer failed) {
        this.failed = failed;
    }

    public List<PeriodicReportResponse> getResults() {
        return results;
    }

    public void setResults(List<PeriodicReportResponse> results) {
        this.results = results;
    }

    public Map<String, String> getErrors() {
        return errors;
    }

    public void setErrors(Map<String, String> errors) {
        this.errors = errors;
    }

}