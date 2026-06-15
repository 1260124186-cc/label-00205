package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 策略配置列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class StrategyConfigListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<StrategyConfigItemResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<StrategyConfigItemResponse> getItems() {
        return items;
    }

    public void setItems(List<StrategyConfigItemResponse> items) {
        this.items = items;
    }

}