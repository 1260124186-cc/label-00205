package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 告警列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AlertListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<AlertEventResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<AlertEventResponse> getItems() {
        return items;
    }

    public void setItems(List<AlertEventResponse> items) {
        this.items = items;
    }

}