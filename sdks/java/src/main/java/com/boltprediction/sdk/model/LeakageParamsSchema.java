package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 泄漏率估算模型参数 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class LeakageParamsSchema {

    @JsonProperty("base_leakage_rate_m3_per_hour")
    private Double baseLeakageRateM3PerHour;

    @JsonProperty("critical_leakage_threshold")
    private Double criticalLeakageThreshold;

    @JsonProperty("preload_leakage_sensitivity")
    private Double preloadLeakageSensitivity;

    @JsonProperty("seal_aging_factor_per_year")
    private Double sealAgingFactorPerYear;

    @JsonProperty("pressure_sensitivity")
    private Double pressureSensitivity;

    public Double getBaseLeakageRateM3PerHour() {
        return baseLeakageRateM3PerHour;
    }

    public void setBaseLeakageRateM3PerHour(Double baseLeakageRateM3PerHour) {
        this.baseLeakageRateM3PerHour = baseLeakageRateM3PerHour;
    }

    public Double getCriticalLeakageThreshold() {
        return criticalLeakageThreshold;
    }

    public void setCriticalLeakageThreshold(Double criticalLeakageThreshold) {
        this.criticalLeakageThreshold = criticalLeakageThreshold;
    }

    public Double getPreloadLeakageSensitivity() {
        return preloadLeakageSensitivity;
    }

    public void setPreloadLeakageSensitivity(Double preloadLeakageSensitivity) {
        this.preloadLeakageSensitivity = preloadLeakageSensitivity;
    }

    public Double getSealAgingFactorPerYear() {
        return sealAgingFactorPerYear;
    }

    public void setSealAgingFactorPerYear(Double sealAgingFactorPerYear) {
        this.sealAgingFactorPerYear = sealAgingFactorPerYear;
    }

    public Double getPressureSensitivity() {
        return pressureSensitivity;
    }

    public void setPressureSensitivity(Double pressureSensitivity) {
        this.pressureSensitivity = pressureSensitivity;
    }

}