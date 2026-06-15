package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 能耗与碳排增量模型参数 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class EnergyCarbonParamsSchema {

    @JsonProperty("energy_per_leakage_unit")
    private Double energyPerLeakageUnit;

    @JsonProperty("carbon_factor_electricity")
    private Double carbonFactorElectricity;

    @JsonProperty("carbon_factor_natural_gas")
    private Double carbonFactorNaturalGas;

    @JsonProperty("carbon_factor_steam")
    private Double carbonFactorSteam;

    @JsonProperty("compressor_efficiency")
    private Double compressorEfficiency;

    @JsonProperty("recovery_rate")
    private Double recoveryRate;

    @JsonProperty("base_monthly_energy_kwh")
    private Double baseMonthlyEnergyKwh;

    @JsonProperty("base_monthly_carbon_kg")
    private Double baseMonthlyCarbonKg;

    public Double getEnergyPerLeakageUnit() {
        return energyPerLeakageUnit;
    }

    public void setEnergyPerLeakageUnit(Double energyPerLeakageUnit) {
        this.energyPerLeakageUnit = energyPerLeakageUnit;
    }

    public Double getCarbonFactorElectricity() {
        return carbonFactorElectricity;
    }

    public void setCarbonFactorElectricity(Double carbonFactorElectricity) {
        this.carbonFactorElectricity = carbonFactorElectricity;
    }

    public Double getCarbonFactorNaturalGas() {
        return carbonFactorNaturalGas;
    }

    public void setCarbonFactorNaturalGas(Double carbonFactorNaturalGas) {
        this.carbonFactorNaturalGas = carbonFactorNaturalGas;
    }

    public Double getCarbonFactorSteam() {
        return carbonFactorSteam;
    }

    public void setCarbonFactorSteam(Double carbonFactorSteam) {
        this.carbonFactorSteam = carbonFactorSteam;
    }

    public Double getCompressorEfficiency() {
        return compressorEfficiency;
    }

    public void setCompressorEfficiency(Double compressorEfficiency) {
        this.compressorEfficiency = compressorEfficiency;
    }

    public Double getRecoveryRate() {
        return recoveryRate;
    }

    public void setRecoveryRate(Double recoveryRate) {
        this.recoveryRate = recoveryRate;
    }

    public Double getBaseMonthlyEnergyKwh() {
        return baseMonthlyEnergyKwh;
    }

    public void setBaseMonthlyEnergyKwh(Double baseMonthlyEnergyKwh) {
        this.baseMonthlyEnergyKwh = baseMonthlyEnergyKwh;
    }

    public Double getBaseMonthlyCarbonKg() {
        return baseMonthlyCarbonKg;
    }

    public void setBaseMonthlyCarbonKg(Double baseMonthlyCarbonKg) {
        this.baseMonthlyCarbonKg = baseMonthlyCarbonKg;
    }

}