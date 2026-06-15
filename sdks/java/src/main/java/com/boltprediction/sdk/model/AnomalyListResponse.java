package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 异常列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<AnomalyDataResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<AnomalyDataResponse> getItems() {
        return items;
    }

    public void setItems(List<AnomalyDataResponse> items) {
        this.items = items;
    }

}