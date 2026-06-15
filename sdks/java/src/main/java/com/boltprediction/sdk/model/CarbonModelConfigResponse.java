package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 碳排模型系数配置响应 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CarbonModelConfigResponse {

    @JsonProperty("degradation")
    private DegradationParamsSchema degradation;

    @JsonProperty("leakage")
    private LeakageParamsSchema leakage;

    @JsonProperty("energy_carbon")
    private EnergyCarbonParamsSchema energyCarbon;

    public DegradationParamsSchema getDegradation() {
        return degradation;
    }

    public void setDegradation(DegradationParamsSchema degradation) {
        this.degradation = degradation;
    }

    public LeakageParamsSchema getLeakage() {
        return leakage;
    }

    public void setLeakage(LeakageParamsSchema leakage) {
        this.leakage = leakage;
    }

    public EnergyCarbonParamsSchema getEnergyCarbon() {
        return energyCarbon;
    }

    public void setEnergyCarbon(EnergyCarbonParamsSchema energyCarbon) {
        this.energyCarbon = energyCarbon;
    }

}