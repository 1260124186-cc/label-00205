package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 学习率调度器配置 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LrSchedulerConfig {

    @JsonProperty("type")
    private String type;

    @JsonProperty("factor")
    private Object factor;

    @JsonProperty("patience")
    private Object patience;

    @JsonProperty("min_lr")
    private Object minLr;

    @JsonProperty("step_size")
    private Object stepSize;

    @JsonProperty("gamma")
    private Object gamma;

    @JsonProperty("t_max")
    private Object tMax;

    @JsonProperty("eta_min")
    private Object etaMin;

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public Object getFactor() {
        return factor;
    }

    public void setFactor(Object factor) {
        this.factor = factor;
    }

    public Object getPatience() {
        return patience;
    }

    public void setPatience(Object patience) {
        this.patience = patience;
    }

    public Object getMinLr() {
        return minLr;
    }

    public void setMinLr(Object minLr) {
        this.minLr = minLr;
    }

    public Object getStepSize() {
        return stepSize;
    }

    public void setStepSize(Object stepSize) {
        this.stepSize = stepSize;
    }

    public Object getGamma() {
        return gamma;
    }

    public void setGamma(Object gamma) {
        this.gamma = gamma;
    }

    public Object getTMax() {
        return tMax;
    }

    public void setTMax(Object tMax) {
        this.tMax = tMax;
    }

    public Object getEtaMin() {
        return etaMin;
    }

    public void setEtaMin(Object etaMin) {
        this.etaMin = etaMin;
    }

}