package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 训练会话列表响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TrainingSessionListResponse {

    @JsonProperty("total")
    private Integer total;

    @JsonProperty("items")
    private List<TrainingSessionSchema> items;

    public Integer getTotal() {
        return total;
    }

    public void setTotal(Integer total) {
        this.total = total;
    }

    public List<TrainingSessionSchema> getItems() {
        return items;
    }

    public void setItems(List<TrainingSessionSchema> items) {
        this.items = items;
    }

}