package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 策略审计日志列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StrategyAuditLogListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<StrategyAuditLogResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<StrategyAuditLogResponse> getItems() {
        return items;
    }

    public void setItems(List<StrategyAuditLogResponse> items) {
        this.items = items;
    }

}