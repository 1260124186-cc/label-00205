package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 预紧力劣化模型参数 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class DegradationParamsSchema {

    @JsonProperty("nominal_preload")
    private Double nominalPreload;

    @JsonProperty("min_effective_preload_ratio")
    private Double minEffectivePreloadRatio;

    @JsonProperty("relaxation_rate_per_month")
    private Double relaxationRatePerMonth;

    @JsonProperty("temperature_acceleration_factor")
    private Double temperatureAccelerationFactor;

    @JsonProperty("vibration_acceleration_factor")
    private Double vibrationAccelerationFactor;

    @JsonProperty("cycle_acceleration_factor")
    private Double cycleAccelerationFactor;

    public Double getNominalPreload() {
        return nominalPreload;
    }

    public void setNominalPreload(Double nominalPreload) {
        this.nominalPreload = nominalPreload;
    }

    public Double getMinEffectivePreloadRatio() {
        return minEffectivePreloadRatio;
    }

    public void setMinEffectivePreloadRatio(Double minEffectivePreloadRatio) {
        this.minEffectivePreloadRatio = minEffectivePreloadRatio;
    }

    public Double getRelaxationRatePerMonth() {
        return relaxationRatePerMonth;
    }

    public void setRelaxationRatePerMonth(Double relaxationRatePerMonth) {
        this.relaxationRatePerMonth = relaxationRatePerMonth;
    }

    public Double getTemperatureAccelerationFactor() {
        return temperatureAccelerationFactor;
    }

    public void setTemperatureAccelerationFactor(Double temperatureAccelerationFactor) {
        this.temperatureAccelerationFactor = temperatureAccelerationFactor;
    }

    public Double getVibrationAccelerationFactor() {
        return vibrationAccelerationFactor;
    }

    public void setVibrationAccelerationFactor(Double vibrationAccelerationFactor) {
        this.vibrationAccelerationFactor = vibrationAccelerationFactor;
    }

    public Double getCycleAccelerationFactor() {
        return cycleAccelerationFactor;
    }

    public void setCycleAccelerationFactor(Double cycleAccelerationFactor) {
        this.cycleAccelerationFactor = cycleAccelerationFactor;
    }

}