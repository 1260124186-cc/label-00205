package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 处置记录列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DisposalRecordListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<DisposalRecordResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<DisposalRecordResponse> getItems() {
        return items;
    }

    public void setItems(List<DisposalRecordResponse> items) {
        this.items = items;
    }

}