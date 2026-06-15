package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 工单列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkOrderListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<WorkOrderResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<WorkOrderResponse> getItems() {
        return items;
    }

    public void setItems(List<WorkOrderResponse> items) {
        this.items = items;
    }

}