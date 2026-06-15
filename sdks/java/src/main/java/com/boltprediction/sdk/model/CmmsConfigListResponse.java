package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** CMMS配置列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CmmsConfigListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<CmmsConfigResponse> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<CmmsConfigResponse> getItems() {
        return items;
    }

    public void setItems(List<CmmsConfigResponse> items) {
        this.items = items;
    }

}