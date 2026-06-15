package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 螺栓预测请求

Attributes:
    螺栓id: 螺栓唯一标识
    data: 预紧力时序数据 [[时间, 预紧力], ...] */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BoltPredictionRequest {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("data")
    private List<List<Object>> data;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public List<List<Object>> getData() {
        return data;
    }

    public void setData(List<List<Object>> data) {
        this.data = data;
    }

}