package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantListResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<TenantResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<TenantResponse> getItems() {
        return items;
    }

    public void setItems(List<TenantResponse> items) {
        this.items = items;
    }

}