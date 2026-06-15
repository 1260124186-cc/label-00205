package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 预测对比列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PredictionCompareListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<PredictionCompareResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<PredictionCompareResponse> getItems() {
        return items;
    }

    public void setItems(List<PredictionCompareResponse> items) {
        this.items = items;
    }

}