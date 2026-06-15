package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 批量操作结果响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyBatchResultResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("success")
    private Integer success;

    @JsonProperty("failed")
    private Integer failed;

    @JsonProperty("failed_ids")
    private List<Integer> failedIds;

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

    public List<Integer> getFailedIds() {
        return failedIds;
    }

    public void setFailedIds(List<Integer> failedIds) {
        this.failedIds = failedIds;
    }

}