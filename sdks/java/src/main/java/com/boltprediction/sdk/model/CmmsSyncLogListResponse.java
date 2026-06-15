package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CMMS同步日志列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsSyncLogListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<CmmsSyncLogResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<CmmsSyncLogResponse> getItems() {
        return items;
    }

    public void setItems(List<CmmsSyncLogResponse> items) {
        this.items = items;
    }

}