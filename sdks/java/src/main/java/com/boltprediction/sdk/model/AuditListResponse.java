package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 审计记录列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AuditListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<AuditRecordResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<AuditRecordResponse> getItems() {
        return items;
    }

    public void setItems(List<AuditRecordResponse> items) {
        this.items = items;
    }

}