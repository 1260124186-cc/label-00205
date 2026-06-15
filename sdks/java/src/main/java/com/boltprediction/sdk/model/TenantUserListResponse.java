package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** TenantUserListResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TenantUserListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<TenantUserResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<TenantUserResponse> getItems() {
        return items;
    }

    public void setItems(List<TenantUserResponse> items) {
        this.items = items;
    }

}