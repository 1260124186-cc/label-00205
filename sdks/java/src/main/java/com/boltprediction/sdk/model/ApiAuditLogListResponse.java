package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** APIAuditLogListResponse */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiAuditLogListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<ApiAuditLogResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<ApiAuditLogResponse> getItems() {
        return items;
    }

    public void setItems(List<ApiAuditLogResponse> items) {
        this.items = items;
    }

}