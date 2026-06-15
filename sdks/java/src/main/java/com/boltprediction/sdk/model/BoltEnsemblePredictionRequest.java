package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 螺栓集成学习预测调试请求 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class BoltEnsemblePredictionRequest {

    @JsonProperty("bolt_id")
    private String boltId;

    @JsonProperty("data")
    private List<Double> data;

    @JsonProperty("version")
    private Object version;

    @JsonProperty("method")
    private Object method;

    @JsonProperty("weights")
    private Object weights;

    public String getBoltId() {
        return boltId;
    }

    public void setBoltId(String boltId) {
        this.boltId = boltId;
    }

    public List<Double> getData() {
        return data;
    }

    public void setData(List<Double> data) {
        this.data = data;
    }

    public Object getVersion() {
        return version;
    }

    public void setVersion(Object version) {
        this.version = version;
    }

    public Object getMethod() {
        return method;
    }

    public void setMethod(Object method) {
        this.method = method;
    }

    public Object getWeights() {
        return weights;
    }

    public void setWeights(Object weights) {
        this.weights = weights;
    }

}