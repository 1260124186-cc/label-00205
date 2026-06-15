package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** APIKeyListResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiKeyListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<ApiKeyInfoResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<ApiKeyInfoResponse> getItems() {
        return items;
    }

    public void setItems(List<ApiKeyInfoResponse> items) {
        this.items = items;
    }

}