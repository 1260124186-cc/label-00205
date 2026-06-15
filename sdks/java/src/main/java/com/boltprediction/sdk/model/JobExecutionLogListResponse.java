package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 任务执行日志列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class JobExecutionLogListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<JobExecutionLogSchema> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<JobExecutionLogSchema> getItems() {
        return items;
    }

    public void setItems(List<JobExecutionLogSchema> items) {
        this.items = items;
    }

}