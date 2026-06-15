package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 案例列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class KnowledgeCaseListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<KnowledgeCaseResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<KnowledgeCaseResponse> getItems() {
        return items;
    }

    public void setItems(List<KnowledgeCaseResponse> items) {
        this.items = items;
    }

}