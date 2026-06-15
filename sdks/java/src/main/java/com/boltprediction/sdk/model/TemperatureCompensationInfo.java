package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 温度耦合补偿信息

Attributes:
    applied: 是否执行了温度补偿
    temperature_coefficient: 估计的温度系数 α (kN/°C)
    correlation: 温度与预紧力的皮尔逊相关系数
    original_mean_preload: 补偿前平均预紧力
    compensated_mean_preload: 补偿后平均预紧力
    delta_t_mean: 平均温度波动 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TemperatureCompensationInfo {

    @JsonProperty("applied")
    private Boolean applied;

    @JsonProperty("temperature_coefficient")
    private Object temperatureCoefficient;

    @JsonProperty("correlation")
    private Object correlation;

    @JsonProperty("original_mean_preload")
    private Object originalMeanPreload;

    @JsonProperty("compensated_mean_preload")
    private Object compensatedMeanPreload;

    @JsonProperty("delta_t_mean")
    private Object deltaTMean;

    public Boolean getApplied() {
        return applied;
    }

    public void setApplied(Boolean applied) {
        this.applied = applied;
    }

    public Object getTemperatureCoefficient() {
        return temperatureCoefficient;
    }

    public void setTemperatureCoefficient(Object temperatureCoefficient) {
        this.temperatureCoefficient = temperatureCoefficient;
    }

    public Object getCorrelation() {
        return correlation;
    }

    public void setCorrelation(Object correlation) {
        this.correlation = correlation;
    }

    public Object getOriginalMeanPreload() {
        return originalMeanPreload;
    }

    public void setOriginalMeanPreload(Object originalMeanPreload) {
        this.originalMeanPreload = originalMeanPreload;
    }

    public Object getCompensatedMeanPreload() {
        return compensatedMeanPreload;
    }

    public void setCompensatedMeanPreload(Object compensatedMeanPreload) {
        this.compensatedMeanPreload = compensatedMeanPreload;
    }

    public Object getDeltaTMean() {
        return deltaTMean;
    }

    public void setDeltaTMean(Object deltaTMean) {
        this.deltaTMean = deltaTMean;
    }

}