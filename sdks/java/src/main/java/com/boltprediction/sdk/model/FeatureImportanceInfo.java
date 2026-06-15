package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 特征重要性分析（各通道对预测结果的贡献度） */
@JsonIgnoreProperties(ignoreUnknown = true)
public class FeatureImportanceInfo {

    @JsonProperty("preload")
    private Double preload;

    @JsonProperty("temperature")
    private Double temperature;

    @JsonProperty("humidity")
    private Double humidity;

    @JsonProperty("vibration")
    private Double vibration;

    @JsonProperty("torque")
    private Double torque;

    @JsonProperty("others")
    private Map<String, Double> others;

    public Double getPreload() {
        return preload;
    }

    public void setPreload(Double preload) {
        this.preload = preload;
    }

    public Double getTemperature() {
        return temperature;
    }

    public void setTemperature(Double temperature) {
        this.temperature = temperature;
    }

    public Double getHumidity() {
        return humidity;
    }

    public void setHumidity(Double humidity) {
        this.humidity = humidity;
    }

    public Double getVibration() {
        return vibration;
    }

    public void setVibration(Double vibration) {
        this.vibration = vibration;
    }

    public Double getTorque() {
        return torque;
    }

    public void setTorque(Double torque) {
        this.torque = torque;
    }

    public Map<String, Double> getOthers() {
        return others;
    }

    public void setOthers(Map<String, Double> others) {
        this.others = others;
    }

}