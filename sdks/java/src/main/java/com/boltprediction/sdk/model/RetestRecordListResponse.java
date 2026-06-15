package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 复测记录列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class RetestRecordListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<RetestRecordResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<RetestRecordResponse> getItems() {
        return items;
    }

    public void setItems(List<RetestRecordResponse> items) {
        this.items = items;
    }

}