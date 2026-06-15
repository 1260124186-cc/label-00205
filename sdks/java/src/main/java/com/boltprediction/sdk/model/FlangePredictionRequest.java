package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 法兰面预测请求

Attributes:
    法兰面id: 法兰面唯一标识
    data: 多螺栓预紧力时序数据 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FlangePredictionRequest {

    @JsonProperty("flange_id")
    private String flangeId;

    @JsonProperty("data")
    private List<List<List<Object>>> data;

    public String getFlangeId() {
        return flangeId;
    }

    public void setFlangeId(String flangeId) {
        this.flangeId = flangeId;
    }

    public List<List<List<Object>>> getData() {
        return data;
    }

    public void setData(List<List<List<Object>>> data) {
        this.data = data;
    }

}